import pytest
from app.prompts.critique_runtime import build_design_critique_prompt, build_run_critique_prompt


def test_design_critique_prompt_contains_agent_description():
    prompt = build_design_critique_prompt(
        agent_name="CloneRepository",
        agent_description="Clones a git repository to a local path",
        input_schema={"clone_url": {"type": "string"}},
        output_schema={"repository_path": {"type": "string"}},
    )
    assert "CloneRepository" in prompt
    assert "git" in prompt.lower() or "clone" in prompt.lower()
    assert "industry" in prompt.lower() or "standard" in prompt.lower()


def test_run_critique_prompt_contains_execution_results():
    prompt = build_run_critique_prompt(
        agent_name="IdentifyLogStorage",
        agent_description="Identifies the log storage mechanism",
        input_schema={"repository_path": {"type": "string"}},
        output_schema={"log_storage_mechanism": {"type": "string"}},
        actual_inputs={"REPOSITORY_PATH": "/tmp/tmpabc"},
        code="import os\npath = os.environ['REPOSITORY_PATH']",
        stdout='{"log_storage_mechanism": "file"}',
        stderr="",
        returncode=0,
    )
    assert "IdentifyLogStorage" in prompt
    assert "/tmp/tmpabc" in prompt
    assert "APPROVED" in prompt
    assert "NEEDS_FIX" in prompt


def test_run_critique_prompt_flags_output_schema_as_env_var():
    prompt = build_run_critique_prompt(
        agent_name="TestAgent",
        agent_description="Detects log events",
        input_schema={"repository_path": {"type": "string"}},
        output_schema={"detected_log_event": {"type": "string"}},
        actual_inputs={"REPOSITORY_PATH": "/tmp/repo"},
        code="import os\nevent = os.environ['DETECTED_LOG_EVENT']",
        stdout="",
        stderr="KeyError: 'DETECTED_LOG_EVENT'",
        returncode=1,
    )
    assert "output" in prompt.lower()
    assert "input" in prompt.lower()
    assert "DETECTED_LOG_EVENT" in prompt
