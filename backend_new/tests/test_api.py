import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_execution(client):
    """Test creating an execution."""
    response = client.post(
        "/api/executions",
        json={
            "objective": "Test objective",
            "domain": "Test Domain",
            "config": {"max_recursion_depth": 5}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "planning"


def test_get_execution(client):
    """Test retrieving an execution."""
    # Create first
    create_response = client.post(
        "/api/executions",
        json={"objective": "Test", "domain": "Test"}
    )
    exec_id = create_response.json()["id"]

    # Get
    response = client.get(f"/api/executions/{exec_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == exec_id
    assert data["objective"] == "Test"
