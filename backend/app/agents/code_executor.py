import asyncio
import os
import tempfile
from pathlib import Path

MAX_STDOUT_BYTES = 50 * 1024   # 50 KB
EXEC_TIMEOUT_SECONDS = 60


async def execute_python_code(
    code: str,
    env_vars: dict[str, str],
) -> tuple[str, str, int]:
    """
    Write code to a temp file, run in subprocess with env vars injected.
    Returns (stdout, stderr, returncode).
    Cleans up temp file on exit.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        prefix="agentmaster_",
        dir=None,
        delete=False,
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        env = {**os.environ, **{k: str(v) for k, v in env_vars.items()}}
        proc = await asyncio.create_subprocess_exec(
            "python",
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=EXEC_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return "", f"Execution timed out after {EXEC_TIMEOUT_SECONDS}s", 1

        stdout = stdout_bytes[:MAX_STDOUT_BYTES].decode("utf-8", errors="replace")
        stderr = stderr_bytes[:MAX_STDOUT_BYTES].decode("utf-8", errors="replace")
        return stdout, stderr, proc.returncode or 0
    finally:
        Path(tmp_path).unlink(missing_ok=True)
