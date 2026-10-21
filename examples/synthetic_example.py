"""Invented demonstration, not a historical record or a model response."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from personnel_evidence import anchors, export, grounding, intake


TEXT = (
    "Örnek Kişi Hicri 1300 ve Rumi 1298 yılında örnek kaleme atandı; maaşı 0 kuruş olarak yazıldı.\n"
    "Bir ek ödeme zikredildi; miktarı kaydedilmedi.\n"
    "Tarihi kaydedilmeyen bir yer değiştirme notu vardır."
)


def pool_row():
    # There is no PDF behind this fixture. The hashes identify the invented
    # bytes and a separate invented native-text representation, not an archive.
    return {
        "appearance_id": "synthetic:appearance:001", "source_id": "synthetic:source:001",
        "name_raw": "Örnek Kişi (invented)", "entry_locator_raw": "invented entry 1",
        "entry_role": "synthetic_personnel_entry", "evidence_form": "synthetic_text",
        "pdf_sha256": hashlib.sha256(b"SYNTHETIC DOCUMENT; NO REAL PDF").hexdigest(),
        "source_native_sha256": hashlib.sha256(TEXT.encode()).hexdigest(),
        "pdf_path": "synthetic-document-not-a-real-pdf", "source_native_path": "synthetic_text",
        "source_url": "https://example.invalid/synthetic", "title": "Invented test document",
        "author": "Synthetic fixture", "year": "not historical",
        "archive_refs_raw": [], "archive_reference_status": "not_applicable_synthetic",
        "identity_resolution_status": "unresolved", "native_boundary_review_status": "boundary_reviewed",
        "segments": [{"segment_id": "synthetic:segment:001", "pdf_page": 1,
                      "printed_page": 1, "text_raw": TEXT}],
    }


def build_demo():
    unit = intake.build_units([pool_row()], [{
        "appearance_id": "synthetic:appearance:001", "source_id": "",
        "reason": "offline invented demonstration", "selected_by": "synthetic_example",
    }])[0]
    packet = anchors.prepare(unit)
    money_id = next(a["id"] for a in packet["money_anchors"] if a["amount"] == 0)
    raw = {
        "person_key": unit["person_key"], "facts": [], "events": [
            {"event_no": 1, "event_type": "appointment", "description": "invented appointment",
             "source_lines": ["L001"], "office_raw": "örnek kalem", "office_basis": "explicit",
             "dates": [
                 {"calendar": "hijri", "year": 1300, "year_basis": "literal", "source_lines": ["L001"]},
                 {"calendar": "rumi", "year": 1298, "year_basis": "literal", "source_lines": ["L001"]},
             ], "payments": [
                 {"pay_anchor_id": money_id, "component": "salary", "source_lines": ["L001"]},
                 {"component": "allowance", "basis": "unclear", "amount": None,
                  "source_lines": ["L002"], "warnings": ["amount_not_recorded"]},
             ]},
            {"event_no": 2, "event_type": "transfer", "description": "invented undated note",
             "source_lines": ["L003"], "office_basis": "not_recorded", "dates": [], "payments": []},
        ], "excluded_money": [], "warnings": ["synthetic_demo_not_historical"],
    }
    parsed, issues, evidence = grounding.ground(raw, unit, packet)
    result = {
        "request_id": "synthetic:manual-example:001", "person_key": unit["person_key"],
        "source_id": unit["source_id"], "source_pdf_sha256": unit["source_pdf_sha256"],
        "status": "completed", "requested_model": "none; hand-written synthetic example",
        "actual_model": "none", "review_status": "candidate_requires_source_review",
        "validation_errors": issues, "parsed": parsed,
    }
    return unit, packet, result, evidence


def write_demo(out: Path):
    if out.exists():
        raise ValueError("choose a new output directory; the demonstration will not overwrite one")
    out.mkdir(parents=True)
    unit, packet, result, evidence = build_demo()
    for name, value in [("synthetic-result.json", result), ("synthetic-packet.json", packet),
                        ("synthetic-evidence.json", evidence)]:
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    (out / "units.jsonl").write_text(json.dumps(unit, ensure_ascii=False) + "\n")
    tables, counts = export.collect_records([unit], [out / "synthetic-result.json"])
    db = export.write_export(out / "export", tables)
    return {"synthetic_only": True, "network_used": False, "database": str(db),
            "candidates": len(tables["candidates"]), "events": len(tables["events"]),
            "payments": len(tables["payments"]), "event_dates": len(tables["event_dates"]),
            "validation_issues": result["validation_errors"]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    print(json.dumps(write_demo(p.parse_args().out), ensure_ascii=False, indent=2))
