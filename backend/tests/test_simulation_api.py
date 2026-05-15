from fastapi.testclient import TestClient

from app.main import create_application


def _make_client() -> TestClient:
    app = create_application()
    return TestClient(app)


def test_start_initializes_simulation_session():
    with _make_client() as client:
        response = client.post(
            "/api/v1/simulation/start",
            json={"day_type": "weekday", "bess_capacity_kwh": 750.0},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"]
    assert payload["status"] == "paused"
    assert payload["day_type"] == "weekday"
    assert payload["current_interval"] == 0
    assert payload["battery_soc"] == 0.5
    assert payload["bess_capacity_kwh"] == 750.0
    assert payload["total_intervals"] > 0


def test_step_advances_simulation_and_records_decision_log():
    with _make_client() as client:
        start = client.post(
            "/api/v1/simulation/start",
            json={"day_type": "holiday", "bess_capacity_kwh": 600.0},
        )
        session_id = start.json()["session_id"]

        response = client.post("/api/v1/simulation/step", json={"session_id": session_id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == session_id
    assert payload["current_interval"] == 1
    assert len(payload["decision_log"]) == 1
    assert payload["current_time"]


def test_state_returns_latest_snapshot():
    with _make_client() as client:
        start = client.post(
            "/api/v1/simulation/start",
            json={"day_type": "solar_duck_curve", "bess_capacity_kwh": 1000.0},
        )
        session_id = start.json()["session_id"]
        client.post("/api/v1/simulation/step", json={"session_id": session_id})

        response = client.get("/api/v1/simulation/state", params={"session_id": session_id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == session_id
    assert payload["day_type"] == "solar_duck_curve"
    assert payload["current_interval"] == 1
    assert len(payload["decision_log"]) == 1


def test_pause_marks_session_as_paused():
    with _make_client() as client:
        start = client.post(
            "/api/v1/simulation/start",
            json={"day_type": "weekday", "bess_capacity_kwh": 500.0},
        )
        session_id = start.json()["session_id"]

        response = client.post("/api/v1/simulation/pause", json={"session_id": session_id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == session_id
    assert payload["status"] == "paused"
