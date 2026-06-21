import pytest
import uuid
from app.agents.atomic_agent import AtomicAgent
from app.models import Agent


def test_atomic_agent_execute_bash_command(db_session):
    """Test AtomicAgent executing a bash command."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    # Create agent record
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Run echo command",
        status="pending",
        input_data={"command": "echo 'test'"}
    )
    db_session.add(agent)
    db_session.commit()

    # Execute
    atomic = AtomicAgent(
        agent_id=agent_id,
        task_description="Run echo command",
        input_data={"command": "echo 'test'"},
        db_session=db_session
    )

    result = atomic.execute()

    assert result["status"] == "completed"
    assert "data" in result
    assert "citations" in result
    assert len(result["citations"]) > 0
    assert result["citations"][0]["source_type"] == "command"


def test_atomic_agent_logs_tool_execution(db_session):
    """Test that AtomicAgent logs tool executions to database."""
    from app.models import ToolExecution

    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Test task",
        status="running"
    )
    db_session.add(agent)
    db_session.commit()

    atomic = AtomicAgent(
        agent_id=agent_id,
        task_description="Test task",
        input_data={},
        db_session=db_session
    )

    # Log a tool execution
    atomic.log_tool_execution(
        tool_name="bash",
        tool_input={"command": "ls"},
        tool_output={"status": "completed", "stdout": "file1.txt"}
    )

    # Check database
    tool_exec = db_session.query(ToolExecution).filter_by(agent_id=agent_id).first()
    assert tool_exec is not None
    assert tool_exec.tool_name == "bash"
    assert tool_exec.status == "completed"


def test_atomic_agent_file_read(db_session, tmp_path):
    """Test AtomicAgent executing file read."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    # Create agent record
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Read file",
        status="pending"
    )
    db_session.add(agent)
    db_session.commit()

    # Create temp file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    # Execute
    atomic = AtomicAgent(
        agent_id=agent_id,
        task_description="Read file",
        input_data={"file_path": str(test_file)},
        db_session=db_session
    )

    result = atomic.execute()

    assert result["status"] == "completed"
    assert result["data"]["content"] == "Hello, World!"
    assert "citations" in result
    assert len(result["citations"]) > 0
    assert result["citations"][0]["source_type"] == "file"


def test_atomic_agent_file_write(db_session, tmp_path):
    """Test AtomicAgent executing file write."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    # Create agent record
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Write file",
        status="pending"
    )
    db_session.add(agent)
    db_session.commit()

    test_file = tmp_path / "output.txt"

    # Execute
    atomic = AtomicAgent(
        agent_id=agent_id,
        task_description="Write file",
        input_data={
            "file_path": str(test_file),
            "content": "Test content"
        },
        db_session=db_session
    )

    result = atomic.execute()

    assert result["status"] == "completed"
    assert result["data"]["bytes_written"] == 12
    assert test_file.read_text() == "Test content"
    assert "citations" in result
    assert result["citations"][0]["source_type"] == "file"
