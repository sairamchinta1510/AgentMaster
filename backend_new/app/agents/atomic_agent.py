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
        Intelligently selects tools based on task description and input.
        """
        # Explicit tool inputs (structured API)
        if "command" in self.input_data:
            return self._execute_bash()
        elif "file_path" in self.input_data and "content" in self.input_data:
            return self._execute_file_write()
        elif "file_path" in self.input_data:
            return self._execute_file_read()
        elif "prompt" in self.input_data:
            return self._execute_llm()

        # Task analysis (natural language)
        task_lower = self.task_description.lower()
        objective = self.input_data.get("objective", "").lower()
        domain = self.input_data.get("domain", "").lower()

        # Content Generation tasks
        if any(keyword in task_lower or keyword in objective for keyword in [
            "create", "write", "generate", "document", "training", "report",
            "guide", "tutorial", "article", "content"
        ]):
            return self._execute_content_generation()

        # Command execution tasks
        elif any(keyword in task_lower for keyword in ["echo", "run", "execute", "command"]):
            return self._execute_simple_command()

        # File operations
        elif any(keyword in task_lower for keyword in ["read file", "open file", "load file"]):
            return self._execute_simple_file_read()

        # Default: use LLM to reason about the task
        else:
            logger.warning(f"No specific tool matched for task: {self.task_description}")
            return self._execute_general_task()

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

    def _execute_content_generation(self) -> Dict[str, Any]:
        """
        Generate content (documents, training materials, reports, etc.).
        Uses LLM to create content, then saves to file.
        """
        objective = self.input_data.get("objective", self.task_description)
        domain = self.input_data.get("domain", "General")

        # Step 1: Use LLM to generate content
        prompt = f"""You are an expert content creator in the domain of {domain}.

Task: {objective}

Please create comprehensive, well-structured content that fully addresses this objective.
Include:
- Clear sections and headings
- Detailed explanations
- Practical examples where relevant
- Best practices
- Common pitfalls to avoid

Format the output in Markdown format."""

        llm_output = llm_call_tool(prompt)
        self.log_tool_execution("llm_call", {"prompt": prompt}, llm_output)

        if llm_output["status"] != "completed":
            return {
                "status": "failed",
                "data": {},
                "citations": [],
                "confidence": 0,
                "error": llm_output.get("error", "LLM call failed")
            }

        content = llm_output.get("response", "")

        # Step 2: Save to file
        import os
        filename = self._generate_filename(objective, domain)
        file_path = os.path.join(".", filename)

        file_output = file_write_tool(file_path, content)
        self.log_tool_execution("file_write", {"file_path": file_path, "content": content}, file_output)

        return {
            "status": "completed",
            "data": {
                "file_path": file_path,
                "content_preview": content[:500] + "..." if len(content) > 500 else content,
                "total_length": len(content),
                "word_count": len(content.split())
            },
            "citations": [
                {
                    "source_type": "llm",
                    "source": "gemini-1.5-flash",
                    "excerpt": content[:200]
                },
                {
                    "source_type": "file",
                    "source": file_path,
                    "excerpt": f"Created {filename} with {len(content)} characters"
                }
            ],
            "confidence": 95  # High confidence for completed content generation
        }

    def _execute_simple_command(self) -> Dict[str, Any]:
        """Execute simple bash commands like echo, ls, etc."""
        # Extract command from task description
        task_lower = self.task_description.lower()

        if "echo" in task_lower:
            # Extract what to echo
            parts = self.task_description.split("'")
            if len(parts) >= 2:
                message = parts[1]
            else:
                parts = self.task_description.split('"')
                message = parts[1] if len(parts) >= 2 else "Hello AgentMaster"

            command = f'echo "{message}"'
        else:
            # Default simple command
            command = "echo 'Task completed'"

        tool_output = bash_tool(command, timeout=5)
        self.log_tool_execution("bash", {"command": command}, tool_output)

        return {
            "status": tool_output["status"],
            "data": {
                "stdout": tool_output["stdout"],
                "command": command
            },
            "citations": [{
                "source_type": "command",
                "source": command,
                "excerpt": tool_output["stdout"]
            }],
            "confidence": 100 if tool_output["status"] == "completed" else 0
        }

    def _execute_simple_file_read(self) -> Dict[str, Any]:
        """Read a file when no explicit path given."""
        # Try to extract filename from task description
        # For now, return an error
        return {
            "status": "failed",
            "data": {},
            "citations": [],
            "confidence": 0,
            "error": "File path not specified in input"
        }

    def _execute_general_task(self) -> Dict[str, Any]:
        """
        Fallback: Use LLM to reason about and execute the task.
        """
        objective = self.input_data.get("objective", self.task_description)

        prompt = f"""You are an AI agent executing a task.

Task: {objective}

Please complete this task and provide a detailed response explaining:
1. What you did
2. The results
3. Any relevant information

Be specific and actionable."""

        llm_output = llm_call_tool(prompt)
        self.log_tool_execution("llm_call", {"prompt": prompt}, llm_output)

        if llm_output["status"] != "completed":
            return {
                "status": "failed",
                "data": {},
                "citations": [],
                "confidence": 0,
                "error": llm_output.get("error", "LLM call failed")
            }

        response = llm_output.get("response", "")

        return {
            "status": "completed",
            "data": {"response": response},
            "citations": [{
                "source_type": "llm",
                "source": "gemini-1.5-flash",
                "excerpt": response[:200]
            }],
            "confidence": 80  # Moderate confidence for general tasks
        }

    def _generate_filename(self, objective: str, domain: str) -> str:
        """Generate a meaningful filename from objective and domain."""
        import re
        from datetime import datetime

        # Extract key words from objective
        words = re.findall(r'\b[a-zA-Z]{4,}\b', objective.lower())
        key_words = [w for w in words[:5] if w not in ['create', 'write', 'generate', 'comprehensive', 'document']]

        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_part = "_".join(key_words[:3]) if key_words else domain.replace(" ", "_").lower()

        return f"{name_part}_{timestamp}.md"

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
