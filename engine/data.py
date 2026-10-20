"""Deterministic fictional cohort. No inferred ethnicity or drug response."""

import math
import random
from datetime import datetime, timedelta
from uuid import uuid5, NAMESPACE_URL

START = datetime.fromisoformat("2026-10-01T00:00:00+05:30")
PROFILES = [
    dict(
        id="PT-IND-001",
        context="T2D / hypertension / CKD context",
        age=58,
        bmi=27.1,
        waist_cm=98,
        hba1c=8.1,
        egfr=54,
        baseline=145,
        diagnoses=[
            "Type 2 diabetes mellitus",
            "Hypertension",
            "Chronic kidney disease",
        ],
        medications=["Metformin (historical, illustrative)"],
        shift_work=False,
    ),
    dict(
        id="PT-IND-002",
        context="T2D / lower BMI / central adiposity context",
        age=44,
        bmi=22.4,
        waist_cm=91,
        hba1c=7.4,
        egfr=92,
        baseline=125,
        diagnoses=["Type 2 diabetes mellitus"],
        medications=["Metformin (historical, illustrative)"],
        shift_work=False,
    ),
    dict(
        id="PT-IND-003",
        context="Prediabetes / rotating shift work context",
        age=36,
        bmi=24.2,
        waist_cm=88,
        hba1c=6.1,
        egfr=105,
        baseline=105,
        diagnoses=["Prediabetes"],
        medications=[],
        shift_work=True,
    ),
]


def telemetry(profile: dict, seed: int = 42, days: int = 10) -> list[dict]:
    rng = random.Random(seed + int(profile["id"][-1]))
    rows = []
    for i in range(days * 288):
        minute = (i * 5) % 1440
        meal_times = [480, 780, 1200] if not profile["shift_work"] else [60, 660, 1080]
        pulses = sum(
            75 * math.exp(-(((minute - m - 50) / 65) ** 2)) for m in meal_times
        )
        low = (
            95 * math.exp(-(((minute - 1020) / 35) ** 2))
            if profile["id"].endswith("001")
            else 0
        )
        glucose = max(
            45,
            min(
                350,
                profile["baseline"]
                + pulses
                + 8 * math.sin(i / 28)
                - low
                + rng.gauss(0, 3),
            ),
        )
        active = 3.0 if 850 <= minute <= 875 else 1.0
        rows.append(
            dict(
                timestamp=(START + timedelta(minutes=i * 5)).isoformat(),
                glucose=round(glucose, 2) if i % 401 != 400 else None,
                unit="mg/dL",
                hr=round(72 + 10 * (active - 1) + rng.gauss(0, 2), 1),
                hrv=round(40 + rng.gauss(0, 3), 1),
                eda=round(0.5 + rng.random() * 0.2, 3),
                temperature=round(33 + rng.gauss(0, 0.2), 2),
                activity=active,
                carbs=65.0 if minute in meal_times else 0.0,
                source="synthetic",
                index=i,
            )
        )
    return rows


def bundle(profile: dict) -> dict:
    def uid(name):
        return str(uuid5(NAMESPACE_URL, profile["id"] + "/" + name))

    def ref(name):
        return {"reference": "urn:uuid:" + uid(name)}

    resources = []

    def add(name, resource):
        resource["id"] = uid(name)
        resources.append({"fullUrl": "urn:uuid:" + uid(name), "resource": resource})

    narrative = {
        "status": "generated",
        "div": '<div xmlns="http://www.w3.org/1999/xhtml">Synthetic research record. Not for patient care.</div>',
    }
    add(
        "composition",
        dict(
            resourceType="Composition",
            status="final",
            type={"text": "Synthetic outpatient research summary"},
            date=START.isoformat(),
            title="Synthetic outpatient summary",
            subject=ref("patient"),
            author=[ref("organization")],
            text=narrative,
            section=[],
        ),
    )
    add(
        "patient",
        dict(
            resourceType="Patient",
            identifier=[
                {
                    "system": "https://pranatwin.example/synthetic",
                    "value": profile["id"],
                }
            ],
            birthDate=f"{2026 - profile['age']}-01-01",
            text=narrative,
        ),
    )
    add(
        "organization",
        dict(
            resourceType="Organization", name="Fictional research sandbox", active=True
        ),
    )
    for i, diagnosis in enumerate(profile["diagnoses"]):
        add(
            "condition" + str(i),
            dict(
                resourceType="Condition",
                clinicalStatus={
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                        }
                    ]
                },
                code={"text": diagnosis},
                subject=ref("patient"),
            ),
        )
    for name, value, unit, code in [
        ("HbA1c", profile["hba1c"], "%", "4548-4"),
        ("BMI", profile["bmi"], "kg/m2", None),
        ("Waist", profile["waist_cm"], "cm", None),
        ("eGFR", profile["egfr"], "mL/min/{1.73_m2}", None),
        ("Historical glucose baseline", profile["baseline"], "mg/dL", None),
    ]:
        coding = {"text": name}
        if code:
            coding["coding"] = [{"system": "http://loinc.org", "code": code}]
        add(
            name,
            dict(
                resourceType="Observation",
                status="final",
                code=coding,
                subject=ref("patient"),
                effectiveDateTime=START.isoformat(),
                valueQuantity={
                    "value": value,
                    "unit": unit,
                    "system": "http://unitsofmeasure.org",
                    "code": unit,
                },
            ),
        )
    for i, med in enumerate(profile["medications"]):
        add(
            "med" + str(i),
            dict(
                resourceType="MedicationRequest",
                status="completed",
                intent="order",
                medicationCodeableConcept={"text": med},
                subject=ref("patient"),
                authoredOn=START.isoformat(),
                requester=ref("organization"),
            ),
        )
    resources[0]["resource"]["section"] = [
        {
            "title": "Synthetic context",
            "text": narrative,
            "entry": [{"reference": e["fullUrl"]} for e in resources[3:]],
        }
    ]
    return dict(
        resourceType="Bundle",
        id=uid("bundle"),
        type="document",
        identifier={
            "system": "https://pranatwin.example/documents",
            "value": uid("bundle"),
        },
        timestamp=START.isoformat(),
        meta={"lastUpdated": START.isoformat()},
        entry=resources,
    )


def validate_bundle(value: dict) -> dict:
    errors = []
    entries = value.get("entry", [])
    if value.get("resourceType") != "Bundle" or value.get("type") != "document":
        errors.append("Expected document Bundle")
    if (
        not entries
        or entries[0].get("resource", {}).get("resourceType") != "Composition"
    ):
        errors.append("Composition must be first")
    if not value.get("identifier", {}).get("value") or not value.get("timestamp"):
        errors.append("Missing identifier/timestamp")
    urls = [e.get("fullUrl", "") for e in entries]
    if len(set(urls)) != len(urls):
        errors.append("Duplicate fullUrl")
    for url in urls:
        if not url.startswith("urn:uuid:"):
            errors.append("Expected UUID fullUrl")

    def visit(obj):
        if isinstance(obj, dict):
            if "reference" in obj and obj["reference"] not in urls:
                errors.append("Unresolved reference")
            for v in obj.values():
                visit(v)
        elif isinstance(obj, list):
            for v in obj:
                visit(v)

    visit(value)
    for e in entries:
        r = e["resource"]
        if r["resourceType"] == "Observation" and not all(
            k in r.get("valueQuantity", {}) for k in ("value", "unit", "system", "code")
        ):
            errors.append("Quantity missing units")
    return {
        "passed": not errors,
        "errors": errors,
        "scope": "Local structural checks only; no full FHIR/ABDM profile or terminology validation",
        "abdm_conformant": False,
    }


def baseline_from_bundle(value: dict) -> float:
    if not validate_bundle(value)["passed"]:
        raise ValueError("Invalid bundle")
    return next(
        e["resource"]["valueQuantity"]["value"]
        for e in value["entry"]
        if e["resource"].get("code", {}).get("text") == "Historical glucose baseline"
    )
