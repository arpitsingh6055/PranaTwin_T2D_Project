import asyncio
import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from .data import PROFILES, telemetry, bundle, validate_bundle, baseline_from_bundle
from .model import initial, synchronize, forecast, Scenario
from .schemas import StateResponse, SnapshotResponse, ForecastResponse, ScenarioResponse
from .production import LocalStore, normalize_wearable_payload, validate_fhir_bundle
from .connectors import fetch_configured_wearable_payload
from .hybrid import train_predictor

ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("pranatwin")
DATA_DIR = Path(os.getenv("PRANATWIN_DATA_DIR", ROOT / "data"))
_PREDICTOR_CACHE = {}


class ReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["start", "pause", "reset", "seek", "speed"]
    index: int = Field(default=0, ge=0, le=2879)
    speed: float = Field(default=1, ge=0.25, le=20)


class ForecastRequest(BaseModel):
    horizon: int = Field(default=120, ge=15, le=120, multiple_of=5)


class ConsentRequest(BaseModel):
    status: Literal["active", "revoked"]


class WearableIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str
    payload: object
    source_uri: str | None = Field(default=None, max_length=500)


class FhirIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str
    bundle: dict
    source_uri: str | None = Field(default=None, max_length=500)


class WearablePullRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str


class Sandbox:
    def __init__(self):
        self.store = LocalStore(DATA_DIR / "pranatwin.sqlite3")
        self.profiles = {p["id"]: p for p in PROFILES}
        self.rows = {p["id"]: telemetry(p) for p in PROFILES}
        self.bundles = {p["id"]: bundle(p) for p in PROFILES}
        self.consents = {
            pid: {
                "status": "active",
                "expires": (
                    datetime.now(timezone.utc) + timedelta(hours=8)
                ).isoformat(),
            }
            for pid in self.profiles
        }
        self.replay = {
            pid: dict(index=96, running=False, speed=1.0, last_tick=time.monotonic())
            for pid in self.profiles
        }
        self.states = {}
        self.predictors = {}
        self.sockets = {pid: set() for pid in self.profiles}
        for pid in self.profiles:
            self.seek(pid, 96)
            self.predictors[pid] = self._train_predictors(pid)

    def _train_predictors(self, pid):
        if pid in _PREDICTOR_CACHE:
            return _PREDICTOR_CACHE[pid]
        context = self.profiles[pid]
        state = initial(baseline_from_bundle(self.bundles[pid]))
        states = []
        for row in self.rows[pid]:
            state = synchronize(state, row)
            states.append(state)
        train_end = int(len(self.rows[pid]) * 0.6) - 24
        predictors = {
            horizon: train_predictor(
                states,
                self.rows[pid],
                context,
                horizon,
                list(range(12, train_end, 4)),
            )
            for horizon in (15, 30, 60, 90, 120)
        }
        _PREDICTOR_CACHE[pid] = predictors
        return predictors

    def check(self, pid):
        if pid not in self.profiles:
            raise HTTPException(404, "Unknown synthetic patient")
        consent = self.consents[pid]
        if consent["status"] != "active" or datetime.fromisoformat(
            consent["expires"]
        ) <= datetime.now(timezone.utc):
            raise HTTPException(403, "Demo consent revoked or expired")

    def seek(self, pid, index):
        s = initial(baseline_from_bundle(self.bundles[pid]))
        for row in self.rows[pid][: index + 1]:
            s = synchronize(s, row)
        self.states[pid] = s
        self.replay[pid]["index"] = index
        self.replay[pid]["last_tick"] = time.monotonic()

    def snapshot(self, pid):
        self.check(pid)
        index = self.replay[pid]["index"]
        return dict(
            state=self.states[pid],
            replay={k: v for k, v in self.replay[pid].items() if k != "last_tick"},
            history=self.rows[pid][max(0, index - 72) : index + 1],
            bookmarks=[
                {"label": "Post-meal input", "index": 156},
                {"label": "Artificial low-glucose scenario", "index": 204},
                {"label": "Sensor dropout", "index": 400},
            ],
            total=len(self.rows[pid]),
            clock="simulated; age measured against replay timestamp",
        )

    async def close_streams(self, pid):
        self.replay[pid]["running"] = False
        for ws in list(self.sockets[pid]):
            try:
                await ws.close(code=1008, reason="Consent inactive")
            except RuntimeError:
                pass
        self.sockets[pid].clear()

    async def tick(self):
        while True:
            await asyncio.sleep(0.1)
            for pid, r in self.replay.items():
                try:
                    self.check(pid)
                except HTTPException:
                    await self.close_streams(pid)
                    continue
                if r["running"] and time.monotonic() - r["last_tick"] >= 1 / r["speed"]:
                    if r["index"] >= len(self.rows[pid]) - 1:
                        r["running"] = False
                    else:
                        r["index"] += 1
                        self.states[pid] = synchronize(
                            self.states[pid], self.rows[pid][r["index"]]
                        )
                        r["last_tick"] = time.monotonic()


def create_app():
    sandbox = Sandbox()

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(sandbox.tick())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app = FastAPI(
        title="PranaTwin research sandbox", version="0.1.0", lifespan=lifespan
    )
    app.state.sandbox = sandbox

    @app.middleware("http")
    async def request_audit(request, call_next):
        request_id = uuid4().hex
        started = time.monotonic()
        configured_key = os.getenv("PRANATWIN_API_KEY")
        supplied_key = request.headers.get("X-API-Key", "")
        protected_path = request.url.path.startswith("/api/")
        if (
            configured_key
            and protected_path
            and not hmac.compare_digest(supplied_key, configured_key)
        ):
            response = JSONResponse(
                status_code=401,
                content={"detail": "API key required", "request_id": request_id},
            )
            response.headers["X-Request-ID"] = request_id
            response.headers["Cache-Control"] = "no-store"
            return response
        try:
            response = await call_next(request)
        except Exception:
            # Deliberately omit request URL, bodies, patient IDs and exception payloads.
            log.error("request_failed request_id=%s", request_id)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal service error", "request_id": request_id},
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        log.info(
            "request_completed request_id=%s status=%s elapsed_ms=%.1f",
            request_id,
            response.status_code,
            (time.monotonic() - started) * 1000,
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(","),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "mode": "self-hosted clinical research platform",
            "persistence": "SQLite provenance/audit + in-memory replay state",
            "synthetic_showcase": True,
        }

    @app.get("/api/v1/patients")
    def patients():
        return [{"id": pid, "source": "synthetic"} for pid in sandbox.profiles]

    @app.post("/api/v1/ingest/wearable")
    def ingest_wearable(request: WearableIngestRequest):
        if request.patient_id not in sandbox.profiles:
            raise HTTPException(404, "Unknown patient")
        try:
            packets = normalize_wearable_payload(request.payload, request.patient_id)
            result = sandbox.store.record_batch(
                request.patient_id, "authorized-api", packets, request.source_uri
            )
            sandbox.store.audit(
                "wearable_ingestion",
                "api-client",
                {"packet_count": len(packets), "sha256": result["sha256"]},
                request.patient_id,
            )
            return {"accepted": True, **result}
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/v1/ingest/fhir")
    def ingest_fhir(request: FhirIngestRequest):
        if request.patient_id not in sandbox.profiles:
            raise HTTPException(404, "Unknown patient")
        try:
            validation = validate_fhir_bundle(request.bundle)
            result = sandbox.store.record_batch(
                request.patient_id,
                "authorized-fhir",
                [request.bundle],
                request.source_uri,
            )
            sandbox.store.audit(
                "fhir_ingestion",
                "api-client",
                {"validation": validation, "sha256": result["sha256"]},
                request.patient_id,
            )
            return {"accepted": True, "validation": validation, **result}
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/v1/connectors/wearable/pull")
    def pull_wearable(request: WearablePullRequest):
        if request.patient_id not in sandbox.profiles:
            raise HTTPException(404, "Unknown patient")
        try:
            payload, source_uri = fetch_configured_wearable_payload()
            packets = normalize_wearable_payload(payload, request.patient_id)
            result = sandbox.store.record_batch(
                request.patient_id, "authorized-api", packets, source_uri
            )
            sandbox.store.audit(
                "wearable_api_pull",
                "configured-connector",
                {"packet_count": len(packets), "sha256": result["sha256"]},
                request.patient_id,
            )
            return {"accepted": True, **result}
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/v1/patients/{pid}")
    def patient(pid: str):
        sandbox.check(pid)
        return dict(**sandbox.profiles[pid], source="synthetic")

    @app.get("/api/v1/patients/{pid}/fhir")
    def fhir(pid: str):
        sandbox.check(pid)
        b = sandbox.bundles[pid]
        return {"bundle": b, "validation": validate_bundle(b)}

    @app.get("/api/v1/patients/{pid}/timeline", response_model=SnapshotResponse)
    def timeline(pid: str):
        return sandbox.snapshot(pid)

    @app.get("/api/v1/twin/{pid}/state", response_model=StateResponse)
    def state(pid: str):
        sandbox.check(pid)
        return sandbox.states[pid]

    @app.post("/api/v1/twin/{pid}/forecast", response_model=ForecastResponse)
    def predict(pid: str, request: ForecastRequest):
        sandbox.check(pid)
        try:
            return forecast(
                sandbox.states[pid],
                request.horizon,
                context=sandbox.profiles[pid],
                predictor=sandbox.predictors[pid][request.horizon],
            )
        except ValueError as e:
            raise HTTPException(409, str(e)) from e

    @app.post("/api/v1/twin/{pid}/counterfactual", response_model=ScenarioResponse)
    def simulate(pid: str, request: Scenario):
        sandbox.check(pid)
        try:
            base = forecast(
                sandbox.states[pid],
                context=sandbox.profiles[pid],
                predictor=sandbox.predictors[pid][120],
            )
            alternative = forecast(
                sandbox.states[pid],
                scenario=request,
                context=sandbox.profiles[pid],
                predictor=sandbox.predictors[pid][120],
            )
            return dict(
                baseline=base,
                alternative=alternative,
                inputs=request.model_dump(),
                initial_state=sandbox.states[pid],
                delta_peak=round(
                    max(p["glucose"] for p in alternative["points"])
                    - max(p["glucose"] for p in base["points"]),
                    3,
                ),
                warning="Research simulation. No treatment or food recommendation.",
            )
        except ValueError as e:
            raise HTTPException(409, str(e)) from e

    @app.post("/api/v1/replay/{pid}", response_model=SnapshotResponse)
    def replay(pid: str, request: ReplayRequest):
        sandbox.check(pid)
        r = sandbox.replay[pid]
        if request.action == "start":
            r["running"] = True
            r["last_tick"] = time.monotonic()
        if request.action == "pause":
            r["running"] = False
        if request.action == "speed":
            r["speed"] = request.speed
        if request.action in ("seek", "reset"):
            r["running"] = False
            sandbox.seek(pid, request.index if request.action == "seek" else 96)
        return sandbox.snapshot(pid)

    @app.get("/api/v1/consent/{pid}")
    def consent(pid: str):
        if pid not in sandbox.profiles:
            raise HTTPException(404, "Unknown synthetic patient")
        return sandbox.consents[pid]

    @app.post("/api/v1/consent/{pid}")
    async def set_consent(pid: str, request: ConsentRequest):
        if pid not in sandbox.profiles:
            raise HTTPException(404, "Unknown synthetic patient")
        sandbox.consents[pid] = {
            "status": request.status,
            "expires": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
        }
        if request.status == "revoked":
            await sandbox.close_streams(pid)
        return sandbox.consents[pid]

    @app.get("/api/v1/evaluation")
    def evaluation():
        path = ROOT / "reports/metrics.json"
        if not path.exists():
            raise HTTPException(
                503, "Evaluation unavailable. Run python -m engine.evaluate"
            )
        return json.loads(path.read_text())

    @app.get("/api/v1/provenance")
    def provenance():
        return {
            "model_version": "0.1.0",
            "source": "synthetic showcase; authorized FHIR and wearable ingestion boundary available",
            "seed": 42,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "public_data_used": False,
            "storage": "Local SQLite provenance and audit ledger",
            "limitations": [
                "Not for patient care, diagnosis, emergency use or medication decisions.",
                "No calibrated intervals, event probabilities or clinical validation.",
                "Prototype consent gate, no authentication or legal compliance claim.",
                "HR/HRV/EDA/temperature displayed for context and quality; not used to infer glucose.",
            ],
            "documents": [
                "model_methodology.md",
                "data_provenance.md",
                "sources.md",
                "model_card.md",
            ],
        }

    @app.websocket("/api/v1/stream/{pid}")
    async def stream(ws: WebSocket, pid: str):
        configured_key = os.getenv("PRANATWIN_API_KEY")
        if configured_key and not hmac.compare_digest(
            ws.headers.get("x-api-key", ""), configured_key
        ):
            await ws.close(code=1008, reason="API key required")
            return
        try:
            sandbox.check(pid)
        except HTTPException:
            await ws.close(code=1008)
            return
        await ws.accept()
        sandbox.sockets[pid].add(ws)
        try:
            while True:
                sandbox.check(pid)
                await ws.send_json(
                    {
                        "type": "snapshot",
                        "heartbeat": datetime.now(timezone.utc).isoformat(),
                        **sandbox.snapshot(pid),
                    }
                )
                await asyncio.sleep(0.5)
        except (WebSocketDisconnect, RuntimeError, HTTPException):
            pass
        finally:
            sandbox.sockets[pid].discard(ws)
            try:
                await ws.close()
            except RuntimeError:
                pass

    if (ROOT / "frontend/dist").exists():
        app.mount(
            "/", StaticFiles(directory=ROOT / "frontend/dist", html=True), name="ui"
        )
    return app


app = create_app()
