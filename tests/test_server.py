"""Integration tests for the FastAPI backend service and UI console."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from nightshift.server.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_ui_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "NIGHT SHIFT" in response.text
    assert "Autonomous After-Hours Software Maintenance Worker" in response.text


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "nightshift"


def test_webhook_ping_event(client):
    response = client.post(
        "/api/webhooks/github",
        json={"zen": "Design for failure."},
        headers={"x-github-event": "ping"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["event"] == "ping"


def test_webhook_workflow_run_failure_queued(client):
    payload = {
        "action": "completed",
        "workflow_run": {
            "name": "CI Tests",
            "conclusion": "failure",
        },
        "repository": {
            "full_name": "saisushwanth17-dot/demo-service",
        },
    }
    response = client.post(
        "/api/webhooks/github",
        json=payload,
        headers={"x-github-event": "workflow_run"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "CI failure detected" in data["action_taken"]


def test_trigger_diagnostic_api(client):
    repo_path = str(Path(__file__).resolve().parents[1] / "demo_repo")
    response = client.post(
        "/api/triggers/diagnose",
        json={"repo_path": repo_path, "test_command": "pytest test_data_pipeline.py"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tests_passed"] is False
    assert "test_data_pipeline.py" in data["failing_test_name"]


def test_trigger_remediation_api(client):
    repo_path = str(Path(__file__).resolve().parents[1] / "demo_repo")
    response = client.post(
        "/api/triggers/remediate",
        json={
            "repo_path": repo_path,
            "test_command": "pytest test_data_pipeline.py",
            "repo_name": "demo_repo",
            "create_pr": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["remediation"]["status"] == "RESOLVED"
    assert data["remediation"]["successful_patch"] is not None


def test_briefing_api(client):
    response = client.get("/api/briefing?repo_name=demo_repo")
    assert response.status_code == 200
    data = response.json()
    assert "briefing" in data
    assert "markdown" in data
    assert data["briefing"]["repo_name"] == "demo_repo"


def test_incidents_api(client):
    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
