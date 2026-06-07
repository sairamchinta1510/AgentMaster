import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_session():
    r = client.post("/api/sessions", json={"objective": "Analyze my GitHub repo"})
    assert r.status_code == 201
    data = r.json()
    assert "session_id" in data
    assert data["phase"] == "DESIGN"


def test_get_session():
    r = client.post("/api/sessions", json={"objective": "Test objective"})
    session_id = r.json()["session_id"]
    r2 = client.get(f"/api/sessions/{session_id}")
    assert r2.status_code == 200
    assert r2.json()["session_id"] == session_id


def test_list_library():
    r = client.get("/api/library")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_404_unknown_session():
    r = client.get("/api/sessions/nonexistent-session-id-xyz")
    assert r.status_code == 404


def test_provide_input():
    r = client.post("/api/sessions", json={"objective": "Test input"})
    session_id = r.json()["session_id"]
    r2 = client.post(
        f"/api/sessions/{session_id}/input",
        json={"input_name": "api_key", "value": "test-value"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "input_received"
