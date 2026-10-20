# PranaTwin-T2D

Indian-context clinician-facing cardiometabolic Digital Twin research PoC for the **Happiest Health Digital Twin Challenge 2026**.

**Research only. Not for patient care, diagnosis, emergency monitoring or medication decisions. All default patient data and streams are synthetic.**

## Submission identity

| Required item | Status |
|---|---|
| Team name | [FILL IN] |
| College / institution / incubator | [FILL IN] |
| Members and roles (1–4 eligible students) | [FILL IN] |
| Team leader name, phone and email | [FILL IN] |
| Public GitHub repository URL | PENDING — local repository only |
| Minimum 20-minute demo video | PENDING — [recording instructions](demo/video_link.md) |
| Open-source license | [MIT](LICENSE), third-party data/dependencies excluded |

Before public submission, rename this project directory to **`Team Name_College Name`** using the real details. Publish only this directory, not the parent context pack, source research DOCX, master prompt or extracted media. Complete personal contact fields only with the team's intended publication details.

## What runs

React + TypeScript + Vite + Recharts control room, FastAPI/Pydantic API, WebSocket telemetry replay, Python/NumPy scientific core and scikit-learn ridge baseline. One API serves the compiled frontend. Docker Compose adds a durable local SQLite volume for provenance and audit metadata; no paid service, cloud credential or external database is required.

Three deterministic fictional profiles cover T2D with hypertension/CKD context, lower BMI with waist context, and prediabetes with shift work. Synthetic FHIR R4 document bundles include historical glucose, clinical context, labs and medication history. The synchronizer **reads its initial baseline from FHIR**, then advances state on five-minute packets. It produces actual 15–120 minute reduced-order forecasts and bounded additive meal/activity scenarios. The UI exposes replay controls, FHIR checks, evaluation evidence, data provenance and a revoke/restore consent demonstration.

This is an illustrative reduced-order model, not a full Bergman/Hovorka model. No residual ML, clinical validation, uncertainty bands, calibrated event probabilities, medication simulator, full ABDM integration or legal compliance is claimed. HR/HRV/EDA/temperature are contextual signals, not substitutes for CGM. See [model methodology](docs/model_methodology.md) and [decision log](docs/decision_log.md).

## Native setup and launch

Prerequisites: Python 3.12, Node.js 24 and pnpm 11.25.0. Initial dependency installation needs internet (or a populated package cache); after installation/build, startup uses local files only. All commands below run from this project directory.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
npm install -g pnpm@11.25.0
python manage.py setup
python manage.py up
```

macOS/Linux:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
npm install -g pnpm@11.25.0
python manage.py setup
python manage.py up
```

Open **http://127.0.0.1:8000**. API documentation: **http://127.0.0.1:8000/docs**. Stop with **Ctrl+C** in the server terminal. `python manage.py down` explains shutdown without terminating unrelated processes. State resets on restart. Run one worker because replay/consent state is in process memory.

For frontend development, run `pnpm --dir frontend dev` beside the API. Vite proxies `/api` and WebSockets to port 8000. `.env.example` documents optional CORS origins; set that environment variable in your shell if changing it. No secret configuration is necessary.

For a self-hosted integration, set `PRANATWIN_API_KEY` in the Docker
environment and send it as `X-API-Key`. Leave it unset only for a trusted
local showcase. This lightweight gate does not replace identity, roles,
consent management, TLS, or clinical governance.

## Docker alternative

```sh
docker compose up --build -d
docker compose ps
docker compose down
```

Same URL, port 8000. Compose configuration parses successfully. **Container execution has not been verified here because the Docker engine is not running.** Initial image builds need network access. The native path is the verified route. Do not claim a successful Docker launch based on the configuration check.

## Tests and reproducible evaluation

```sh
python manage.py test
python manage.py evaluate
pnpm --dir frontend exec playwright install chromium
# In a second terminal with the application running:
python manage.py smoke
```

`test` runs Python lint/unit/API tests, TypeScript checking, ESLint and frontend component tests, failing on nonzero status. Browser smoke uses the real API, including consent denial, and captures screenshots into reports/. CI repeats setup, tests, evaluation and browser journey. Hosted CI itself has not run until the repository is published.

Actual verification and limits: [audit](docs/audit.md). Current scientific/API/import suite: **23 passing tests**. Frontend: **2 passing component/API-client tests**, typecheck/lint/build pass. Browser: **1 passing complete journey**, with desktop and 390-pixel layout checks. Advisory reports are in reports/ and are time-specific, not security certification.

## Measured synthetic results

Within-patient chronological 60/20/20, 120-minute purges, train-only ridge preprocessing, test origins every 30 minutes. Three fictional patients; 8,640 generated rows; **276 held-out predictions per model/horizon**. Test windows overlap within holdout and are correlated. Validation partition is reserved, not used to tune these results.

| Horizon | Persistence RMSE | Ridge RMSE | Reduced-order RMSE |
|---|---:|---:|---:|
| 15 min | 9.05 | 6.79 | 9.54 |
| 30 min | 16.89 | 11.12 | 15.77 |
| 60 min | 29.66 | 18.83 | 26.50 |
| 90 min | 38.43 | 23.01 | 33.74 |
| 120 min | 43.83 | 22.91 | 36.27 |

Units: mg/dL. Ridge is strongest on this simulator; reduced-order loses to persistence at 15 minutes. These numbers do **not** establish clinical accuracy. The online dashboard uses the reduced-order state/scenario engine; ridge is an offline benchmark. [Full metrics](reports/metrics.json), [truth/prediction pairs](reports/predictions.csv), [figure](reports/evaluation.pdf). Metrics include MAE, MARD, confusion counts and AUROC/AUPRC where defined. No probabilistic Brier, interval coverage or verified Clarke grid is available. Undefined values are null.

## Demo walkthrough

1. Choose a fictional ID and inspect context and FHIR structural checks.
2. Start replay, change speed, pause/resume, seek a bookmark and reset.
3. Observe state version, history, future timestamps and quality flags. Age uses replay time, not today's wall clock.
4. Pause and compare bounded meal/activity scenarios from the same initial state. The meal is additive, not a validated food substitution.
5. Inspect evaluation and provenance. Revoke consent and verify data disappears and protected endpoints return 403. Restore demo access.

The normalized external-data importer preserves raw files and quality flags: [contract](docs/ingestion.md). The API also exposes explicit `/api/v1/ingest/wearable` and `/api/v1/ingest/fhir` boundaries for an authorized upstream smartwatch or clinical connector. The server does not fetch arbitrary URLs. Accepted batches receive a SHA-256 provenance record in local SQLite. CGMacros and BIG IDEAs are optional candidates; no public dataset has been used or redistributed. Follow each source's access/license conditions; never mix real and synthetic validation tables. [Data provenance](docs/data_provenance.md).

For a configured smartwatch/IoT GET provider, set
`PRANATWIN_WEARABLE_API_URL` and optionally
`PRANATWIN_WEARABLE_API_KEY`, then call
`POST /api/v1/connectors/wearable/pull` with a patient ID. The URL is
deployment-controlled and is never accepted from the caller.

## Submission and technical artifacts

- [Architecture PDF](docs/architecture.pdf), [editable Mermaid](docs/architecture.mmd), [diagram generator](scripts/build_figures.py)
- [Jury presentation PPTX](presentation/project_presentation.pptx) and [PDF viewing copy](presentation/project_presentation.pdf)
- [22-minute video script](demo/video_script.md) and [pending video URL](demo/video_link.md)
- [Model card](docs/model_card.md), [methodology](docs/model_methodology.md), [data dictionary](docs/data_dictionary.md), [sources](docs/sources.md)
- [Security/privacy](docs/security_privacy.md), [API contract](docs/api_contract.md), [artifact rebuilding](docs/artifact_build.md)
- [Synthetic FHIR example](samples/synthetic_fhir.json), [model config](config/model.json), [desktop screenshot](reports/dashboard-desktop.png), [mobile screenshot](reports/dashboard-mobile.png)

## Remaining work

Complete team identity, public publication and minimum 20-minute video; execute Docker when an engine is available. For research progress, prioritize authorized real-world CGM data with subject holdout and independent validation. Full FHIR profile/terminology validation, clinical parameter identification and production security are beyond this bounded sandbox. No hospital readiness is implied.
