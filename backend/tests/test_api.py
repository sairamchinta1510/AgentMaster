import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"


def test_create_pipeline():
    r = client.post("/api/pipelines", json={"objective": "Analyze my GitHub repo for security issues"})
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["objective"] == "Analyze my GitHub repo for security issues"
    assert "blueprint" in data
    assert "input_schema" in data


def test_list_pipelines():
    client.post("/api/pipelines", json={"objective": "List test pipeline"})
    r = client.get("/api/pipelines")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_pipeline():
    r = client.post("/api/pipelines", json={"objective": "Test get pipeline"})
    pipeline_id = r.json()["id"]
    r2 = client.get(f"/api/pipelines/{pipeline_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == pipeline_id


def test_get_pipeline_not_found():
    r = client.get("/api/pipelines/nonexistent-id-xyz")
    assert r.status_code == 404


def test_create_run():
    r = client.post("/api/pipelines", json={"objective": "Run test pipeline"})
    pipeline_id = r.json()["id"]
    r2 = client.post("/api/runs", json={"pipeline_id": pipeline_id, "inputs": {"key": "value"}})
    assert r2.status_code == 201
    data = r2.json()
    assert "id" in data
    assert data["pipeline_id"] == pipeline_id
    assert data["status"] == "pending"


def test_get_run():
    r = client.post("/api/pipelines", json={"objective": "Get run test"})
    pipeline_id = r.json()["id"]
    r2 = client.post("/api/runs", json={"pipeline_id": pipeline_id, "inputs": {}})
    run_id = r2.json()["id"]
    r3 = client.get(f"/api/runs/{run_id}")
    assert r3.status_code == 200
    assert r3.json()["id"] == run_id


def test_get_run_not_found():
    r = client.get("/api/runs/nonexistent-run-id-xyz")
    assert r.status_code == 404


def test_create_run_for_missing_pipeline():
    r = client.post("/api/runs", json={"pipeline_id": "nonexistent-pipeline-id"})
    assert r.status_code == 404


def test_list_runs_for_pipeline():
    r = client.post("/api/pipelines", json={"objective": "List runs test"})
    pipeline_id = r.json()["id"]
    client.post("/api/runs", json={"pipeline_id": pipeline_id, "inputs": {}})
    client.post("/api/runs", json={"pipeline_id": pipeline_id, "inputs": {}})
    r2 = client.get(f"/api/runs/by-pipeline/{pipeline_id}")
    assert r2.status_code == 200
    assert len(r2.json()) >= 2


def test_delete_pipeline():
    r = client.post("/api/pipelines", json={"objective": "Delete me"})
    pipeline_id = r.json()["id"]
    r2 = client.delete(f"/api/pipelines/{pipeline_id}")
    assert r2.status_code == 204
    r3 = client.get(f"/api/pipelines/{pipeline_id}")
    assert r3.status_code == 404
