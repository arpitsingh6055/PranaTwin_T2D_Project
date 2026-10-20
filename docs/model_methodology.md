# Model methodology, version 0.1.0

## Scope and equations

This is an engineering demonstrator of synchronization, not a validated physiological model. No full Bergman, Hovorka, insulin, medication, renal clearance, glucose mass balance or endogenous production model is claimed. Parameters below are explicit illustrative assumptions, not fitted biological constants. References in sources.md support standards and thresholds, not these parameter values.

Every five minutes, with glucose G (mg/dL), carbohydrate proxy Q (g), baseline B (mg/dL), activity A (dimensionless MET-like proxy), dt=5 min:

```
absorbed = Q * (1 - exp(-k_gut * dt))                 [g]
G_next = clip(G + dt*k_return*(B-G)
              + gain_carb*absorbed
              - dt*gain_activity*(A-1), 40, 400)     [mg/dL]
Q_next = max(0, Q - absorbed)                       [g]
```

The exponential gut update is exact for first-order decay; glucose relaxation uses forward Euler. Stability requires 0 <= dt*k_return <= 1 for a monotone step (default 0.06). This is a proxy calculation, not a blood-volume compartment or conservation claim. Clipping is a numerical guardrail and not evidence that a physiological response is safe.

At each packet, propagate old state, add the newly logged meal to Q, then assimilate observed glucose directly. Update B = clip(B + eta*(G_observed-B),70,200). Trend is the bounded causal glucose difference divided by elapsed minutes (mg/dL/min); ridge uses it, the reduced-order rollout does not. No latent insulin parameters are identified. Initialize G=B from the historical glucose Observation extracted from the FHIR Bundle, Q=0, trend=0. Each packet increments state version. Seek reconstructs all prior states from the seed rather than using future packets.

| Parameter | Default | Units | Supported bounds / provenance |
|---|---:|---|---|
| dt | 5 | min | Fixed step, illustrative |
| k_return | 0.012 | 1/min | Nonnegative, dt*k <=1 |
| k_gut | 0.025 | 1/min | Nonnegative, illustrative |
| gain_carb | 1.8 | (mg/dL)/g | Illustrative engineering gain |
| gain_activity | 0.3 | (mg/dL)/min per proxy unit | Illustrative, no individual response claim |
| eta | 0.01 | dimensionless | Bounded online baseline tracking |
| glucose bounds | 40..400 | mg/dL | Input/solver support boundary |
| stale cutoff | 15 | min | Operational assumption |
| event cutpoints | <70, >180 | mg/dL | International consensus source [S3] |

All model coefficients reside in config/model.json. Cohort values and synthetic pulse assumptions reside in engine/data.py. Ten days at five-minute intervals; meal pulse amplitude 75 mg/dL, centered 50 min after logged meals, Gaussian width 65 min; daily sinusoid amplitude 8; independent noise SD 3. The first patient has an artificial negative pulse amplitude 95 and width 35 at 17:00 IST. Generated glucose is clipped to 45..350. These patterns are software fixtures, not medication responses. Every 401st glucose packet is missing.

## Quality and causality

Require timezone-aware timestamps, mg/dL, finite bounded sensor values and strictly increasing timestamps. Duplicate/out-of-order packets fail. Missing glucose is propagated from the previous state with an explicit flag. Missing auxiliary signals are flagged. Irregular sampling/gaps are visible. Glucose older than 15 minutes relative to replay clock suppresses forecasts. Historical dates are intentionally not compared with today's wall clock; this is simulated replay. Gaps up to one day are propagated in five-minute substeps. Import contract rejects gaps above one day, and no future filling occurs.

## Forecast and scenarios

Return five-minute points out to 15..120 minutes, timestamps and units. Assume no unannounced future meal/activity. Event flags mean ANY predicted sampled value crosses the strict threshold within the horizon; they are research flags, not diagnoses. No calibrated event probabilities or intervals exist. Each scenario copies the identical initial state, adds 0..120 g carbohydrate multiplied by 0.7..1.3 factor, and applies activity 1..5 for 0..60 min. Report peak difference, curves, assumptions. It is not a food substitution estimate or treatment recommendation. The additive meal cannot establish a causal real-world benefit.

## Evaluation

Per patient, train origins are indices 12..1703; validation 1728..2279; untouched test 2304..2855 for 2880 rows. Maximum target is origin+24. Last training target is strictly before first validation origin; last validation target before first test origin. Test origins are every six packets (30 min). Separate ridge model per patient/horizon, StandardScaler and Ridge(alpha=10) fitted only on training data. Validation reserved; no tuning performed. Features: current causal glucose, trend, gut proxy, adaptive baseline, activity, HR. Future exogenous values are never features. State tracking updates in the held-out stream as observations arrive, as in deployment.

Evaluate persistence, ridge and reduced-order on identical eligible targets. MAE/RMSE in mg/dL. MARD=mean(abs(pred-truth)/truth)*100 only for positive synthetic truth. Endpoint event labels compare the target glucose with cutpoints, unlike UI any-crossing flags. Sensitivity/specificity/PPV/NPV use confusion counts; undefined denominators yield null. AUROC/AUPRC use continuous signed forecast glucose ranking and require both classes. No Brier score because no probability estimate. No interval coverage/width because no intervals. Clarke grid unavailable.

reports/predictions.csv retains every truth/prediction pair. reports/metrics.json records seed, config, source hash, sample counts, boundaries and slices. 276 test predictions per model/horizon across three patients. Overlapping holdout targets are correlated, so no independent-sample significance or confidence claim. Baseline tracking is not test-target leakage: only available observations at each origin are used. No real-world or new-patient generalization evidence.
