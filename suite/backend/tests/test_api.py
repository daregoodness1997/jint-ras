"""Backend API tests for the research suite."""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import app


def test_root() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "research-suite"


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_models() -> None:
    client = TestClient(app)
    response = client.get("/api/models")
    assert response.status_code == 200
    models = response.json()["models"]
    assert "JINT" in models
    assert "RAS" in models


def test_controllers() -> None:
    client = TestClient(app)
    response = client.get("/api/controllers")
    assert response.status_code == 200
    controllers = response.json()["controllers"]
    assert "pd" in controllers


def test_params() -> None:
    client = TestClient(app)
    response = client.get("/api/params/JINT")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "JINT"
    names = {p["name"] for p in data["params"]}
    assert "A_deg" in names
    assert "f" in names
    assert "rho_deg_s" in names


def test_unknown_model_params() -> None:
    client = TestClient(app)
    response = client.get("/api/params/NOPE")
    assert response.status_code == 404


def test_simulate() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/simulate",
        json={"model": "JINT", "controller": "pd", "A_deg": 40.0, "f": 1.0, "rho_deg_s": 0.0, "duration": 2.0, "f_sim": 200.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "JINT"
    assert "metrics" in data
    assert "distance" in data["metrics"]


def test_start_and_get_sweep() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/sweep",
        json={
            "model": "JINT",
            "controller": "pd",
            "axes": {"A_deg": [40.0, 50.0], "f": [0.8, 1.2]},
            "duration": 2.0,
            "f_sim": 200.0,
        },
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    get_response = client.get(f"/api/sweep/{run_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["run_id"] == run_id
    assert data["status"] in {"queued", "running", "completed"}


def test_runs_list() -> None:
    client = TestClient(app)
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert "runs" in response.json()
