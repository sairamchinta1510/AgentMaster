import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.code_reviewer import detect_code_issues, review_and_fix_code


# ── detect_code_issues (static analysis, no LLM) ─────────────────────────────

def test_detects_hardcoded_tmp_path():
    code = 'subprocess.run(["git", "clone", url, "/tmp/repo"])'
    issues = detect_code_issues(code, available_inputs={})
    assert any("/tmp" in i.lower() or "hardcoded" in i.lower() for i in issues)


def test_allows_tempfile_mkdtemp():
    code = (
        "import tempfile\n"
        "path = tempfile.mkdtemp()\n"
        'subprocess.run(["git", "clone", url, path])\n'
    )
    issues = detect_code_issues(code, available_inputs={})
    assert not any("/tmp" in i.lower() or "hardcoded path" in i.lower() for i in issues)


def test_detects_shutil_rmtree_outside_tmp():
    code = 'import shutil\nshutil.rmtree("/var/data")\n'
    issues = detect_code_issues(code, available_inputs={})
    assert len(issues) > 0
    assert any("destructive" in i.lower() or "rmtree" in i.lower() for i in issues)


def test_allows_shutil_rmtree_on_tmp_path():
    code = (
        "import tempfile, shutil\n"
        "d = tempfile.mkdtemp()\n"
        "shutil.rmtree(d)\n"
    )
    issues = detect_code_issues(code, available_inputs={})
    # Cleanup of own tempdir is fine — no destructive issue
    assert not any("destructive" in i.lower() for i in issues)


def test_detects_rm_rf_shell_command():
    code = 'subprocess.run(["rm", "-rf", "/"])\n'
    issues = detect_code_issues(code, available_inputs={})
    assert any("destructive" in i.lower() or "rm" in i.lower() for i in issues)


def test_detects_hardcoded_value_matching_available_input():
    code = 'url = "https://github.com/myorg/myrepo"\n'
    issues = detect_code_issues(
        code,
        available_inputs={"CLONE_URL": "https://github.com/myorg/myrepo"},
    )
    assert any("clone_url" in i.lower() or "hardcoded" in i.lower() for i in issues)


def test_no_issues_on_clean_code():
    code = (
        "import os, tempfile, subprocess, json\n"
        "repo_url = os.environ['CLONE_URL']\n"
        "path = tempfile.mkdtemp()\n"
        'subprocess.run(["git", "clone", repo_url, path], check=True)\n'
        'print(json.dumps({"repository_path": path}))\n'
    )
    issues = detect_code_issues(
        code,
        available_inputs={"CLONE_URL": "https://github.com/myorg/myrepo"},
    )
    assert issues == []


# ── review_and_fix_code (calls LLM only when issues exist) ───────────────────

@pytest.mark.asyncio
async def test_review_skips_llm_when_no_issues():
    """Clean code should pass through without any LLM call."""
    clean_code = (
        "import os, tempfile, subprocess, json\n"
        "repo_url = os.environ['CLONE_URL']\n"
        "path = tempfile.mkdtemp()\n"
        'subprocess.run(["git", "clone", repo_url, path], check=True)\n'
        'print(json.dumps({"repository_path": path}))\n'
    )
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock()

    fixed, changes = await review_and_fix_code(
        clean_code,
        available_inputs={"CLONE_URL": "https://github.com/myorg/myrepo"},
        client=mock_client,
        model="gemini-pro",
    )

    mock_client.chat.completions.create.assert_not_called()
    assert fixed == clean_code
    assert changes == []


@pytest.mark.asyncio
async def test_review_calls_llm_and_returns_fixed_code_when_issues_found():
    """Code with hardcoded /tmp/repo should trigger LLM fix."""
    bad_code = 'subprocess.run(["git", "clone", "https://github.com/x/y", "/tmp/repo"])\n'
    fixed_code = (
        "import tempfile, subprocess, json\n"
        "path = tempfile.mkdtemp()\n"
        'subprocess.run(["git", "clone", "https://github.com/x/y", path], check=True)\n'
        'print(json.dumps({"repository_path": path}))\n'
    )

    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps({
            "fixed_code": fixed_code,
            "changes": ["Replaced /tmp/repo with tempfile.mkdtemp()"],
        })))]
    ))

    fixed, changes = await review_and_fix_code(
        bad_code,
        available_inputs={},
        client=mock_client,
        model="gemini-pro",
    )

    mock_client.chat.completions.create.assert_called_once()
    assert "tempfile.mkdtemp()" in fixed
    assert len(changes) > 0


@pytest.mark.asyncio
async def test_review_falls_back_to_original_if_llm_returns_invalid_json():
    """If LLM returns garbage, fall back to the original code rather than crashing."""
    bad_code = 'subprocess.run(["git", "clone", url, "/tmp/repo"])\n'

    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="not valid json at all"))]
    ))

    fixed, changes = await review_and_fix_code(
        bad_code,
        available_inputs={},
        client=mock_client,
        model="gemini-pro",
    )

    # Must not raise; falls back to original code
    assert fixed == bad_code
