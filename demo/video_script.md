# 22-minute technical demonstration

Record an uninterrupted walkthrough of the actual app. Do not substitute static screenshots for replay. Use fictional IDs only. Team and institution: [FILL IN].

| Time | Screen and spoken points |
|---|---|
| 00:00–02:00 | Title and use case. Explain focused short-horizon glycemic excursion research in an Indian outpatient context. State synthetic data and research-only boundary. Do not claim clinical validation or universal ethnic physiology. |
| 02:00–04:00 | Cohort context. Show all three synthetic profiles. Explain waist/BMI, hypertension/CKD and shift-work fields. Explain that these are configured examples, not representative prevalence estimates. |
| 04:00–06:00 | Architecture PDF. Trace FHIR historical glucose into initial state, packets into synchronization, state into forecast and WebSocket into UI. Describe one-process sandbox and restart behavior. |
| 06:00–08:00 | FHIR tab. Show Composition first, UUID references, Observation quantities, local check report. Explain missing full ABDM validation and text-only unverified concepts. |
| 08:00–11:00 | Control room. Start replay, change speed, pause/resume, seek post-meal bookmark and reset. Show packet index, state version, future timestamps, observed versus forecast styling. Show dropout bookmark and explain data quality. |
| 11:00–13:00 | Model code and methodology. Show the bounded Bergman/Hovorka-inspired prior, medication/eGFR context factors, gradient-boosted residual learner, quantile regressors and endpoint classifiers. State clearly that these are research outputs and are not clinically calibrated or a validated published physiological model. |
| 13:00–15:00 | Scenario lab. Pause replay. Compare zero-input baseline and an added meal/activity scenario. Read actual peak delta and assumptions. State that this is an illustrative sensitivity calculation, not a meal recommendation or medication advice. |
| 15:00–17:00 | Run tests and inspect API docs. Show health, forecast response and invalid input handling. Avoid claiming checks that did not run. Explain causal state and split-boundary tests. |
| 17:00–20:00 | Evaluation. Inspect actual CSV pairs and JSON metrics, compare persistence, Ridge, reduced-order and hybrid methods. Explain purges, train-only preprocessing, synthetic-data dependence, research quantile/probability outputs and Clarke Error Grid categories. Do not claim the synthetic benchmark is clinical validation. |
| 20:00–21:00 | Revoke consent. Show locked UI and denied protected API request, then restore. Explain local prototype access behavior and absence of identity/legal compliance. |
| 21:00–22:00 | Limitations and roadmap. Authorized PhysioNet or clinical dataset validation, subject-level holdout, probability calibration, physiological identification, external FHIR validator and security review. Explicitly exclude unsupported scenario risk-reduction percentages and deployment-cost claims. Show actual public repo URL only after publication; team details and video link must be completed by team. |

Before recording: `python manage.py up`, open localhost:8000, reset replay, restore consent, close unrelated windows. Capture clear desktop text and browser zoom. Verify the final recording is at least 20 minutes and its link is accessible to judges.
