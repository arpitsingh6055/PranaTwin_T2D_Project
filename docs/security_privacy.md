# Security and prototype governance

Self-hosted clinical research platform foundation. The default Docker binding is
127.0.0.1. SQLite persistence is local and intended for a single host. The API
still has no identity provider, JWT authorization, encryption-at-rest,
authenticated consent signing, multitenancy or tamper-evident audit chain.
The demo consent endpoint remains intentionally simplified. Do not expose this
deployment to a network or ingest identifiable patient data until those controls
are replaced by an independently reviewed identity and consent integration.
For a self-hosted deployment, set `PRANATWIN_API_KEY` through the container
environment and distribute it only to the trusted local integration. This is
an API gate, not user authentication or role-based access control.

All patient detail, FHIR, timeline, twin, forecast, scenario and replay routes use one server-side consent check. Active status and an eight-hour wall-clock expiry are required. Revocation stops replay and closes existing WebSockets with policy code 1008. Expiry is checked every replay tick and before stream sends. Public patient inventory exposes only fictional IDs; evaluation/provenance contain synthetic aggregate evidence. Consent management is deliberately accessible for demonstration. Browser clears protected displays when locked. Session state and consent reset on restart.

Retention: replay is discarded at shutdown; ingestion metadata and audit events
are retained in the mounted SQLite volume. The current endpoints store batch
digests and metadata, not a queryable clinical record, and do not fetch provider
URLs. Never put secrets, .env, real PHI or restricted data in git. No
request-body logging. Run server with --no-access-log to avoid path logging.
Error responses include validation messages, not stack traces. CORS is limited
to configured local development origins. CORS is not authentication.

Threat assumptions: single reviewer on a trusted local computer. Network exposure, malicious local users, resource exhaustion, browser extensions and shared workstation access are outside tested protections. Production would require independent security review, validated identity/consent workflows, secure transport, rate limits, retention controls, governance, clinical validation and applicable regulatory review. This document makes no DPDP, HIPAA, ABDM integration or certification claim.
