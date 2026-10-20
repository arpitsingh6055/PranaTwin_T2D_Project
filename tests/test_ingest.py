import pytest
from engine.ingest import ingest


def test_ingestion_preserves_raw_and_flags_missing(tmp_path):
    p = tmp_path / "raw.csv"
    raw = "timestamp,glucose,unit,hr\n2026-10-01T00:00:00+05:30,120,mg/dL,72\n2026-10-01T00:10:00+05:30,,mg/dL,\n"
    p.write_text(raw)
    result = ingest(p, "open-source")
    assert p.read_text() == raw
    assert result["source"] == "open-source"
    assert "irregular_sampling" in result["rows"][1]["quality"]
    assert "missing_glucose" in result["rows"][1]["quality"]
    p.write_text(raw + raw.splitlines()[1] + "\n")
    with pytest.raises(ValueError):
        ingest(p, "open-source")
