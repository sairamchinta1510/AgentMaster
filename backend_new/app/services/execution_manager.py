import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models import Agent, Edge, Execution
from app.agents import SubAgent, AtomicAgent, CritiqueAgent
from app.services.graph_builder import GraphBuilder
from app.services.websocket_manager import websocket_manager
from app.schemas import WebSocketEvent
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExecutionManager:
    """
    Execution Manager - orchestrates agent execution in topological order.

    Responsibilities:
    - Load agents and edges from database
    - Build DAG and compute execution order
    - Execute agents sequentially (topological order)
    - Run critique after each agent
    - Broadcast WebSocket events
    - Update agent statuses in database
    """

    def __init__(self, execution_id: str, db_session: Session):
        self.execution_id = execution_id
        self.db_session = db_session

    async def execute(self) -> None:
        """Execute all agents for this execution."""
        logger.info(f"Starting execution: {self.execution_id}")

        # Load agents and edges
        agents = self.db_session.query(Agent).filter_by(execution_id=self.execution_id).all()
        edges = self.db_session.query(Edge).filter_by(execution_id=self.execution_id).all()

        if not agents:
            logger.warning(f"No agents found for execution {self.execution_id}")
            return

        # Build graph and get execution order
        graph = GraphBuilder()
        for agent in agents:
            graph.add_agent(agent)
        for edge in edges:
            graph.add_edge(edge)

        # Validate no cycles
        if not graph.validate_no_cycles():
            logger.error(f"Cycle detected in execution {self.execution_id}")
            await self._broadcast_event("execution_failed", {"reason": "Cycle detected in agent graph"})
            return

        # Get topological order
        execution_order = graph.topological_sort()
        logger.info(f"Execution order: {execution_order}")

        # Execute agents in order
        for agent_id in execution_order:
            agent = graph.agents[agent_id]
            await self._execute_agent(agent)

        # Mark execution complete
        execution = self.db_session.query(Execution).filter_by(id=self.execution_id).first()
        execution.status = "completed"
        execution.completed_at = datetime.utcnow()
        self.db_session.commit()

        await self._broadcast_event("execution_completed", {})
        logger.info(f"Execution {self.execution_id} completed")

    async def _execute_agent(self, agent: Agent) -> None:
        """Execute a single agent."""
        logger.info(f"Executing agent {agent.id}: {agent.task_description}")

        # Update status to running
        agent.status = "running"
        agent.started_at = datetime.utcnow()
        self.db_session.commit()

        await self._broadcast_event("agent_started", {
            "agent_id": agent.id,
            "agent_name": agent.task_description,
            "agent_type": agent.agent_type
        })

        try:
            # Execute based on agent type
            if agent.agent_type == "atomic_agent":
                result = await self._execute_atomic_agent(agent)
            elif agent.agent_type == "sub_agent":
                result = await self._execute_sub_agent(agent)
            else:
                raise ValueError(f"Unknown agent type: {agent.agent_type}")

            # Run critique
            agent.status = "critique_phase"
            self.db_session.commit()

            critique_result = await self._run_critique(agent, result)

            if critique_result["verdict"] == "approved":
                agent.status = "completed"
                agent.output_data = result["data"]
                agent.citations = result.get("citations", [])
                agent.completed_at = datetime.utcnow()
                self.db_session.commit()

                await self._broadcast_event("agent_completed", {
                    "agent_id": agent.id,
                    "agent_name": agent.task_description,
                    "output": result
                })
            elif critique_result["verdict"] == "rejected":
                # Retry logic would go here (max 3 retries)
                agent.status = "failed"
                self.db_session.commit()

                await self._broadcast_event("agent_failed", {
                    "agent_id": agent.id,
                    "agent_name": agent.task_description,
                    "reason": "Critique rejected output"
                })
            else:  # needs_human_review
                agent.status = "human_review"
                self.db_session.commit()

                await self._broadcast_event("human_review_needed", {
                    "agent_id": agent.id,
                    "agent_name": agent.task_description
                })

        except Exception as e:
            logger.error(f"Agent {agent.id} execution failed: {e}")
            agent.status = "failed"
            self.db_session.commit()

            await self._broadcast_event("agent_failed", {
                "agent_id": agent.id,
                "agent_name": agent.task_description,
                "error": str(e)
            })

    async def _execute_atomic_agent(self, agent: Agent) -> dict:
        """Execute an Atomic Agent."""
        atomic = AtomicAgent(
            agent_id=agent.id,
            task_description=agent.task_description,
            input_data=agent.input_data or {},
            db_session=self.db_session
        )
        return atomic.execute()

    async def _execute_sub_agent(self, agent: Agent) -> dict:
        """Execute a Sub-Agent (decompose into children)."""
        sub = SubAgent(
            agent_id=agent.id,
            task_description=agent.task_description,
            input_data=agent.input_data or {},
            depth=agent.depth,
            domain=agent.input_data.get("domain", "Unknown") if agent.input_data else "Unknown",
            db_session=self.db_session
        )

        decomposition = sub.decompose()

        # Create child agents in database
        for child in decomposition["children"]:
            child_agent = Agent(
                id=child["agent_id"],
                execution_id=self.execution_id,
                parent_id=agent.id,
                agent_type=child["agent_type"],
                depth=child["depth"],
                task_description=child["task_description"],
                status="pending",
                input_data=child["input_data"]
            )
            self.db_session.add(child_agent)

            await self._broadcast_event("agent_created", {
                "agent_id": child["agent_id"],
                "agent_name": child["task_description"],
                "agent_type": child["agent_type"],
                "parent_id": agent.id
            })

        # Create edges
        for edge in decomposition["edges"]:
            edge_obj = Edge(
                id=edge["edge_id"],
                execution_id=self.execution_id,
                from_agent_id=edge["from_agent_id"],
                to_agent_id=edge["to_agent_id"],
                data_description=edge.get("data_description")
            )
            self.db_session.add(edge_obj)

            await self._broadcast_event("edge_created", {
                "from_agent_id": edge["from_agent_id"],
                "to_agent_id": edge["to_agent_id"]
            })

        self.db_session.commit()

        return {
            "status": "completed",
            "data": {"decomposition": decomposition},
            "citations": [{
                "source_type": "decomposition",
                "source": "sub_agent",
                "excerpt": decomposition["reasoning"]
            }],
            "confidence": 90
        }

    async def _run_critique(self, agent: Agent, agent_output: dict) -> dict:
        """Run critique on agent output."""
        critique = CritiqueAgent(
            agent_id=agent.id,
            agent_output=agent_output,
            task_description=agent.task_description,
            db_session=self.db_session
        )

        result = critique.run_critique()

        await self._broadcast_event("critique_completed", {
            "agent_id": agent.id,
            "verdict": result["verdict"],
            "confidence": result["overall_confidence"]
        })

        return result

    async def _broadcast_event(self, event_type: str, data: dict) -> None:
        """Broadcast WebSocket event."""
        event = WebSocketEvent.create(
            event_type=event_type,
            execution_id=self.execution_id,
            data=data
        )
        await websocket_manager.broadcast(self.execution_id, event)
