# Data dictionary

All default values are synthetic. Telemetry timestamps carry +05:30 offset; UI labels IST. Internal comparisons use aware datetime objects. No timezone guessing on external input.

| Field | Unit/type | Source and transformation |
|---|---|---|
| id | fictional string | PT-IND-001..003, no real identifier |
| age | years | configured example; FHIR birth date assumes Jan 1 |
| bmi | kg/m2 | configured context, no physiology multiplier |
| waist_cm | cm | configured context |
| hba1c | % | configured example, LOINC 4548-4 |
| egfr | mL/min/1.73 m2 | configured example, not calculated |
| baseline | mg/dL | historical synthetic glucose, parsed from FHIR |
| diagnoses / medications | text lists | fictional history, no dose advice |
| shift_work | boolean | shifts synthetic meal timing only |
| timestamp | ISO 8601 offset | start 2026-10-01 IST + index*5 min |
| index | integer | zero-based replay packet |
| glucose | mg/dL or null | independent synthetic pulse/noise generator |
| unit | literal mg/dL | rejected if mismatched |
| hr | beats/min or null | synthetic 72 + activity effect + noise |
| hrv | ms or null | synthetic RMSSD-like fixture, not derived from IBI |
| eda | microSiemens or null | synthetic uniform fixture |
| temperature | deg C or null | synthetic skin-temperature fixture |
| activity | dimensionless MET-like proxy | configured simulated activity, not accelerometer-derived |
| carbs | g | logged meal at exact packet, zero otherwise |
| source | synthetic/open-source | provenance label; external importer disallows relabeling as synthetic |
| gut | g | decayed logged carbohydrate proxy |
| trend | mg/dL/min | bounded backward difference |
| version | count | number of synchronized packets since reset |
| observations | count | valid glucose observations |
| last_glucose | ISO timestamp | most recent nonmissing glucose |
| quality | string list | missing signals, gaps and sampling flags |
| forecast.points | timestamp, minute, glucose | future 5-min rollout; no intervals |
| scenario inputs | g, factor, proxy, min | additive meal/activity bounded by schema |

FHIR Bundle document includes Composition first, Patient, Organization, Condition, Observation and optional MedicationRequest. All internal references are urn:uuid with deterministic UUID5. Local validator checks document type, ordering, identifier/time, unique full URLs, resolved references and quantity shape. It does not execute FHIRPath, terminology bindings or complete ABDM constraints. Most codeable concepts use text until verified; units use UCUM system with no terminology-server validation.

Evaluation CSV: patient, origin, target, horizon (min), method, truth/prediction (mg/dL), quality, endpoint event class, source. JSON includes hashes, split boundaries, config, metrics and slices. Null metric means undefined/unsupported, never zero performance.
