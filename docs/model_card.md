# PranaTwin-T2D model card

Version 0.1.0, 2026-10-20. Intended users: technical reviewers and clinician researchers exploring a software PoC. Intended use: demonstrate synchronized EHR/telemetry state, synthetic forecasting, scenario sensitivity and transparent evaluation.

Out of scope: patient care, diagnosis, emergency monitoring, drug selection/dosing, individual nutritional recommendations, claims of regulatory clearance or certified safety. No CGM-free glucose estimation. No ethnicity inferred from identifiers.

Data: three fictional outpatient contexts, ten days each, deterministic seed 42. Context includes hypertension/CKD, lower BMI with waist circumference, and shift work. This is neither a representative Indian cohort nor a clinically validated dataset. No protected or real patient data. See data_provenance.md.

Algorithm: first-order glucose relaxation with decaying meal proxy; causal glucose assimilation and slowly tracked baseline. Historical FHIR glucose supplies initial baseline. HR/HRV/EDA/temperature are presented as contextual sensors. Ridge baseline additionally uses HR and causal features in offline evaluation. No trained residual ML deployed.

Evaluation: within-patient chronological 60/20/20 with 120-minute purge and reserved validation partition. Exact metrics in ../reports/metrics.json and pairwise predictions in ../reports/predictions.csv. At 120 min: RMSE 36.27 reduced-order, 43.83 persistence, 22.91 ridge mg/dL in the executed synthetic run. At 15 min the reduced-order model underperforms persistence. Weak results are retained. No accuracy threshold is a test assertion.

Uncertainty/event probability: unavailable. No calibrated bands, Brier score or claimed coverage. Deterministic threshold flags only. No verified Clarke-grid implementation.

Failure modes: unannounced meals, artificial low scenarios, missing/stale glucose, changes in baseline, unsupported input ranges, real-world domain shift, measurement lag and noise not represented by this simulator. Subgroups are too small and fictional to assess fairness or clinical performance. Reported slices are debugging evidence only.

Highest-value research next step: independently sourced, licensed CGM data with real meal annotations and a prespecified subject holdout. Validate model comparison and uncertainty before extending physiology or making clinical claims.
