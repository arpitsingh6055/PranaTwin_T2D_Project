# PranaTwin-T2D: 25-minute narration script

This is the presenter-only version of the Prototype & Code Submission script.
Read the paragraphs under the section headings without switching slides,
windows, browsers or terminals. The application and presentation footage can
be recorded separately and edited over this narration later.
Replace the team and institution placeholders before recording.

The script is deliberately evidence-grounded. It does not claim clinical
validation, regulatory approval, calibrated probabilities, medication dosing
advice, the unsupported 94.2% to 38.5% risk reduction, or a deployment-cost
estimate.

## Opening and challenge alignment

Hello everyone. We are **[team name]** from **[college or incubator]**, and
this is our submission for the Happiest Health Digital Twin Challenge 2026.
Our project is called **PranaTwin-T2D**.

The challenge asks us to build a proof-of-concept healthcare Digital Twin.
The important word here is not simply “digital”, and it is not simply
“prediction”. A Digital Twin is a continuously updated virtual representation
of a specific patient. It combines historical clinical context with incoming
measurements, maintains an evolving internal state, and uses that state to
simulate what may happen next.

The challenge specifically requires two data streams. The first is static or
historical data, such as demographics, diagnoses, laboratory results and
clinical history from an Electronic Health Record. The second is dynamic data,
such as continuous glucose, heart rate, heart-rate variability, electrodermal
activity, temperature, activity or other wearable signals.

The output must be a working algorithmic model that predicts a localized
adverse event and a conceptual dashboard showing how a clinician could
interact with the virtual patient.

We selected Type 2 Diabetes and a focused outcome: short-horizon glycemic
excursions, especially a future glucose value crossing the research thresholds
of 180 milligrams per deciliter or 70 milligrams per deciliter.

Our goal is not to claim that a student prototype can replace a doctor. Our
goal is to demonstrate the complete technical loop: EHR context, streaming
wearable data, synchronized patient state, a hybrid AI/ML forecast, scenario
analysis, evaluation, provenance and a clinician-facing interface.

## Why this problem matters

Traditional healthcare workflows are often reactive. A patient records a
glucose value, visits a clinic, or reports a symptom after an event has
already occurred. A proactive system would try to identify a deteriorating
trajectory early enough for a clinician to review it.

Type 2 Diabetes is a useful Digital Twin use case because glucose is dynamic.
It changes with meals, activity, sleep, stress, medication context, baseline
physiology and measurement timing. A single static risk score cannot represent
the difference between a stable patient at 150 milligrams per deciliter and a
patient currently rising rapidly after a meal.

The same historical glucose value can mean different things for different
patients. A patient with chronic kidney disease, a patient with different
body composition, and a patient with rotating shift work may have different
contexts and different timing patterns. That is why our architecture keeps
patient-specific context instead of treating every observation as an
independent row.

For the competition prototype, we use fictional synthetic profiles. This is
intentional. We do not use real identifiable patient data, and we do not
present the synthetic cohort as representative of India. Synthetic data lets
us demonstrate the complete workflow while respecting the challenge's privacy
constraints.

The future production path is an authorized ingestion layer for FHIR clinical
records and normalized wearable API data. The current showcase remains
synthetic and reproducible.

## What exactly we built

At the left of this architecture are two inputs.

The first input is a synthetic FHIR R4 document bundle. It contains a
Composition, a fictional Patient, clinical conditions, laboratory
observations, medication history and a historical glucose baseline.

The second input is a five-minute telemetry stream. Each packet may contain
glucose, heart rate, HRV, EDA, skin temperature, activity and logged
carbohydrates. Missing signals remain missing. We do not fill a missing future
measurement by looking ahead.

Both inputs meet at the state synchronizer. The synchronizer does not produce
a stateless prediction for each row. It updates a virtual patient state:
current glucose, adaptive baseline, remaining carbohydrate proxy, trend,
timestamp, observation count, quality flags and model context.

That state is passed into the hybrid forecast and scenario engine. The API
exposes the result through REST endpoints and a WebSocket stream. The React
control room renders the evolving state, history, forecasts, quality and
research warnings.

In parallel, the same deterministic data generator is evaluated using
chronological, purged splits. The evaluation writes machine-readable JSON
metrics and prediction pairs rather than hard-coding a performance claim.

The architecture is intentionally simple to run. One FastAPI process serves
the built React application. Docker Compose provides the container and a
local SQLite volume for ingestion provenance and audit metadata. No cloud
database or paid external service is required for the demonstration.

## Data governance and FHIR

Let us look at the historical stream first.

The FHIR document is a synthetic document bundle. The Composition is first,
internal references use deterministic UUIDs, and observation quantities include
values and units. The application runs local structural checks for bundle type,
Composition ordering, unique full URLs, reference resolution and quantity
shape.

This local check is useful, but I want to be precise: it is not a complete
FHIR validator, it is not a terminology server, and it does not prove full
ABDM conformance. The application makes that limitation visible instead of
quietly calling the bundle compliant.

The historical glucose observation is important because it initializes the
twin. The initial baseline is read from the FHIR bundle rather than copied
from a separate hidden value. BMI, waist, HbA1c, eGFR, diagnoses and
medication context are retained as patient context. In this prototype they
are model inputs and explanations, not treatment instructions.

For authorized integrations, the API has two explicit boundaries. A FHIR
bundle can be submitted after an upstream authorized connector has retrieved
it. A wearable payload can be submitted in the normalized packet contract.
Every accepted batch receives a SHA-256 fingerprint and a local provenance
record.

There is also an optional administrator-configured wearable GET connector.
The caller cannot provide an arbitrary URL. The deployment administrator
configures the URL and optional bearer token, and the connector applies a
timeout, JSON check and response-size limit. This is a safer boundary than
letting any browser request cause the server to fetch any URL.

## Dynamic data and replay

Now I will demonstrate the dynamic stream.

This is patient PT-IND-001, a fictional Type 2 Diabetes profile with
hypertension and chronic kidney disease context. The synthetic label is
always visible.

The latest glucose is shown with its simulated India-time timestamp. The twin
baseline is the historical EHR anchor followed by causal baseline tracking.
The clock is a replay clock, not the computer's current wall-clock time.

When replay starts, packets arrive in simulated order. The state version
increases as synchronization occurs. The chart combines observed history with
the future forecast. The future portion has timestamps that begin after the
current state timestamp.

The speed changes how quickly packets are replayed; it does not change the
meaning of one packet. Each packet still represents five simulated minutes.
Seeking reconstructs the state from the initial seed through the selected
index. It does not jump to a state calculated using future observations.

Here the quality panel can show missing glucose, missing auxiliary signals,
irregular sampling or a sensor gap. The system does not silently convert
missing data into a confident forecast. If glucose becomes stale relative to
the replay clock, the forecast endpoint rejects the request instead of
presenting an apparently fresh result.

This is one of the central Digital Twin properties: synchronization and data
quality are part of the result, not an afterthought.

## Model foundations

The model has three layers.

The first layer is a bounded physiology-inspired prior. It includes a glucose
state, a gut carbohydrate state and an insulin-action state. Carbohydrates
enter the gut compartment and decay through a first-order absorption process.
Glucose relaxes toward a patient baseline, rises with absorbed carbohydrate,
and is affected by activity and the insulin-action state.

The model also uses bounded context factors derived from the documented
patient context. eGFR contributes to a renal-clearance factor. Medication
names can contribute to a bounded insulin-action or hypoglycemia-sensitivity
factor. These are deliberately constrained engineering features.

This is not a published, fully identified Bergman or Hovorka model. We do not
estimate insulin sensitivity from clinical intervention data. We do not model
complete pharmacokinetics, renal drug clearance or dosing. We use the phrase
“Bergman/Hovorka-inspired” to describe the compartment structure, not to claim
clinical equivalence.

The second layer is machine learning. The model generates a physiology
inspired forecast first. A GradientBoostingRegressor learns the residual:

observed future glucose minus physiology-inspired predicted glucose.

The residual features include the current causal glucose, trend, remaining
gut proxy, adaptive baseline, heart rate, HRV, EDA, skin temperature,
activity, BMI, waist circumference, HbA1c, eGFR and medication-context
factors.

The third layer provides research uncertainty and event outputs. Two
gradient-boosted quantile regressors estimate the lower and upper research
bounds. Separate endpoint classifiers estimate whether the future target is
above 180 or below 70.

These probabilities are not clinical probabilities. They are model outputs
trained on the synthetic cohort and labelled as uncalibrated. We show them
because the blueprint calls for risk outputs, but we do not present them as
validated patient risk.

## Live hybrid forecast

The running API identifies this model as version 0.2.0-hybrid-gbr.

The endpoint returns 24 points because the horizon is 120 minutes and the
step is five minutes. It returns the forecast origin, state version, source,
event flags, research event probabilities and research quantile information.

The important distinction is that this forecast is not only the original
deterministic rollout. The live path trains the hybrid predictors during
application initialization from the reproducible synthetic training stream.
The dashboard forecast applies the physiology-inspired prior and the learned
residual correction.

The quantile output is useful for showing uncertainty as a first-class
concept. But the label says “research quantile model”. We do not call it a
95 percent clinical confidence interval. We have not established calibration,
coverage or clinical utility.

The high and low outputs are also separated. An above-180 probability and a
below-70 probability are different clinical questions. We do not collapse
them into a single universal risk score in the model itself.

## EHR and wearable feature fusion

This section demonstrates how the two streams are fused.

The EHR contributes relatively stable context: age, BMI, waist, HbA1c, eGFR,
diagnoses, medications and historical glucose. The dynamic stream contributes
the current glucose, trend, heart rate, HRV, EDA, temperature, activity and
meal proxy.

The current glucose is not replaced by HR or HRV. The auxiliary wearable
signals are not being used to estimate glucose when glucose is absent. They
are contextual model features and quality indicators. If a glucose value is
missing, the state records that fact, and a stale or insufficient state can
block forecasting.

This is also why a Digital Twin differs from a generic classifier demo. The
model carries forward state and timing. A packet at 8:00 and the same packet
at 20:00 are not interchangeable when the patient context and recent state
are different.

For a future smartwatch integration, a provider-specific adapter would map
the provider's authenticated data to this normalized schema. That adapter
must document timestamp semantics, units, sampling rate, missingness and
identity matching. We do not silently infer these details.

## Scenario simulation

The scenario engine starts from the same current state and creates an
alternative rollout. I can change additional carbohydrate, a bounded
glycemic factor, activity and duration.

The result shows a baseline forecast and an alternative forecast, along with
the peak difference and the input assumptions.

This is a counterfactual sensitivity experiment, not a recommendation. The
meal is an additive model input. It is not a validated food substitution.
The activity value is a proxy, not a prescribed exercise plan. Medication
changes are not offered as a scenario control.

We intentionally do not claim a fixed percentage reduction in risk from this
panel. The result depends on the current synthetic state, the model version
and the scenario inputs. A causal clinical effect would require intervention
data and prospective validation.

The same initial state test is important. The baseline and alternative begin
from identical state values. Only the declared scenario inputs change. This
prevents an accidental comparison between two different replay positions.

## Evaluation design

Now I will explain how we evaluated the model.

The synthetic cohort contains three fictional profiles and 8,640 generated
rows. The data is divided chronologically within patient into training,
validation and test regions. We apply a 120-minute purge between partitions
because a target at a future horizon must not overlap the neighboring split.
Test origins are sampled every 30 minutes.

The evaluation compares four methods:

First, persistence, which predicts that the current glucose remains the same.

Second, a Ridge regression baseline with standardization.

Third, the reduced-order deterministic forecast.

Fourth, the hybrid model, which combines the physiology-inspired prior with
the gradient-boosted residual, quantile and endpoint components.

At 120 minutes on this synthetic generator, the RMSE values are 43.83 for
persistence, 22.91 for Ridge, 36.27 for the reduced-order model, and 19.12
for the hybrid model.

Across all horizons, the hybrid RMSE values are 5.50, 7.99, 13.12, 17.57 and
19.12 milligrams per deciliter for 15, 30, 60, 90 and 120 minutes.

These numbers are real outputs from the current reports, but they are not
clinical accuracy. The generator creates the data distribution, the windows
are correlated, the cohort is tiny, and there is no new-patient evidence.
The hybrid model can benefit from patterns that exist in the simulator.

The report also includes MAE, MARD, event metrics and Clarke Error Grid zone
categories. We use Clarke categories as an error-analysis view. We do not
present them as a clinical safety certification.

The evaluation preserves prediction pairs in CSV. This lets a reviewer
inspect individual truth and prediction values instead of trusting only one
aggregate score.

## API, reproducibility and deployment

The backend is FastAPI with Pydantic request and response validation.

The forecast endpoint rejects unsupported horizons. Ingestion rejects
unsupported glucose units and malformed records. FHIR ingestion runs the
local structural checks before recording provenance.

The application exposes health, patients, FHIR, timeline, twin state,
forecast, counterfactual, replay, consent, evaluation, provenance and
WebSocket endpoints.

The Docker image builds the frontend and backend into a single self-hosted
container. Docker Compose maps the application to localhost port 8000 and
mounts a named volume for local SQLite provenance and audit records.

The database records batch metadata, source label, source URI where supplied,
packet count, SHA-256 digest and audit events. It does not pretend that this
alone is a complete clinical data platform.

For the showcase, the synthetic seed makes the behavior reproducible. For a
real deployment, the upstream connector would need authentication, consent,
identity matching, TLS, role-based access and organization-specific
governance.

## Consent and safety boundary

I will now demonstrate the access gate.

When consent is revoked, the browser clears protected patient content, the
protected API returns a denial, replay stops and active WebSocket streams are
closed. Restoring the demo consent re-enables the fictional sandbox.

This is a prototype access demonstration. It is not a legal consent system,
not an identity provider and not a replacement for clinical authorization.

The application displays a research-only warning because the system is not
for diagnosis, emergency monitoring, medication decisions or patient care.

## Limitations and roadmap

There are several limitations we want to state clearly.

First, the current reported metrics are synthetic. They do not establish
performance on real patients or a representative Indian population.

Second, the physiology layer is an engineering approximation inspired by
compartment models. It is not a fully identified Bergman/Hovorka simulator.

Third, quantile bounds and event probabilities are not clinically calibrated.
We have not claimed Brier performance, calibration curves, prospective
coverage, treatment utility or safety.

Fourth, the local FHIR checks are not complete ABDM profile validation.

Fifth, the medication and eGFR effects are bounded context features, not
pharmacokinetic or dosing recommendations.

Sixth, unannounced meals, sensor lag, device-specific measurement error,
missingness patterns and real-world domain shift are not fully represented by
the synthetic generator.

Our next research steps are:

One, obtain and document an authorized public dataset such as the PhysioNet
BIG IDEAs wearable and glycemic dataset or CGMacros, following its current
license and attribution requirements.

Two, build source-specific parsers rather than pretending different devices
have identical semantics.

Three, use subject-level holdout so the model is tested on people not seen in
training.

Four, calibrate probabilities and uncertainty on a separate validation
cohort.

Five, perform independent clinical, privacy, security and regulatory review
before any patient-care use.

We also explicitly exclude unsupported claims such as a fixed 94.2 percent
to 38.5 percent risk reduction or a fixed sub-rupee deployment cost. Those
figures are not substantiated by our current code or reports.

## Final summary

To summarize, PranaTwin-T2D demonstrates the complete Digital Twin loop for a
focused Type 2 Diabetes use case.

We start with a synthetic FHIR record and patient context.

We synchronize incoming five-minute wearable and glucose packets into a
causal virtual patient state.

We generate a bounded physiology-inspired forecast.

We correct that prior with a trained gradient-boosted residual model.

We produce research quantile bounds and endpoint event probabilities.

We compare the hybrid model against persistence, Ridge and reduced-order
baselines using chronological purged evaluation.

We expose the result in a clinician-facing control room with replay,
scenarios, quality flags, FHIR inspection, provenance and consent behavior.

Most importantly, we separate what is implemented from what remains to be
validated. This is a technically complete and reproducible research
prototype, not an autonomous medical device.

Thank you for watching our submission. The repository contains the source
code, Docker setup, architecture document, presentation PDF, model
methodology, model card, evaluation reports, data provenance and limitations.
