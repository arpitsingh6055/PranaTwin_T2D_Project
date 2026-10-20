"""Editable source for architecture and measured evaluation PDF figures."""

import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from engine.data import PROFILES, bundle

ROOT = Path(__file__).resolve().parents[1]


def build():
    (ROOT / "samples").mkdir(exist_ok=True)
    (ROOT / "samples/synthetic_fhir.json").write_text(
        json.dumps(bundle(PROFILES[0]), indent=2), encoding="utf8"
    )
    c = canvas.Canvas(str(ROOT / "docs/architecture.pdf"), pagesize=(960, 540))
    c.setFillColor(HexColor("#123b3c"))
    c.rect(0, 0, 960, 540, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 28)
    c.drawString(48, 478, "PranaTwin-T2D architecture")
    c.setFont("Helvetica", 12)
    c.drawString(
        48, 451, "Hybrid ML data flow | synthetic research only | version 0.2.0"
    )
    boxes = [
        (48, 320, 220, 75, "FHIR R4 document", "Historical glucose baseline"),
        (48, 190, 220, 75, "Synthetic telemetry", "5-minute packets + meal logs"),
        (
            340,
            255,
            245,
            90,
            "Causal state synchronizer",
            "Glucose, baseline, gut, quality",
        ),
        (
            660,
            320,
            250,
            75,
            "Hybrid forecast / scenarios",
            "Physiology prior + GBR residual",
        ),
        (660, 190, 250, 75, "React control room", "REST + WebSocket snapshots"),
        (340, 70, 245, 70, "Offline evaluation", "Purged ML + quantiles + Clarke"),
    ]
    for x, y, w, h, title, sub in boxes:
        c.setFillColor(HexColor("#eaf3f0"))
        c.roundRect(x, y, w, h, 8, fill=1, stroke=0)
        c.setFillColor(HexColor("#123b3c"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x + 14, y + h - 27, title)
        c.setFont("Helvetica", 10)
        c.drawString(x + 14, y + 21, sub)
    c.setStrokeColor(HexColor("#95c6ba"))
    c.setLineWidth(2)
    for x1, y1, x2, y2 in [
        (268, 355, 340, 320),
        (268, 225, 340, 280),
        (585, 320, 660, 355),
        (585, 280, 660, 225),
        (785, 320, 785, 265),
        (460, 255, 460, 140),
    ]:
        c.line(x1, y1, x2, y2)
    c.setFillColor(HexColor("#c1d8d1"))
    c.setFont("Helvetica", 11)
    c.drawString(
        48,
        35,
        "One FastAPI process serves the built UI. Consent gate protects all patient routes and streams.",
    )
    c.save()
    r = json.loads((ROOT / "reports/metrics.json").read_text())
    c = canvas.Canvas(str(ROOT / "reports/evaluation.pdf"), pagesize=(960, 540))
    c.setFillColor(HexColor("#f5f8f7"))
    c.rect(0, 0, 960, 540, fill=1, stroke=0)
    c.setFillColor(HexColor("#123b3c"))
    c.setFont("Helvetica-Bold", 26)
    c.drawString(48, 480, "Forecast error on synthetic holdout")
    c.setFont("Helvetica", 12)
    c.drawString(
        48,
        453,
        "RMSE (mg/dL) | 276 predictions per model/horizon | three fictional patients",
    )
    colors = ["#72878c", "#13796c", "#505fc4"]
    for n, method in enumerate(["persistence", "ridge", "reduced_order"]):
        metrics = [m for m in r["metrics"] if m["method"] == method]
        c.setFillColor(HexColor(colors[n]))
        c.setFont("Helvetica", 12)
        c.drawString(60 + n * 270, 408, method)
        for j, m in enumerate(metrics):
            x = 105 + j * 165 + n * 30
            h = m["rmse"] * 5.6
            c.rect(x, 110, 22, h, fill=1, stroke=0)
            c.setFont("Helvetica", 8)
            c.drawCentredString(x + 11, 115 + h, f"{m['rmse']:.1f}")
    c.setFillColor(HexColor("#123b3c"))
    c.setFont("Helvetica", 11)
    for j, h in enumerate([15, 30, 60, 90, 120]):
        c.drawCentredString(145 + j * 165, 86, f"{h} min")
    c.drawString(
        48,
        45,
        "Ridge performs best here. These synthetic results do not establish clinical validity.",
    )
    c.save()


if __name__ == "__main__":
    build()
