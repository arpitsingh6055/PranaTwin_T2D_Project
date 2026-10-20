"""Hybrid physiology-inspired and machine-learning forecasting.

This module is a research implementation. Parameters are engineering priors,
not identified patient physiology or a clinical treatment model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

from .model import CONFIG


def medication_profile(context: dict[str, Any]) -> dict[str, float]:
    """Convert documented medication/context fields into bounded model factors."""
    egfr = float(context.get("egfr", 90))
    renal_factor = max(0.7, min(1.5, 90 / max(30, egfr)))
    medications = " ".join(context.get("medications", [])).lower()
    sulfonylurea = 1.15 if any(
        name in medications for name in ("glimepiride", "glipizide", "gliclazide")
    ) else 1.0
    metformin = 1.05 if "metformin" in medications else 1.0
    return {
        "renal_clearance_factor": renal_factor,
        "insulin_action_factor": min(1.25, sulfonylurea * metformin),
        "hypoglycemia_sensitivity": sulfonylurea * renal_factor,
    }


def bergman_hovorka_step(
    glucose: float,
    gut: float,
    insulin_action: float,
    context: dict[str, Any],
    *,
    carbs: float = 0,
    activity: float = 1,
) -> tuple[float, float, float]:
    """Advance a bounded Bergman/Hovorka-inspired reduced compartment model."""
    dt = CONFIG["step_minutes"]
    profile = medication_profile(context)
    baseline = float(context.get("baseline", glucose))
    renal = profile["renal_clearance_factor"]
    action = profile["insulin_action_factor"]
    absorbed = gut * (1 - math.exp(-CONFIG["gut_rate"] * dt))
    meal_absorption = carbs * (1 - math.exp(-CONFIG["gut_rate"] * dt))
    insulin_action = max(
        0.0,
        insulin_action
        + dt * (0.015 * action / renal * (max(glucose - baseline, 0) / 100) - 0.01 * insulin_action),
    )
    insulin_effect = 0.12 * insulin_action * max(glucose - 70, 0)
    next_glucose = (
        glucose
        + dt * CONFIG["return_rate"] * (baseline - glucose)
        + 1.35 * (absorbed + meal_absorption)
        - dt * 0.18 * insulin_effect
        - dt * CONFIG["activity_gain"] * (activity - 1)
    )
    return (
        min(400, max(40, next_glucose)),
        max(0, gut - absorbed + carbs - meal_absorption),
        insulin_action,
    )


def hybrid_rollout(
    state: dict[str, Any],
    context: dict[str, Any],
    horizon: int,
    scenario: Any = None,
) -> list[dict[str, Any]]:
    g = float(state["glucose"])
    gut = float(state["gut"])
    action = float(state.get("insulin_action", 0))
    scenario_carbs = float(getattr(scenario, "carbs", 0)) * float(
        getattr(scenario, "glycemic_factor", 1)
    ) if scenario else 0
    scenario_activity = float(getattr(scenario, "activity", 1)) if scenario else 1
    duration = int(getattr(scenario, "duration", 0)) if scenario else 0
    points = []
    for minute in range(5, horizon + 1, 5):
        g, gut, action = bergman_hovorka_step(
            g,
            gut,
            action,
            context,
            carbs=scenario_carbs if minute == 5 else 0,
            activity=scenario_activity if minute <= duration else 1,
        )
        points.append({"minute": minute, "glucose": round(g, 3), "gut": gut})
    return points


def feature_vector(
    state: dict[str, Any], context: dict[str, Any], horizon: int
) -> np.ndarray:
    packet = state.get("last_packet") or {}
    prior = hybrid_rollout(state, context, horizon)[-1]["glucose"]
    profile = medication_profile(context)
    return np.asarray(
        [
            state["glucose"],
            state["trend"],
            state["gut"],
            state["baseline"],
            packet.get("hr") or 0,
            packet.get("hrv") or 0,
            packet.get("eda") or 0,
            packet.get("temperature") or 0,
            packet.get("activity", 1),
            prior,
            context.get("bmi", 0),
            context.get("waist_cm", 0),
            context.get("hba1c", 0),
            context.get("egfr", 90),
            profile["renal_clearance_factor"],
            profile["insulin_action_factor"],
        ],
        dtype=float,
    )


@dataclass
class HybridPredictor:
    residual: GradientBoostingRegressor
    lower: GradientBoostingRegressor
    upper: GradientBoostingRegressor
    high: GradientBoostingClassifier | None
    low: GradientBoostingClassifier | None
    horizon: int

    def predict(self, features: np.ndarray, prior: float) -> dict[str, float | None]:
        x = features.reshape(1, -1)
        prediction = float(prior + self.residual.predict(x)[0])
        low = float(self.lower.predict(x)[0])
        high = float(self.upper.predict(x)[0])
        result: dict[str, float | None] = {
            "prediction": min(400, max(40, prediction)),
            "lower": min(400, max(40, low)),
            "upper": min(400, max(40, high)),
            "above_180_probability": None,
            "below_70_probability": None,
        }
        if self.high:
            result["above_180_probability"] = float(self.high.predict_proba(x)[0, 1])
        if self.low:
            result["below_70_probability"] = float(self.low.predict_proba(x)[0, 1])
        return result


def train_predictor(
    states: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    context: dict[str, Any],
    horizon: int,
    train_indices: list[int],
) -> HybridPredictor:
    steps = horizon // 5
    x, residual_y, y = [], [], []
    for i in train_indices:
        if i + steps >= len(rows) or rows[i + steps].get("glucose") is None:
            continue
        prior = hybrid_rollout(states[i], context, horizon)[-1]["glucose"]
        x.append(feature_vector(states[i], context, horizon))
        residual_y.append(rows[i + steps]["glucose"] - prior)
        y.append(rows[i + steps]["glucose"])
    if len(x) < 20:
        raise ValueError("Insufficient training observations for hybrid predictor")
    x_array = np.asarray(x)
    residual = GradientBoostingRegressor(
        n_estimators=60, max_depth=2, learning_rate=0.04, random_state=42, loss="huber"
    ).fit(x_array, residual_y)
    lower = GradientBoostingRegressor(
        loss="quantile", alpha=0.1, n_estimators=60, max_depth=2, random_state=42
    ).fit(x_array, y)
    upper = GradientBoostingRegressor(
        loss="quantile", alpha=0.9, n_estimators=60, max_depth=2, random_state=42
    ).fit(x_array, y)
    labels_high = np.asarray(y) > 180
    labels_low = np.asarray(y) < 70
    high = (
        GradientBoostingClassifier(n_estimators=50, max_depth=2, random_state=42).fit(
            x_array, labels_high
        )
        if len(set(labels_high)) == 2
        else None
    )
    low = (
        GradientBoostingClassifier(n_estimators=50, max_depth=2, random_state=42).fit(
            x_array, labels_low
        )
        if len(set(labels_low)) == 2
        else None
    )
    return HybridPredictor(residual, lower, upper, high, low, horizon)
