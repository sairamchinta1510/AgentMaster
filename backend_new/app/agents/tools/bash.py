import subprocess
from typing import Dict


def bash_tool(command: str, timeout: int = 30) -> Dict:
    """
    Execute a bash command and return the result.

    Args:
        command: The bash command to execute
        timeout: Maximum execution time in seconds

    Returns:
        dict with status, stdout, stderr, exit_code
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "exit_code": -1,
            "error": "Command execution timeout"
        }
    except Exception as e:
        return {
            "status": "failed",
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "error": str(e)
        }
