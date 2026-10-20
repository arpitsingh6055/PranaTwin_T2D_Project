# PranaTwin-T2D model card

Version 0.2.0, 2026-10-20. Intended users: technical reviewers and clinician researchers exploring a software PoC. Intended use: demonstrate synchronized EHR/telemetry state, a physiology-inspired prior, residual machine learning, scenario sensitivity and transparent evaluation.

Out of scope: patient care, diagnosis, emergency monitoring, drug selection/dosing, individual nutritional recommendations, claims of regulatory clearance or certified safety. No CGM-free glucose estimation. No ethnicity inferred from identifiers.

Data: three fictional outpatient contexts, ten days each, deterministic seed 42. Context includes hypertension/CKD, lower BMI with waist circumference, and shift work. This is neither a representative Indian cohort nor a clinically validated dataset. No protected or real patient data. See data_provenance.md.

Algorithm: bounded Bergman/Hovorka-inspired glucose, gut and insulin-action compartments with causal glucose assimilation, medication-context factors and renal-clearance sensitivity. A GradientBoostingRegressor learns residual corrections; two quantile GradientBoostingRegressor models produce 10th/90th percentile research bounds; endpoint GradientBoostingClassifier models estimate hyperglycemia/hypoglycemia probabilities when both classes exist. Features include glucose dynamics, HR, HRV, EDA, temperature, activity, BMI, waist, HbA1c, eGFR and medication-context factors. The trained hybrid predictor is now used by the live forecast endpoint. Parameters are engineering priors, not identified biological constants.

Evaluation: within-patient chronological 60/20/20 with 120-minute purge and reserved validation partition. Exact metrics in ../reports/metrics.json and pairwise predictions in ../reports/predictions.csv. Persistence, Ridge, reduced-order and hybrid models are compared, with Clarke Error Grid zone proportions now reported. Synthetic results are not clinical evidence and no accuracy threshold is a test assertion.

Uncertainty/event probability: quantile bounds and classifier probabilities are available as research outputs, but are explicitly marked not clinically calibrated. Brier score and calibration curves are not claimed. Clarke Error Grid is implemented as a research error categorization, not a safety certification.

Failure modes: unannounced meals, artificial low scenarios, missing/stale glucose, changes in baseline, unsupported input ranges, real-world domain shift, measurement lag and noise not represented by this simulator. Subgroups are too small and fictional to assess fairness or clinical performance. Reported slices are debugging evidence only.

External data candidates: PhysioNet BIG IDEAs Lab Glycemic Variability and Wearable Device Data (ODC-By) and PhysioNet CGMacros (CC BY 4.0). Neither is silently bundled or used in the synthetic report. Highest-value next step is an authorized download, source-specific parser, subject-level holdout, calibration analysis and independent clinical review.
