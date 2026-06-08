import logging
import time
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.agents.agent_executor import AgentExecutorAgent
from app.agents.runtime_critique import CritiqueNodeExecutor
from app.models.pipeline import PipelineORM
from app.models.run import AgentResult, RunORM
from app.config import settings

logger = logging.getLogger(__name__)


def _topological_order(agents: list[dict]) -> list[dict]:
    """Return agents in dependency order (simple topological sort)."""
    agent_map = {agent["agent_id"]: agent for agent in agents}
    visited: set[str] = set()
    order: list[dict] = []

    def visit(agent_id: str):
        if agent_id in visited:
            return
        visited.add(agent_id)
        for dep in agent_map.get(agent_id, {}).get("depends_on", []):
            if dep in agent_map:
                visit(dep)
        order.append(agent_map[agent_id])

    for agent in agents:
        visit(agent["agent_id"])
    return order


async def _run_critique_node(
    critique_spec: dict,
    ordered_agents: list[dict],
    results: dict,
    context: dict,
    send,
    rerun_agent,
) -> None:
    """Execute a critique node: validate each depends_on agent's result via LLM."""
    agent_map = {a["agent_id"]: a for a in ordered_agents}
    deps = critique_spec.get("depends_on", [])
    critique_agent_id = critique_spec["agent_id"]
    critique_agent_name = critique_spec.get("agent_name", "Critique")

    def _store_and_payload(
        *,
        status: str,
        output: dict,
        error: str | None,
    ) -> dict:
        result = AgentResult(
            agent_id=critique_agent_id,
            agent_name=critique_agent_name,
            status=status,
            output=output,
            error=error,
            duration_ms=0,
        )
        results[critique_agent_id] = result
        return {
            "agent_id": critique_agent_id,
            "agent_name": critique_agent_name,
            "status": result.status,
            "output": result.output,
            "error": result.error,
            "duration_ms": result.duration_ms,
        }

    if not deps:
        await send(
            "AGENT_RESULT",
            _store_and_payload(
                status="completed",
                output={"critique_verdict": "SKIPPED", "reason": "no depends_on"},
                error=None,
            ),
        )
        return

    executor = CritiqueNodeExecutor()
    processed_targets = False
    target_summaries: list[dict] = []
    aggregate_status = "completed"
    aggregate_verdict = "APPROVED"
    aggregate_quality_score = 0.0
    aggregate_iterations = 0
    aggregate_issues: list[str] = []
    aggregate_errors: list[str] = []

    for target_id in deps:
        target_spec = agent_map.get(target_id)
        if not target_spec:
            continue

        processed_targets = True

        async def on_fix(instructions: str, iteration: int, _target_id=target_id):
            await send(
                "CRITIQUE_FIX",
                {
                    "agent_id": critique_agent_id,
                    "target_agent_id": _target_id,
                    "iteration": iteration,
                    "fix_instructions": instructions,
                },
            )
            await rerun_agent(target_spec, context, instructions)

        result = await executor.run_exec_critique(
            agent_spec=target_spec,
            actual_inputs=context,
            code=lambda _target_id=target_id: ((getattr(results.get(_target_id), "output", None) or {}).get("_code", "")),
            stdout=lambda _target_id=target_id: ((getattr(results.get(_target_id), "output", None) or {}).get("_stdout_preview", "")),
            stderr=lambda _target_id=target_id: (getattr(results.get(_target_id), "error", "") or ""),
            returncode=lambda _target_id=target_id: 1 if getattr(results.get(_target_id), "status", "completed") == "failed" else 0,
            min_iterations=3,
            max_iterations=5 if getattr(results.get(target_id), "status", "completed") == "failed" else 3,
            on_fix_needed=on_fix,
            on_event=send,
        )

        target_summary = {
            "target_agent": target_id,
            "critique_verdict": result.verdict,
            "quality_score": result.quality_score,
            "iterations": result.iterations,
            "issues": result.issues,
        }
        target_summaries.append(target_summary)
        aggregate_quality_score = min(aggregate_quality_score, result.quality_score) if target_summaries[:-1] else result.quality_score
        aggregate_iterations += result.iterations
        aggregate_issues.extend(result.issues)
        if result.verdict == "NEEDS_FIX":
            aggregate_status = "failed"
            aggregate_verdict = "NEEDS_FIX"
            if result.fix_instructions:
                aggregate_errors.append(f"{target_id}: {result.fix_instructions}")

    if not processed_targets:
        await send(
            "AGENT_RESULT",
            _store_and_payload(
                status="completed",
                output={"critique_verdict": "SKIPPED", "reason": "no target results"},
                error=None,
            ),
        )
        return

    await send(
        "AGENT_RESULT",
        _store_and_payload(
            status=aggregate_status,
            output={
                "critique_verdict": aggregate_verdict,
                "quality_score": aggregate_quality_score,
                "iterations": aggregate_iterations,
                "issues": aggregate_issues,
                "targets": target_summaries,
            },
            error="\n".join(aggregate_errors) if aggregate_errors else None,
        ),
    )


async def ws_run_handler(websocket: WebSocket, run_id: str):
    await websocket.accept()

    db: Session = SessionLocal()
    try:
        run = db.query(RunORM).filter(RunORM.id == run_id).first()
        if not run:
            await websocket.send_json({"type": "ERROR", "message": "Run not found"})
            await websocket.close()
            return

        pipeline = db.query(PipelineORM).filter(PipelineORM.id == run.pipeline_id).first()
        if not pipeline:
            await websocket.send_json({"type": "ERROR", "message": "Pipeline not found"})
            await websocket.close()
            return

        async def send(event_type: str, data: dict):
            await websocket.send_json({"type": event_type, "run_id": run_id, **data})

        if not settings.active_api_key:
            await send("ERROR", {"message": "No API key configured. Add GEMINI_API_KEY to backend/.env"})
            await websocket.close()
            return

        run.status = "running"
        db.commit()

        await send(
            "RUN_STARTED",
            {
                "pipeline_id": run.pipeline_id,
                "objective": pipeline.objective,
                "inputs": run.inputs,
            },
        )

        blueprint = pipeline.blueprint or {}
        agents = blueprint.get("agents", [])
        ordered_agents = _topological_order(agents)

        executor = AgentExecutorAgent()
        results: dict[str, AgentResult] = {}
        failed_agent_ids: set[str] = set()
        context: dict = dict(run.inputs or {})
        start_ms = int(time.time() * 1000)

        async def _emit_code_event(agent_id: str, phase: str, code_preview: str | None):
            await send(
                "CODE_STATUS",
                {
                    "agent_id": agent_id,
                    "phase": phase,
                    "elapsed_ms": int(time.time() * 1000) - start_ms,
                    "code_preview": code_preview,
                },
            )

        for agent_spec in ordered_agents:
            agent_id = agent_spec["agent_id"]

            if agent_id in failed_agent_ids:
                continue

            # ── Critique node dispatch ────────────────────────────────────────
            if agent_spec.get("agent_type") == "critique":
                async def _rerun(spec, ctx, fix_instr):
                    rerun_result = await executor.execute(
                        {**spec, "_critique_fix": fix_instr},
                        {**ctx, "_critique_fix_instructions": fix_instr},
                        on_code_event=_emit_code_event,
                    )
                    results[spec["agent_id"]] = rerun_result
                    if rerun_result.status != "failed":
                        context.update(rerun_result.output or {})

                await _run_critique_node(
                    critique_spec=agent_spec,
                    ordered_agents=ordered_agents,
                    results=results,
                    context=context,
                    send=send,
                    rerun_agent=_rerun,
                )
                critique_result = results.get(agent_id)
                if critique_result and critique_result.status == "failed":
                    failed_agent_ids.add(agent_id)
                continue

            # Skip this agent if any of its dependencies failed
            failed_deps = [dep for dep in agent_spec.get("depends_on", []) if dep in failed_agent_ids]
            if failed_deps:
                skip_msg = f"Skipped: upstream agent(s) failed — {', '.join(failed_deps)}"
                logger.warning("Skipping %s because of failed deps: %s", agent_id, failed_deps)
                skipped_result = AgentResult(
                    agent_id=agent_id,
                    agent_name=agent_spec.get("agent_name", agent_id),
                    status="failed",
                    output={},
                    error=skip_msg,
                    duration_ms=0,
                )
                results[agent_id] = skipped_result
                failed_agent_ids.add(agent_id)
                await send(
                    "AGENT_RESULT",
                    {
                        "agent_id": agent_id,
                        "agent_name": skipped_result.agent_name,
                        "status": "failed",
                        "output": {},
                        "error": skip_msg,
                        "duration_ms": 0,
                    },
                )
                continue

            await send(
                "AGENT_STARTED",
                {
                    "agent_id": agent_id,
                    "agent_name": agent_spec["agent_name"],
                },
            )

            async def _on_code_event(agent_id: str, phase: str, code_preview: str | None):
                await _emit_code_event(agent_id, phase, code_preview)

            result = await executor.execute(agent_spec, context, on_code_event=_on_code_event)
            results[agent_id] = result
            if result.status == "failed":
                failed_agent_ids.add(agent_id)
            else:
                context.update(result.output)

            await send(
                "AGENT_RESULT",
                {
                    "agent_id": result.agent_id,
                    "agent_name": result.agent_name,
                    "status": result.status,
                    "output": result.output,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                },
            )

            # ── Auto-critique every agent after execution ─────────────────────
            async def _auto_rerun(spec, ctx, fix_instr, _aid=agent_id, _spec=agent_spec):
                rerun_result = await executor.execute(
                    {**_spec, "_critique_fix": fix_instr},
                    {**ctx, "_critique_fix_instructions": fix_instr},
                    on_code_event=_on_code_event,
                )
                results[_aid] = rerun_result
                if rerun_result.status != "failed":
                    context.update(rerun_result.output or {})

            await _run_critique_node(
                critique_spec={
                    "agent_id": f"_autocritique_{agent_id}",
                    "agent_name": f"Critique:{agent_spec.get('agent_name', '')}",
                    "agent_type": "critique",
                    "depends_on": [agent_id],
                },
                ordered_agents=[agent_spec],
                results=results,
                context=context,
                send=send,
                rerun_agent=_auto_rerun,
            )

        final_results = [results[agent["agent_id"]] for agent in ordered_agents if agent["agent_id"] in results]
        failed = [result for result in final_results if result.status == "failed"]
        final_status = "failed" if failed else "completed"

        run.status = final_status
        run.results = [result.model_dump() for result in final_results]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()

        await send(
            "RUN_COMPLETE",
            {
                "status": final_status,
                "total_agents": len(ordered_agents),
                "completed": len([result for result in final_results if result.status == "completed"]),
                "failed": len(failed),
                "results": [result.model_dump() for result in final_results],
            },
        )

    except WebSocketDisconnect:
        logger.info("Run WS disconnected: %s", run_id)
    except Exception as exc:
        logger.error("Run WS error for run %s: %s", run_id, exc, exc_info=True)
        try:
            await websocket.send_json({"type": "ERROR", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
