# Execution audit

Build date: 2026-10-20. Scope: local Windows research sandbox. No clinical, legal or production certification.

## Executed evidence

- Source brief, research document and concept inspected; new project isolated from original sources.
- Fresh Python environment: `python manage.py setup` successfully installed requirements and ran frozen frontend install plus production build. Frontend used its lockfile and existing package cache. This was not a fresh OS or Linux container test.
- Python scientific/API/import tests: 25 passed. Tests cover deterministic generation, FHIR structure/reference failures, causal state, EHR fusion, invalid/timezone/unit/missing/stale inputs, finite bounded rollouts, horizons, identical-state scenarios, split purges, metric edge cases, external CSV provenance, authorized ingestion provenance, API-key gating and consent enforcement including live revocation.
- Frontend typecheck, ESLint, production build and two component/API-client tests passed. Browser journey passed with actual API: select, FHIR, replay, scenario, metrics, revoke/restore, patient switch and 390-pixel layout assertion.
- Desktop and mobile screenshots came from the running application and were visually inspected. Scenario animation disabled to ensure immediate evidence; panel alignment corrected. No horizontal overflow at 390 px. UI was not audited on every browser/device or by an accessibility specialist.
- The showcase control room now merges observed and forecast timestamps into one stable chart series, uses a fixed responsive chart height, labels the live path as the hybrid research forecast, and surfaces one primary threshold-crossing endpoint with an explicit uncalibrated-score warning.
- Evaluation executed on 8,640 synthetic rows; 276 eligible held-out origins per horizon/method; CSV and JSON generated. At 120 min RMSE: persistence 43.83, ridge 22.91, reduced-order 36.27, hybrid 19.12 mg/dL. Synthetic results only. Hybrid is strongest on this simulator; this is not clinical validation.
- Frontend advisory audit: zero reported vulnerabilities after upgrades. Python environment audit: no known vulnerabilities after FastAPI/Starlette/pytest upgrades. Registry snapshots are in reports/. These are time-specific advisory checks, not a security assessment.
- Docker Compose configuration, image build, container startup and healthcheck were verified with Docker Desktop 4.95.0 / Engine 29.8.2. The final container served the UI and API on 127.0.0.1:8000. SQLite ingestion/audit records survived container recreation through the named volume.
- Architecture and evaluation PDFs rendered and visually inspected. Ten-slide PowerPoint passed package, geometry, font, native chart/workbook and authoring-tool reimport checks; each slide rendering inspected. PowerPoint application itself was not used. The PDF deck is a raster viewing export of those rendered slides.
- Git initialized locally; no remote, public upload or commit is represented as completed. CI file is supplied but no hosted CI run exists yet.

## Warnings and limits

- Current dependency set produces an httpx TestClient deprecation warning; tests still pass. Production bundle is approximately 592 kB before gzip and triggers a build size advisory; code splitting is a reasonable future optimization.
- Initial sandbox execution blocked Python local socketpair/thread startup and Node file access. Tests were rerun with permitted local execution and passed. One clean-setup approval review timed out; the permitted retry succeeded. No blocked unsafe action remains.
- Residual boosting, quantile bounds, endpoint probabilities and Clarke Error Grid categories are implemented. They remain research outputs: no clinical calibration, prospective validation or safety certification is claimed.
- Local FHIR checks do not equal complete FHIR or ABDM validation. Only verified terminology is coded. Full national profile validation remains future work.
- Normalized CSV ingestion is implemented and tested. Authorized FHIR/wearable ingestion and a deployment-configured wearable JSON GET connector are implemented and tested at the contract boundary; provider-specific adapters and external-data model evaluation remain unavailable without inspected authorized data. No public dataset was downloaded.
- Prototype gate is not authentication. Eight-hour demo consent expires in wall-clock time; historical telemetry freshness uses replay time. State resets on restart. Use one API worker.

## Acceptance disposition

Implemented and verified: isolated runnable project; deterministic synthetic EHR/telemetry fusion; changing state; timestamped forecasts; visible source/model distinctions; same-state scenarios; FHIR viewer/local checks; protected endpoints and live revocation; leakage-aware measured evaluation; explicitly unavailable uncertainty; native tests/build/browser journey; documentation, MIT license, architecture, deck and 22-minute script.

External/manual pending: supply team/institution/member/contact details; rename directory to Team Name_College Name; publish the intended public repository; record and link a **minimum 20-minute** video. The software build is verified locally, but clinical deployment still requires identity/role integration, secure transport, complete FHIR/ABDM validation, clinical validation, governance and independent safety review.

Highest-value next research work: authorized real CGM benchmark with subject holdout; proper model identification and held-out uncertainty calibration; full FHIR validation; independent security/clinical review before any clinical translation.
