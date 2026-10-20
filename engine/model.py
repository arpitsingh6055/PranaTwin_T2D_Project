"""Reduced-order illustrative dynamics, not Bergman/Hovorka physiology."""

import json
import math
from pathlib import Path
from datetime import datetime, timedelta
from copy import deepcopy
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

CONFIG = json.loads(
    (Path(__file__).resolve().parents[1] / "config/model.json").read_text()
)
if not (
    0 <= CONFIG["step_minutes"] * CONFIG["return_rate"] <= 1 and CONFIG["gut_rate"] >= 0
):
    raise ValueError("Unstable model configuration")


class Packet(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    timestamp: datetime
    glucose: float | None = Field(default=None, ge=40, le=400)
    unit: str = "mg/dL"
    hr: float | None = Field(default=None, ge=30, le=220)
    hrv: float | None = Field(default=None, ge=0, le=250)
    eda: float | None = Field(default=None, ge=0, le=100)
    temperature: float | None = Field(default=None, ge=15, le=45)
    activity: float = Field(default=1, ge=1, le=8)
    carbs: float = Field(default=0, ge=0, le=150)
    source: Literal["synthetic", "open-source", "authorized-api", "authorized-fhir"] = (
        "synthetic"
    )
    index: int = 0


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    carbs: float = Field(default=0, ge=0, le=120)
    glycemic_factor: float = Field(default=1, ge=0.7, le=1.3)
    activity: float = Field(default=1, ge=1, le=5)
    duration: int = Field(default=0, ge=0, le=60)


def initial(baseline: float) -> dict:
    return dict(
        glucose=baseline,
        baseline=baseline,
        gut=0.0,
        trend=0.0,
        timestamp=None,
        last_glucose=None,
        version=0,
        quality=[],
        source="synthetic",
        observations=0,
        last_packet=None,
        insulin_action=0.0,
    )


def transition(
    g: float, gut: float, base: float, activity: float = 1
) -> tuple[float, float]:
    dt = CONFIG["step_minutes"]
    absorbed = gut * (1 - math.exp(-CONFIG["gut_rate"] * dt))
    next_g = (
        g
        + dt * CONFIG["return_rate"] * (base - g)
        + CONFIG["carb_gain"] * absorbed
        - dt * CONFIG["activity_gain"] * (activity - 1)
    )
    return min(400, max(40, next_g)), max(0, gut - absorbed)


def synchronize(state: dict, raw: dict) -> dict:
    p = Packet.model_validate(raw)
    if p.timestamp.tzinfo is None:
        raise ValueError("Timezone offset required")
    if p.unit != "mg/dL":
        raise ValueError("Expected mg/dL")
    s = deepcopy(state)
    gap = (
        5
        if not s["timestamp"]
        else (p.timestamp - datetime.fromisoformat(s["timestamp"])).total_seconds() / 60
    )
    if gap <= 0:
        raise ValueError("Duplicate or non-monotonic timestamp")
    if gap > 1440:
        raise ValueError("Gap exceeds one day; reinitialize explicitly")
    s["quality"] = []
    if gap != 5:
        s["quality"].append("irregular_sampling")
    if gap > 15:
        s["quality"].append("sensor_gap")
    for _ in range(max(1, min(288, int(gap / 5)))):
        s["glucose"], s["gut"] = transition(
            s["glucose"], s["gut"], s["baseline"], p.activity
        )
    s["gut"] += p.carbs
    if p.glucose is not None:
        s["trend"] = (
            max(-3, min(3, (p.glucose - state["glucose"]) / gap))
            if s["observations"]
            else 0
        )
        s["glucose"] = p.glucose
        s["last_glucose"] = p.timestamp.isoformat()
        s["observations"] += 1
        # Bounded baseline tracking, not physiological parameter identification.
        s["baseline"] = max(
            70,
            min(
                200,
                s["baseline"]
                + CONFIG["baseline_learning_rate"] * (p.glucose - s["baseline"]),
            ),
        )
    else:
        s["quality"].append("missing_glucose")
    s["quality"] += [
        "missing_" + k
        for k in ("hr", "hrv", "eda", "temperature")
        if getattr(p, k) is None
    ]
    s["timestamp"] = p.timestamp.isoformat()
    s["last_packet"] = p.model_dump(mode="json")
    s["version"] += 1
    s["source"] = p.source
    return s


def forecast(
    state: dict,
    horizon: int = 120,
    scenario: Scenario | None = None,
    context: dict | None = None,
    predictor=None,
) -> dict:
    if horizon < 15 or horizon > 120 or horizon % 5:
        raise ValueError("Horizon must be 15..120 in five-minute steps")
    if not state["timestamp"] or not state["last_glucose"]:
        raise ValueError("Insufficient glucose observations")
    origin = datetime.fromisoformat(state["timestamp"])
    age = (origin - datetime.fromisoformat(state["last_glucose"])).total_seconds() / 60
    if age > CONFIG["stale_minutes"]:
        raise ValueError("Glucose is stale relative to replay clock")
    scenario = scenario or Scenario()
    g = state["glucose"]
    gut = state["gut"] + scenario.carbs * scenario.glycemic_factor
    points = []
    for minute in range(5, horizon + 1, 5):
        g, gut = transition(
            g,
            gut,
            state["baseline"],
            scenario.activity if minute <= scenario.duration else 1,
        )
        points.append(
            dict(
                timestamp=(origin + timedelta(minutes=minute)).isoformat(),
                minute=minute,
                glucose=round(g, 3),
            )
        )
    model_version = CONFIG["version"]
    uncertainty = {
        "status": "unavailable",
        "reason": "No trained residual model supplied",
    }
    event_probability = None
    above_180_probability = None
    below_70_probability = None
    probability_status = "unavailable; deterministic threshold flags only"
    if context is not None:
        from .hybrid import hybrid_rollout

        hybrid_points = hybrid_rollout(state, context, horizon, scenario)
        for point, hybrid_point in zip(points, hybrid_points):
            point["hybrid_glucose"] = hybrid_point["glucose"]
        if predictor is not None:
            from .hybrid import feature_vector

            learned = predictor.predict(
                feature_vector(state, context, horizon),
                hybrid_points[-1]["glucose"],
            )
            correction = float(learned["prediction"]) - hybrid_points[-1]["glucose"]
            for point in points:
                point["glucose"] = round(
                    max(
                        40,
                        min(
                            400,
                            point["glucose"] + correction * point["minute"] / horizon,
                        ),
                    ),
                    3,
                )
            uncertainty = {
                "status": "research_quantile_model",
                "lower": learned["lower"],
                "upper": learned["upper"],
                "method": "gradient_boosting_quantile_regression",
            }
            event_probability = max(
                learned["above_180_probability"] or 0,
                learned["below_70_probability"] or 0,
            )
            above_180_probability = learned["above_180_probability"]
            below_70_probability = learned["below_70_probability"]
            probability_status = "research classifier; not clinically calibrated"
            model_version = "0.2.0-hybrid-gbr"
    return dict(
        points=points,
        origin=state["timestamp"],
        state_version=state["version"],
        unit="mg/dL",
        model_version=model_version,
        data_age_minutes=age,
        uncertainty=uncertainty,
        event_flags={
            "above_180": any(p["glucose"] > 180 for p in points),
            "below_70": any(p["glucose"] < 70 for p in points),
        },
        event_probability=event_probability,
        above_180_probability=above_180_probability,
        below_70_probability=below_70_probability,
        probability_status=probability_status,
        explanations=[
            f"Historical EHR baseline, updated causally: {state['baseline']:.1f} mg/dL",
            f"Remaining logged carbohydrate proxy: {state['gut']:.1f} g",
            "Illustrative model drivers; not causal clinical explanations",
        ],
        calibration=(
            "Synthetic-data research calibration; not clinically validated"
            if predictor is not None
            else "Illustrative parameters; baseline tracking only"
        ),
        source=state["source"],
    )


def counterfactual(state: dict, scenario: Scenario) -> dict:
    base = forecast(state)
    alt = forecast(state, scenario=scenario)
    return dict(
        baseline=base,
        alternative=alt,
        inputs=scenario.model_dump(),
        initial_state=deepcopy(state),
        delta_peak=round(
            max(p["glucose"] for p in alt["points"])
            - max(p["glucose"] for p in base["points"]),
            3,
        ),
        warning="Illustrative sensitivity experiment. Added meal/activity starts now. No treatment or food recommendation.",
    )
