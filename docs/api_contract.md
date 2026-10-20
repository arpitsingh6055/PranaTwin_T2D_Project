# API and replay contract

Interactive OpenAPI schema at /docs. All endpoints use /api/v1 except /health. Request models reject unsupported scenario fields, input ranges and malformed payloads. 404 means unknown fictional ID, 403 means inactive/expired demo consent, 422 means invalid request, 409 means forecast quality/sufficiency failure, 503 means missing evaluation report.

If `PRANATWIN_API_KEY` is configured, API and WebSocket requests must include
the matching `X-API-Key` header. Static UI assets remain publicly loadable. The
default local showcase leaves the key unset so the browser demo works without
configuration. This is a deployment gate, not a replacement for an identity
provider or clinician authorization system.

| Method | Path | Contract |
|---|---|---|
| GET | /health | Status and in-memory persistence description |
| GET | /api/v1/patients | Public inventory of fictional IDs and synthetic source |
| GET | /api/v1/patients/{id} | Protected context |
| GET | /api/v1/patients/{id}/fhir | Protected Bundle and local structural report |
| GET | /api/v1/patients/{id}/timeline | Protected observed history through current cursor, state, replay and bookmarks |
| GET | /api/v1/twin/{id}/state | Protected typed virtual state |
| POST | /api/v1/twin/{id}/forecast | {horizon:15..120, multiple of 5}; defaults to 120 |
| POST | /api/v1/twin/{id}/counterfactual | {carbs:0..120, glycemic_factor:0.7..1.3, activity:1..5, duration:0..60} |
| POST | /api/v1/replay/{id} | action start/pause/reset/seek/speed, index 0..2879, speed 0.25..20 packets/s |
| GET/POST | /api/v1/consent/{id} | Status/expiry; POST {status:active or revoked}; demo restoration intentionally public |
| GET | /api/v1/evaluation | Computed synthetic metrics and provenance |
| GET | /api/v1/provenance | Version, source, limitations and documentation names |
| POST | /api/v1/ingest/wearable | Validate and persist a normalized authorized wearable API payload; does not fetch arbitrary URLs |
| POST | /api/v1/ingest/fhir | Validate and persist an authorized FHIR document bundle; does not assert ABDM conformance |
| POST | /api/v1/connectors/wearable/pull | Fetch the administrator-configured JSON wearable URL, validate it, and persist it |
| WS | /api/v1/stream/{id} | Protected snapshot every 0.5 s, type=snapshot, UTC heartbeat, state/replay/history/bookmarks |

WebSocket checks status/expiry before subscription and sends. Revocation closes active streams with 1008. Browser reconnects after other disconnects; snapshot messages also act as heartbeat. Snapshot history is bounded to 73 observations and never includes future replay packets. Simulation speed changes wall-clock playback only; each packet still spans five simulated minutes.

## Production intake boundary

The two ingestion endpoints accept data already retrieved by an authorized
connector. They intentionally do not accept a URL to fetch, preventing an
unbounded server-side request/SSRF surface. A connector may call a smartwatch
or clinical API outside this process, map its fields to the normalized packet
contract, and submit the resulting JSON. Every accepted batch receives a
SHA-256 digest and a local SQLite provenance/audit record. Provider
authentication, consent verification, patient identity matching, and clinical
terminology/profile validation remain deployment responsibilities.

The optional pull endpoint uses `PRANATWIN_WEARABLE_API_URL` configured in the
container environment. It adds an administrator-configured bearer token from
`PRANATWIN_WEARABLE_API_KEY`, enforces a ten-second timeout and a 2 MB response
limit, and rejects non-JSON responses. Callers cannot choose the URL.

State and compute responses are Pydantic validated. No API route imports arbitrary files or accepts real patient records. This reduces prototype exposure and deliberately separates external preprocessing from synthetic demo operation.
