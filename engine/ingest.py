"""Normalize an authorized CSV without changing the raw source."""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from .model import Packet, initial, synchronize


def ingest(path: Path, source: str) -> dict:
    if source not in ("open-source", "synthetic"):
        raise ValueError("Unsupported source")
    rows = []
    state = initial(120)
    with path.open(encoding="utf8", newline="") as f:
        for i, raw in enumerate(csv.DictReader(f)):
            packet = {
                "timestamp": raw["timestamp"],
                "unit": raw["unit"],
                "source": source,
                "index": i,
            }
            for k in ("glucose", "hr", "hrv", "eda", "temperature"):
                packet[k] = float(raw[k]) if raw.get(k) else None
            packet["activity"] = float(raw.get("activity") or 1)
            packet["carbs"] = float(raw.get("carbs") or 0)
            p = Packet.model_validate(packet)
            if (
                state["timestamp"]
                and (
                    p.timestamp - datetime.fromisoformat(state["timestamp"])
                ).total_seconds()
                > 86400
            ):
                raise ValueError("Gap exceeds one day")
            state = synchronize(state, packet)
            rows.append({"packet": packet, "quality": state["quality"]})
    if not rows:
        raise ValueError("No rows")
    return {
        "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": source,
        "transformed_at": datetime.now(timezone.utc).isoformat(),
        "transform": "normalized-v1; no future interpolation",
        "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--source", choices=["open-source", "synthetic"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Output must differ from raw input")
    result = ingest(args.input, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf8")
