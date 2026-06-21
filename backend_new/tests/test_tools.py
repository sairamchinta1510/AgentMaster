import pytest
import os
import tempfile
from app.agents.tools.bash import bash_tool
from app.agents.tools.file_ops import file_read_tool, file_write_tool
from app.agents.tools.llm import llm_call_tool


# =============================================================================
# Bash Tool Tests
# =============================================================================

def test_bash_tool_success():
    """Test bash tool with successful command."""
    result = bash_tool("echo 'Hello World'")
    assert result["status"] == "completed"
    assert "Hello World" in result["stdout"]
    assert result["exit_code"] == 0


def test_bash_tool_failure():
    """Test bash tool with failing command."""
    result = bash_tool("exit 1")
    assert result["status"] == "failed"
    assert result["exit_code"] == 1


def test_bash_tool_timeout():
    """Test bash tool timeout."""
    result = bash_tool("sleep 10", timeout=1)
    assert result["status"] == "failed"
    assert "timed out" in result["stderr"].lower() or "timeout" in result.get("error", "").lower()


def test_bash_tool_with_stderr():
    """Test bash tool captures stderr."""
    result = bash_tool("python -c \"import sys; sys.stderr.write('error output')\"")
    assert result["status"] == "completed"
    assert "error output" in result["stderr"]


# =============================================================================
# File Operations Tests
# =============================================================================

def test_file_write_and_read():
    """Test writing and reading a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        content = "Hello, AgentMaster!"

        # Write
        write_result = file_write_tool(file_path, content)
        assert write_result["status"] == "completed"
        assert write_result["bytes_written"] > 0

        # Read
        read_result = file_read_tool(file_path)
        assert read_result["status"] == "completed"
        assert read_result["content"] == content


def test_file_read_not_found():
    """Test reading non-existent file."""
    result = file_read_tool("/tmp/nonexistent_file_12345.txt")
    assert result["status"] == "failed"
    assert "not found" in result["error"].lower()


def test_file_write_creates_directory():
    """Test that file_write_tool creates parent directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "subdir", "nested", "test.txt")
        content = "nested content"

        result = file_write_tool(file_path, content)
        assert result["status"] == "completed"
        assert os.path.exists(file_path)

        # Verify content
        read_result = file_read_tool(file_path)
        assert read_result["content"] == content


def test_file_write_overwrites():
    """Test that file_write_tool overwrites existing files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")

        # Write first content
        file_write_tool(file_path, "original content")

        # Overwrite with new content
        new_content = "overwritten content"
        result = file_write_tool(file_path, new_content)
        assert result["status"] == "completed"

        # Verify it was overwritten
        read_result = file_read_tool(file_path)
        assert read_result["content"] == new_content


def test_file_read_bytes_read():
    """Test that file_read_tool reports bytes_read."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        content = "Hello, World!"

        file_write_tool(file_path, content)
        result = file_read_tool(file_path)

        assert result["status"] == "completed"
        assert result["bytes_read"] > 0
        assert result["bytes_read"] == len(content.encode('utf-8'))


def test_file_write_root_level_file():
    """Test writing a file with no directory component (root-level)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory and write to root level
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            file_path = "test_root.txt"
            content = "root level file content"

            # Write to root-level file (no directory path)
            result = file_write_tool(file_path, content)
            assert result["status"] == "completed"
            assert result["bytes_written"] > 0

            # Verify the file was created
            assert os.path.exists(file_path)

            # Verify content
            read_result = file_read_tool(file_path)
            assert read_result["status"] == "completed"
            assert read_result["content"] == content
        finally:
            os.chdir(original_cwd)


# =============================================================================
# LLM Tool Tests
# =============================================================================

@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set"
)
def test_llm_call_tool():
    """Test LLM call with Gemini."""
    result = llm_call_tool("Say 'Hello AgentMaster' and nothing else.")
    assert result["status"] == "completed"
    assert "Hello" in result["response"] or "AgentMaster" in result["response"]
    assert result["tokens_used"] > 0


def test_llm_call_tool_with_system():
    """Test LLM call with system instruction."""
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    result = llm_call_tool(
        "What is 2+2?",
        system="You are a helpful assistant. Answer briefly."
    )
    assert result["status"] == "completed"
    assert result["tokens_used"] > 0
