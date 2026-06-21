import uuid
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.agents.tools import bash_tool, file_read_tool, file_write_tool, llm_call_tool
from app.models import ToolExecution
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class AtomicAgent:
    """
    Base class for Atomic Agents - single-purpose executors.

    Each Atomic Agent executes ONE action using available tools.
    All outputs MUST include citations for anti-hallucination.
    """

    def __init__(
        self,
        agent_id: str,
        task_description: str,
        input_data: Dict[str, Any],
        db_session: Session
    ):
        self.agent_id = agent_id
        self.task_description = task_description
        self.input_data = input_data
        self.db_session = db_session
        self.start_time = None

    def execute(self) -> Dict[str, Any]:
        """
        Execute the agent's task.

        Returns:
            dict with status, data, citations, confidence, execution_time_ms
        """
        self.start_time = time.time()

        try:
            # Determine which tool to use based on task description
            # This is a simple implementation - in production, use LLM to decide
            result = self._execute_task()

            execution_time_ms = int((time.time() - self.start_time) * 1000)

            return {
                "status": result.get("status", "completed"),
                "data": result.get("data", {}),
                "citations": result.get("citations", []),
                "confidence": result.get("confidence", 100),
                "execution_time_ms": execution_time_ms
            }
        except Exception as e:
            logger.error(f"AtomicAgent {self.agent_id} execution failed: {e}")
            execution_time_ms = int((time.time() - self.start_time) * 1000)
            return {
                "status": "failed",
                "data": {},
                "citations": [],
                "confidence": 0,
                "execution_time_ms": execution_time_ms,
                "error": str(e)
            }

    def _execute_task(self) -> Dict[str, Any]:
        """
        Execute the actual task logic.
        Override this in subclasses for specific agent types.
        """
        # Simple heuristic: if input has "command", use bash tool
        if "command" in self.input_data:
            return self._execute_bash()
        elif "file_path" in self.input_data and "content" in self.input_data:
            return self._execute_file_write()
        elif "file_path" in self.input_data:
            return self._execute_file_read()
        elif "prompt" in self.input_data:
            return self._execute_llm()
        else:
            # Default: return input as output
            return {
                "status": "completed",
                "data": self.input_data,
                "citations": [{"source_type": "input", "source": "direct_passthrough"}],
                "confidence": 50
            }

    def _execute_bash(self) -> Dict[str, Any]:
        """Execute bash command."""
        command = self.input_data["command"]
        timeout = self.input_data.get("timeout", 30)

        tool_output = bash_tool(command, timeout)
        self.log_tool_execution("bash", {"command": command}, tool_output)

        return {
            "status": tool_output["status"],
            "data": {
                "stdout": tool_output["stdout"],
                "stderr": tool_output["stderr"],
                "exit_code": tool_output["exit_code"]
            },
            "citations": [{
                "source_type": "command",
                "source": command,
                "excerpt": tool_output["stdout"][:200]
            }],
            "confidence": 100 if tool_output["status"] == "completed" else 0
        }

    def _execute_file_read(self) -> Dict[str, Any]:
        """Read a file."""
        file_path = self.input_data["file_path"]

        tool_output = file_read_tool(file_path)
        self.log_tool_execution("file_read", {"file_path": file_path}, tool_output)

        return {
            "status": tool_output["status"],
            "data": {"content": tool_output.get("content", "")},
            "citations": [{
                "source_type": "file",
                "source": file_path,
                "excerpt": tool_output.get("content", "")[:200]
            }],
            "confidence": 100 if tool_output["status"] == "completed" else 0
        }

    def _execute_file_write(self) -> Dict[str, Any]:
        """Write to a file."""
        file_path = self.input_data["file_path"]
        content = self.input_data["content"]

        tool_output = file_write_tool(file_path, content)
        self.log_tool_execution("file_write", {"file_path": file_path, "content": content}, tool_output)

        return {
            "status": tool_output["status"],
            "data": {"bytes_written": tool_output.get("bytes_written", 0)},
            "citations": [{
                "source_type": "file",
                "source": file_path,
                "excerpt": f"Wrote {tool_output.get('bytes_written', 0)} bytes"
            }],
            "confidence": 100 if tool_output["status"] == "completed" else 0
        }

    def _execute_llm(self) -> Dict[str, Any]:
        """Call LLM."""
        prompt = self.input_data["prompt"]
        system = self.input_data.get("system")

        tool_output = llm_call_tool(prompt, system)
        self.log_tool_execution("llm_call", {"prompt": prompt}, tool_output)

        return {
            "status": tool_output["status"],
            "data": {"response": tool_output.get("response", "")},
            "citations": [{
                "source_type": "llm",
                "source": "gemini-1.5-flash",
                "excerpt": tool_output.get("response", "")[:200]
            }],
            "confidence": 90 if tool_output["status"] == "completed" else 0
        }

    def log_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Dict[str, Any]
    ) -> None:
        """Log a tool execution to the database."""
        tool_exec = ToolExecution(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            status=tool_output.get("status", "completed"),
            completed_at=datetime.now(timezone.utc) if tool_output.get("status") == "completed" else None
        )
        self.db_session.add(tool_exec)
        self.db_session.commit()
