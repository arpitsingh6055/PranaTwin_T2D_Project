from datetime import datetime, timedelta, timezone
import time
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from engine.api import create_app

PID = "PT-IND-001"


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


def test_vertical_slice(client):
    assert client.get("/health").status_code == 200
    assert len(client.get("/api/v1/patients").json()) == 3
    assert client.get(f"/api/v1/patients/{PID}/fhir").json()["validation"]["passed"]
    assert client.get("/api/v1/patients/unknown").status_code == 404
    assert (
        client.post(f"/api/v1/twin/{PID}/forecast", json={"horizon": 17}).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/twin/{PID}/counterfactual", json={"carbs": -1}
        ).status_code
        == 422
    )
    assert (
        client.post(f"/api/v1/twin/{PID}/forecast", json={}).json()["points"][-1][
            "minute"
        ]
        == 120
    )
    assert (
        client.post(
            f"/api/v1/twin/{PID}/counterfactual", json={"carbs": 30}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/provenance").json()["public_data_used"] is False


def test_production_ingestion_records_provenance(client):
    packet = {
        "timestamp": "2026-10-01T00:00:00+05:30",
        "glucose": 140,
        "unit": "mg/dL",
        "hr": 72,
        "hrv": 40,
        "eda": 0.6,
        "temperature": 33,
        "activity": 1,
        "carbs": 0,
    }
    response = client.post(
        "/api/v1/ingest/wearable",
        json={"patient_id": PID, "payload": [packet]},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["accepted"] is True
    assert result["source"] == "authorized-api"
    assert len(result["sha256"]) == 64

    malformed = {**packet, "unit": "mmol/L"}
    assert (
        client.post(
            "/api/v1/ingest/wearable",
            json={"patient_id": PID, "payload": [malformed]},
        ).status_code
        == 422
    )


def test_api_key_gate(monkeypatch):
    monkeypatch.setenv("PRANATWIN_API_KEY", "test-key")
    with TestClient(create_app()) as gated:
        assert gated.get("/api/v1/patients").status_code == 401
        assert gated.get(
            "/api/v1/patients", headers={"X-API-Key": "test-key"}
        ).status_code == 200


@pytest.mark.parametrize("reason", ["revoked", "expired", "unauthorized"])
def test_every_protected_route(client, reason):
    consent = client.app.state.sandbox.consents[PID]
    if reason == "expired":
        consent["expires"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
    else:
        consent["status"] = reason
    for path in [
        f"/patients/{PID}",
        f"/patients/{PID}/fhir",
        f"/patients/{PID}/timeline",
        f"/twin/{PID}/state",
    ]:
        assert client.get("/api/v1" + path).status_code == 403
    for path, body in [
        (f"/twin/{PID}/forecast", {}),
        (f"/twin/{PID}/counterfactual", {}),
        (f"/replay/{PID}", {"action": "start"}),
    ]:
        assert client.post("/api/v1" + path, json=body).status_code == 403
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/stream/{PID}") as ws:
            ws.receive_json()
    assert (
        client.post(f"/api/v1/consent/{PID}", json={"status": "active"}).status_code
        == 200
    )
    assert client.get(f"/api/v1/twin/{PID}/state").status_code == 200


def test_replay_and_socket_revocation(client):
    with client.websocket_connect(f"/api/v1/stream/{PID}") as ws:
        first = ws.receive_json()
        assert first["type"] == "snapshot"
        client.post(f"/api/v1/replay/{PID}", json={"action": "speed", "speed": 20})
        client.post(f"/api/v1/replay/{PID}", json={"action": "start"})
        time.sleep(0.3)
        client.post(f"/api/v1/replay/{PID}", json={"action": "pause"})
        later = client.get(f"/api/v1/twin/{PID}/state").json()
        assert later["version"] > first["state"]["version"]
        time.sleep(0.15)
        assert client.get(f"/api/v1/twin/{PID}/state").json() == later
        client.post(f"/api/v1/consent/{PID}", json={"status": "revoked"})
        with pytest.raises(WebSocketDisconnect):
            for _ in range(5):
                ws.receive_json()


def test_seek_reset_and_bounds(client):
    start = client.get(f"/api/v1/twin/{PID}/state").json()
    b = client.post(
        f"/api/v1/replay/{PID}", json={"action": "seek", "index": 156}
    ).json()
    assert b["history"][-1]["index"] == 156
    assert all(p["index"] <= 156 for p in b["history"])
    assert (
        client.post(f"/api/v1/replay/{PID}", json={"action": "reset"}).json()["state"]
        == start
    )
    assert (
        client.post(
            f"/api/v1/replay/{PID}", json={"action": "seek", "index": 3000}
        ).status_code
        == 422
    )
