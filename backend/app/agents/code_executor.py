import asyncio
import os
import tempfile
from pathlib import Path

MAX_STDOUT_BYTES = 50 * 1024   # 50 KB
EXEC_TIMEOUT_SECONDS = 60

# Build minimal subprocess env — only what Python needs to run
# Never expose server secrets (GEMINI_API_KEY, DATABASE_URL, etc.)
_SAFE_ENV_KEYS = {
    "PATH", "HOME", "USER", "TMPDIR", "TEMP", "TMP",
    "PYTHONPATH", "PYTHONHOME", "LANG", "LC_ALL",
    "SYSTEMROOT", "SYSTEMDRIVE",  # Windows
}


async def execute_python_code(
    code: str,
    env_vars: dict[str, str],
) -> tuple[str, str, int]:
    """
    Write code to a temp file and execute it in a subprocess.
    env_vars are injected as env vars; server secrets are NOT passed through.
    Returns (stdout, stderr, returncode).
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
        # Only pass safe system vars + caller-provided credentials
        safe_os_env = {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}
        # Always include Python executable path
        safe_os_env["PATH"] = os.environ.get("PATH", "")
        env = {**safe_os_env, **{k: str(v) for k, v in env_vars.items()}}
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
