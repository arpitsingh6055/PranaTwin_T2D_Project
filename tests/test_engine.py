import copy
import math
from datetime import timedelta
import pytest
from engine.data import (
    PROFILES,
    telemetry,
    bundle,
    validate_bundle,
    baseline_from_bundle,
)
from engine.model import (
    initial,
    synchronize,
    forecast,
    transition,
    counterfactual,
    Scenario,
)
from engine.evaluate import split_indices, event_metrics, evaluate


def state_at(index=156):
    state = initial(145)
    for row in telemetry(PROFILES[0])[: index + 1]:
        state = synchronize(state, row)
    return state


def test_generator_determinism_and_invariants():
    a = telemetry(PROFILES[0])
    assert a == telemetry(PROFILES[0])
    assert a != telemetry(PROFILES[0], 43)
    assert len(a) == 2880
    assert all(r["glucose"] is None or 40 <= r["glucose"] <= 400 for r in a)
    assert all(a[i]["timestamp"] < a[i + 1]["timestamp"] for i in range(len(a) - 1))


@pytest.mark.parametrize("p", PROFILES)
def test_fhir(p):
    b = bundle(p)
    assert validate_bundle(b)["passed"]
    assert not validate_bundle(b)["abdm_conformant"]
    assert baseline_from_bundle(b) == p["baseline"]
    bad = copy.deepcopy(b)
    bad["entry"][0]["resource"]["subject"]["reference"] = "urn:uuid:missing"
    assert not validate_bundle(bad)["passed"]
    bad = copy.deepcopy(b)
    bad["entry"].reverse()
    assert not validate_bundle(bad)["passed"]


def test_causal_state_and_ehr_fusion():
    rows = telemetry(PROFILES[0])
    s = initial(145)
    for i, row in enumerate(rows[:30]):
        old = copy.deepcopy(s)
        s = synchronize(s, row)
        assert s["version"] == i + 1
        assert s["timestamp"] == row["timestamp"]
        assert old != s
    future = copy.deepcopy(rows)
    future[30]["glucose"] = 390
    t = initial(145)
    for row in future[:30]:
        t = synchronize(t, row)
    assert t == s
    other = initial(90)
    for row in rows[:30]:
        other = synchronize(other, row)
    assert forecast(other)["points"] != forecast(s)["points"]


def test_quality_and_invalid_packets():
    row = telemetry(PROFILES[0])[0]
    s = synchronize(initial(145), row)
    for patch in (
        {"timestamp": row["timestamp"]},
        {"timestamp": "2026-09-01T00:00:00+05:30"},
        {"timestamp": "2026-10-02T00:00:00"},
        {"unit": "mmol/L"},
        {"glucose": 900},
        {"glucose": float("nan")},
    ):
        with pytest.raises(ValueError):
            synchronize(s, {**row, **patch})
    missing = {
        **row,
        "timestamp": "2026-10-01T00:20:00+05:30",
        "glucose": None,
        "hr": None,
    }
    bad = synchronize(s, missing)
    assert "sensor_gap" in bad["quality"]
    assert "missing_hr" in bad["quality"]
    with pytest.raises(ValueError, match="stale"):
        forecast(bad)


@pytest.mark.parametrize("h", [15, 30, 60, 90, 120])
def test_forecast(h):
    s = state_at()
    before = copy.deepcopy(s)
    f = forecast(s, h)
    assert len(f["points"]) == h // 5
    assert f["points"][-1]["minute"] == h
    assert f["unit"] == "mg/dL"
    assert s == before
    from datetime import datetime

    assert datetime.fromisoformat(
        f["points"][-1]["timestamp"]
    ) - datetime.fromisoformat(s["timestamp"]) == timedelta(minutes=h)
    assert f["uncertainty"]["status"] == "unavailable"
    assert f["event_probability"] is None


def test_stability_and_zero_inputs():
    g, gut = 145, 0
    for _ in range(5000):
        g, gut = transition(g, gut, 145)
    assert g == 145 and gut == 0
    for g0 in (40, 400):
        g, gut = g0, 120
        for _ in range(1000):
            g, gut = transition(g, gut, 200, 5)
            assert math.isfinite(g)
            assert 40 <= g <= 400
            assert gut >= 0


def test_scenarios_same_initial_state():
    s = state_at()
    before = copy.deepcopy(s)
    zero = counterfactual(s, Scenario())
    assert zero["baseline"] == zero["alternative"]
    changed = counterfactual(s, Scenario(carbs=60))
    assert changed["baseline"]["origin"] == changed["alternative"]["origin"]
    assert changed["delta_peak"] != 0
    assert s == before
    with pytest.raises(ValueError):
        Scenario(carbs=121)
    with pytest.raises(ValueError):
        Scenario(activity=0)


def test_split_no_overlap():
    split = split_indices(2880)
    assert max(split["train"]) + 24 < min(split["validation"])
    assert max(split["validation"]) + 24 < min(split["test"])
    assert all(i < j for i, j in zip(split["test"], split["test"][1:]))


def test_event_edges():
    m = event_metrics([70, 180], [70, 180], 180)
    assert m["positive_count"] == 0
    assert m["sensitivity"] is None
    assert m["auroc"] is None
    low = event_metrics([69, 70, 71], [60, 70, 80], 70, False)
    assert low["positive_count"] == 1
    assert low["sensitivity"] == 1


def test_evaluation_executes(tmp_path):
    result = evaluate(tmp_path)
    assert len(result["metrics"]) == 15
    assert (tmp_path / "predictions.csv").is_file()
    assert len(result["dataset_sha256"]) == 64
    assert all(m["n"] > 0 and math.isfinite(m["rmse"]) for m in result["metrics"])
