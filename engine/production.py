"""Local production primitives: durable provenance, audit, and provider adapters."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import Packet


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalStore:
    """A small SQLite boundary for single-host deployments.

    SQLite is deliberately used instead of a mandatory external database. The
    schema can be migrated to PostgreSQL later without changing API contracts.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS ingestion_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_uri TEXT,
                    sha256 TEXT NOT NULL,
                    packet_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    patient_id TEXT,
                    actor TEXT NOT NULL,
                    request_id TEXT,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def connection(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def record_batch(
        self,
        patient_id: str,
        source: str,
        packets: list[dict[str, Any]],
        source_uri: str | None = None,
    ) -> dict[str, Any]:
        canonical = json.dumps(packets, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(canonical).hexdigest()
        created_at = utc_now()
        with self.connection() as db:
            cursor = db.execute(
                """
                INSERT INTO ingestion_batches
                (patient_id, source, source_uri, sha256, packet_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (patient_id, source, source_uri, digest, len(packets), created_at),
            )
        return {
            "id": cursor.lastrowid,
            "patient_id": patient_id,
            "source": source,
            "source_uri": source_uri,
            "sha256": digest,
            "packet_count": len(packets),
            "created_at": created_at,
        }

    def audit(
        self,
        event: str,
        actor: str,
        detail: dict[str, Any],
        patient_id: str | None = None,
        request_id: str | None = None,
    ) -> None:
        with self.connection() as db:
            db.execute(
                """
                INSERT INTO audit_events
                (event, patient_id, actor, request_id, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event,
                    patient_id,
                    actor,
                    request_id,
                    json.dumps(detail, sort_keys=True),
                    utc_now(),
                ),
            )


def normalize_wearable_payload(value: Any, patient_id: str) -> list[dict[str, Any]]:
    """Normalize common GET/API payload shapes into the packet contract.

    Provider-specific authentication and field mapping belong at the edge. This
    adapter accepts a list, ``{"data": [...]}``, or ``{"records": [...]}``,
    and rejects ambiguous or unsafe values rather than guessing units.
    """
    if isinstance(value, dict):
        records = value.get("data", value.get("records"))
    else:
        records = value
    if not isinstance(records, list) or not records:
        raise ValueError("Expected a non-empty data or records array")
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("Each wearable record must be an object")
        item = dict(record)
        item["index"] = index
        item.setdefault("source", "authorized-api")
        if item.get("patient_id", patient_id) != patient_id:
            raise ValueError("Record patient_id does not match request patient")
        item.pop("patient_id", None)
        try:
            packet = Packet.model_validate(item)
        except Exception as exc:
            raise ValueError(f"Invalid wearable record at index {index}") from exc
        if packet.unit != "mg/dL":
            raise ValueError(f"Unsupported glucose unit at index {index}")
        normalized.append(packet.model_dump(mode="json"))
    return normalized


def validate_fhir_bundle(value: Any) -> dict[str, Any]:
    """Validate the local FHIR structural subset before clinical processing."""
    from .data import validate_bundle

    if not isinstance(value, dict):
        raise ValueError("FHIR payload must be a JSON object")
    result = validate_bundle(value)
    if not result["passed"]:
        raise ValueError("FHIR structural validation failed")
    return result
