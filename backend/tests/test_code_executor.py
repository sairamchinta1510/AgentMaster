import asyncio
import pytest
from app.agents.code_executor import execute_python_code


@pytest.mark.asyncio
async def test_simple_print():
    stdout, stderr, rc = await execute_python_code('print("hello")', {})
    assert "hello" in stdout
    assert rc == 0


@pytest.mark.asyncio
async def test_env_var_injection():
    code = "import os; print(os.environ['MY_KEY'])"
    stdout, stderr, rc = await execute_python_code(code, {"MY_KEY": "secret_val"})
    assert "secret_val" in stdout
    assert rc == 0


@pytest.mark.asyncio
async def test_stderr_captured():
    code = "import sys; sys.stderr.write('oops\\n'); print('ok')"
    stdout, stderr, rc = await execute_python_code(code, {})
    assert "ok" in stdout
    assert "oops" in stderr


@pytest.mark.asyncio
async def test_timeout():
    from app.agents.code_executor import EXEC_TIMEOUT_SECONDS
    # Patch timeout to 1s for speed
    import app.agents.code_executor as mod
    original = mod.EXEC_TIMEOUT_SECONDS
    mod.EXEC_TIMEOUT_SECONDS = 1
    try:
        stdout, stderr, rc = await execute_python_code("import time; time.sleep(10)", {})
        assert "timed out" in stderr
        assert rc == 1
    finally:
        mod.EXEC_TIMEOUT_SECONDS = original
