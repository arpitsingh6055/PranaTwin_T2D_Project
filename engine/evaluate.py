"""Chronological evaluation with 120-minute purges. Synthetic evidence only."""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score
from .data import PROFILES, telemetry, bundle, baseline_from_bundle
from .model import initial, synchronize, forecast, CONFIG
from .hybrid import train_predictor, feature_vector, hybrid_rollout

ROOT = Path(__file__).resolve().parents[1]
HORIZONS = [15, 30, 60, 90, 120]


def clarke_zone(reference: float, predicted: float) -> str:
    """Return the standard Clarke Error Grid zone for one glucose pair."""
    if reference < 70:
        if predicted <= 70:
            return "A"
        if predicted <= 180:
            return "B"
        return "E" if predicted > 180 and reference < 70 else "C"
    if reference > 180:
        if predicted >= 70:
            return "A" if abs(predicted - reference) <= 0.2 * reference else "B"
        return "E" if predicted < 70 else "C"
    if 0.8 * reference <= predicted <= 1.2 * reference:
        return "A"
    if 70 <= predicted <= 180:
        return "B"
    return "C"


def split_indices(n: int) -> dict:
    a = int(n * 0.6)
    b = int(n * 0.8)
    return {
        "train": list(range(12, a - 24)),
        "validation": list(range(a, b - 24)),
        "test": list(range(b, n - 24)),
        "purge_steps": 24,
        "train_boundary": a,
        "test_boundary": b,
    }


def event_metrics(y, pred, threshold, high=True):
    truth = np.asarray(y) > threshold if high else np.asarray(y) < threshold
    flag = np.asarray(pred) > threshold if high else np.asarray(pred) < threshold
    tp = int(np.sum(truth & flag))
    tn = int(np.sum(~truth & ~flag))
    fp = int(np.sum(~truth & flag))
    fn = int(np.sum(truth & ~flag))

    def div(a, b):
        return a / b if b else None

    score = np.asarray(pred) if high else -np.asarray(pred)
    return dict(
        positive_count=int(truth.sum()),
        negative_count=int((~truth).sum()),
        sensitivity=div(tp, tp + fn),
        specificity=div(tn, tn + fp),
        precision=div(tp, tp + fp),
        npv=div(tn, tn + fn),
        auroc=float(roc_auc_score(truth, score)) if len(set(truth)) == 2 else None,
        auprc=float(average_precision_score(truth, score))
        if len(set(truth)) == 2
        else None,
        brier=None,
        brier_reason="No probabilistic model; do not treat flags as probabilities",
        tp=tp,
        tn=tn,
        fp=fp,
        fn=fn,
    )


def summarize(records):
    y = np.array([r["truth"] for r in records])
    p = np.array([r["prediction"] for r in records])
    err = p - y
    return dict(
        n=len(y),
        mae=float(np.mean(abs(err))),
        rmse=float(np.sqrt(np.mean(err**2))),
        mard=float(np.mean(abs(err) / y) * 100),
        high=event_metrics(y, p, 180),
        low=event_metrics(y, p, 70, False),
        clarke={
            zone: sum(clarke_zone(float(a), float(b)) == zone for a, b in zip(y, p))
            / len(y)
            for zone in ("A", "B", "C", "D", "E")
        },
    )


def evaluate(output: Path | None = None) -> dict:
    output = output or ROOT / "reports"
    output.mkdir(exist_ok=True, parents=True)
    records = []
    manifest = []
    digest = hashlib.sha256()
    for profile in PROFILES:
        rows = telemetry(profile)
        digest.update(json.dumps(rows, sort_keys=True).encode())
        state = initial(baseline_from_bundle(bundle(profile)))
        states = []
        features = []
        for row in rows:
            state = synchronize(state, row)
            states.append(state)
            features.append(
                [
                    state["glucose"],
                    state["trend"],
                    state["gut"],
                    state["baseline"],
                    row["activity"],
                    row["hr"],
                ]
            )
        split = split_indices(len(rows))
        manifest.append(
            {
                "patient": profile["id"],
                "rows": len(rows),
                "split": {
                    k: (len(v) if isinstance(v, list) else v) for k, v in split.items()
                },
                "last_train_target": rows[split["train"][-1] + 24]["timestamp"],
                "first_validation_origin": rows[split["validation"][0]]["timestamp"],
                "last_validation_target": rows[split["validation"][-1] + 24][
                    "timestamp"
                ],
                "first_test_origin": rows[split["test"][0]]["timestamp"],
            }
        )
        x = np.array(features)
        for horizon in HORIZONS:
            steps = horizon // 5
            train = [
                i
                for i in split["train"]
                if rows[i + steps]["glucose"] is not None
                and rows[i]["glucose"] is not None
            ]
            y = np.array([rows[i + steps]["glucose"] for i in train])
            ridge = make_pipeline(StandardScaler(), Ridge(alpha=10))
            ridge.fit(x[train], y)
            hybrid = train_predictor(
                states,
                rows,
                profile,
                horizon,
                split["train"],
            )
            for i in split["test"][::6]:
                truth = rows[i + steps]["glucose"]
                if truth is None:
                    continue
                estimates = {
                    "persistence": states[i]["glucose"],
                    "ridge": float(ridge.predict(x[i : i + 1])[0]),
                    "reduced_order": forecast(states[i], horizon)["points"][-1][
                        "glucose"
                    ],
                    "hybrid": hybrid.predict(
                        feature_vector(states[i], profile, horizon),
                        hybrid_rollout(states[i], profile, horizon)[-1]["glucose"],
                    )["prediction"],
                }
                for method, prediction in estimates.items():
                    records.append(
                        dict(
                            patient=profile["id"],
                            origin=rows[i]["timestamp"],
                            target=rows[i + steps]["timestamp"],
                            horizon=horizon,
                            method=method,
                            truth=truth,
                            prediction=prediction,
                            quality="missing_glucose"
                            if rows[i]["glucose"] is None
                            else "complete",
                            event="event" if truth > 180 or truth < 70 else "in_range",
                            source="synthetic",
                        )
                    )
    metrics = []
    for method in ("persistence", "ridge", "reduced_order", "hybrid"):
        for horizon in HORIZONS:
            group = [
                r for r in records if r["method"] == method and r["horizon"] == horizon
            ]
            metrics.append(dict(method=method, horizon=horizon, **summarize(group)))
    slices = []
    for field in ("patient", "quality", "event"):
        for value in sorted({r[field] for r in records}):
            for method in ("persistence", "ridge", "reduced_order", "hybrid"):
                group = [
                    r for r in records if r[field] == value and r["method"] == method
                ]
                slices.append(
                    dict(field=field, value=value, method=method, **summarize(group))
                )
    result = dict(
        model_version="0.2.0-hybrid-gbr",
        generated_at=datetime.now(timezone.utc).isoformat(),
        source="synthetic",
        dataset_sha256=digest.hexdigest(),
        seed=42,
        config=CONFIG,
        patient_count=3,
        rows=8640,
        protocol="Within-patient chronological 60/20/20; 24-step purges before validation and test; test origins every 30 minutes. Ridge and hybrid preprocessing fitted on training only. Validation partition reserved, not used for tuning.",
        limitations=[
            "Synthetic generator is not physiological truth. No clinical validation.",
            "Test windows overlap within holdout; no independence claim.",
            "No new-patient or real-world generalization evidence.",
            "Reduced-order model cannot anticipate unannounced meals or artificial low scenarios.",
            "Quantile intervals and event probabilities are research outputs and are not clinically calibrated.",
            "Clarke Error Grid categories are reported as research error analysis, not a clinical safety certification.",
        ],
        manifest=manifest,
        metrics=metrics,
        slices=slices,
        uncertainty="unavailable",
    )
    (output / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf8")
    with (output / "predictions.csv").open("w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    return result


if __name__ == "__main__":
    r = evaluate()
    for m in r["metrics"]:
        print(
            m["method"],
            m["horizon"],
            "MAE",
            round(m["mae"], 2),
            "RMSE",
            round(m["rmse"], 2),
            "n",
            m["n"],
        )
