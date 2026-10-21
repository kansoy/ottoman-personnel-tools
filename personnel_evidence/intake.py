"""Build source-only extraction units from the independent appearance pool.

This module intentionally does not import or query any personnel baseline,
canonical person table, or website dataset. An appearance is a source-local
unit, not an identity-resolution decision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_no}: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"line {line_no} is not an object")
            rows.append(row)
    return rows


def _read_selections(path: Path) -> list[dict[str, str]]:
    """Read explicit appearance/source IDs from JSON, JSONL, or newline text."""
    raw = path.read_text(encoding="utf-8")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = None
    if value is not None:
        if isinstance(value, dict):
            value = value.get("selections", value.get("selected", []))
        if not isinstance(value, list):
            raise ValueError("selection JSON must be a list or contain selections/selected")
        entries = value
    else:
        entries = []
        for line_no, line in enumerate(raw.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                entries.append(line)

    selections = []
    for item in entries:
        if isinstance(item, str):
            item = {"appearance_id": item}
        if not isinstance(item, dict):
            raise ValueError("each selection must be an ID string or object")
        appearance_id = str(item.get("appearance_id", "")).strip()
        source_id = str(item.get("source_id", "")).strip()
        if not appearance_id and not source_id:
            raise ValueError("selection needs appearance_id or source_id")
        selections.append({
            "appearance_id": appearance_id,
            "source_id": source_id,
            "reason": str(item.get("reason", "")),
            "selected_by": str(item.get("selected_by", "selection_file")),
        })
    return selections


def _selector_matches(row: dict[str, Any], selector: dict[str, str]) -> bool:
    return ((not selector["appearance_id"] or row.get("appearance_id") == selector["appearance_id"])
            and (not selector["source_id"] or row.get("source_id") == selector["source_id"]))


def build_units(
    pool_rows: list[dict[str, Any]],
    selections: list[dict[str, str]],
    *,
    include_flagged_boundaries: bool = False,
) -> list[dict[str, Any]]:
    """Return source-only units for explicit selections.

    Boundaries are admitted by default only when the pool records
    ``native_boundary_review_status == 'boundary_reviewed'``. Other rows may
    be included explicitly, but remain visibly flagged in every unit.
    """
    if not selections:
        raise ValueError("explicit appearance_id/source_id selection is required")

    seen_ids: set[str] = set()
    for row in pool_rows:
        appearance_id = str(row.get("appearance_id", ""))
        if not appearance_id:
            raise ValueError("pool row missing appearance_id")
        if appearance_id in seen_ids:
            raise ValueError(f"duplicate appearance_id in pool: {appearance_id}")
        seen_ids.add(appearance_id)

    chosen: list[tuple[dict[str, Any], list[dict[str, str]]]] = []
    for row in pool_rows:
        matched = [s for s in selections if _selector_matches(row, s)]
        if not matched:
            continue
        status = str(row.get("native_boundary_review_status") or "")
        if status != "boundary_reviewed" and not include_flagged_boundaries:
            raise ValueError(
                f"boundary not reviewed for {row['appearance_id']} ({status or 'status missing'}); "
                "select with include_flagged_boundaries only if the candidate should be retained"
            )
        chosen.append((row, matched))

    matched_selectors = {
        (s["appearance_id"], s["source_id"], s["reason"], s["selected_by"])
        for _, group in chosen for s in group
    }
    requested = {
        (s["appearance_id"], s["source_id"], s["reason"], s["selected_by"])
        for s in selections
    }
    unmatched = requested - matched_selectors
    if unmatched:
        ids = [x[0] or x[1] for x in sorted(unmatched)]
        raise ValueError("selection did not match a pool row: " + ", ".join(ids))

    units = []
    for row, selected_by in chosen:
        appearance_id = str(row["appearance_id"])
        source_id = str(row.get("source_id", ""))
        pdf_sha = str(row.get("pdf_sha256", ""))
        native_sha = str(row.get("source_native_sha256", ""))
        if not source_id:
            raise ValueError(f"{appearance_id}: missing source_id")
        if not SHA256.fullmatch(pdf_sha):
            raise ValueError(f"{appearance_id}: invalid or missing source PDF SHA256")
        if not SHA256.fullmatch(native_sha):
            raise ValueError(f"{appearance_id}: invalid or missing native-source SHA256")
        segments = row.get("segments")
        if not isinstance(segments, list) or not segments:
            raise ValueError(f"{appearance_id}: no source segments")
        body_segments = []
        for i, segment in enumerate(segments, 1):
            page = segment.get("pdf_page")
            text = segment.get("text_raw")
            if isinstance(page, bool) or not isinstance(page, int) or page < 1 or not isinstance(text, str) or not text:
                raise ValueError(f"{appearance_id}: invalid segment {i}; need positive PDF page and literal text")
            body_segments.append({
                "pdf_page": page,
                "printed_page": segment.get("printed_page"),
                "segment_id": segment.get("segment_id", ""),
                "source_offsets": segment.get("source_offsets", {}),
                "text_raw": text,
            })
        pages = sorted({x["pdf_page"] for x in body_segments})
        page_provenance = []
        for page in pages:
            page_provenance.append({
                "pdf_page": page,
                "segment_ids": [x["segment_id"] for x in body_segments if x["pdf_page"] == page],
                "printed_pages": list(dict.fromkeys(
                    x["printed_page"] for x in body_segments
                    if x["pdf_page"] == page and x["printed_page"] is not None
                )),
            })
        boundary_status = str(row.get("native_boundary_review_status") or "")
        units.append({
            # Runner-compatible unit key. It identifies this source appearance,
            # not a canonical historical person.
            "person_key": appearance_id,
            "appearance_id": appearance_id,
            "name": str(row.get("name_raw") or row.get("heading_raw") or ""),
            "section": str(row.get("entry_locator_raw") or row.get("entry_role") or ""),
            "source_id": source_id,
            "source_pdf_sha256": pdf_sha,
            "source_pdf_path": str(row.get("pdf_path") or ""),
            "source_native_path": str(row.get("source_native_path") or ""),
            "source_native_sha256": native_sha,
            "source_url": str(row.get("source_url") or ""),
            "source_title": str(row.get("title") or ""),
            "source_author": str(row.get("author") or ""),
            "source_year": row.get("year"),
            "entry_locator_raw": str(row.get("entry_locator_raw") or ""),
            "entry_role": str(row.get("entry_role") or ""),
            "evidence_form": str(row.get("evidence_form") or "unspecified_source_text"),
            "archive_refs_raw": row.get("archive_refs_raw", []),
            "archive_reference_status": str(row.get("archive_reference_status") or ""),
            "identity_resolution_status": str(row.get("identity_resolution_status") or "unresolved"),
            "identity_status": "source_appearance_not_merged",
            "complete_boundary_status": str(row.get("complete_boundary_status") or ""),
            "native_boundary_review_status": boundary_status,
            "boundary_gate": "reviewed" if boundary_status == "boundary_reviewed" else "flagged_candidate",
            "selection": [{
                "appearance_id": s["appearance_id"],
                "source_id": s["source_id"],
                "reason": s["reason"],
                "selected_by": s["selected_by"],
            } for s in selected_by],
            "pdf_pages": pages,
            "page_provenance": page_provenance,
            "body_segments": body_segments,
        })
    return units


def _write_jsonl(path: Path, units: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        for unit in units:
            handle.write(json.dumps(unit, ensure_ascii=False, separators=(",", ":")) + "\n")
    temp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="appearance-pool JSONL")
    parser.add_argument("--out", required=True, help="source-only extraction-unit JSONL")
    parser.add_argument("--appearance-id", action="append", default=[], help="explicit appearance ID; repeatable")
    parser.add_argument("--source-id", action="append", default=[], help="explicit source ID; selects its appearances; repeatable")
    parser.add_argument("--selection-file", help="JSON/JSONL/text with explicit appearance_id and/or source_id selections")
    parser.add_argument("--include-flagged-boundaries", action="store_true",
                        help="retain explicitly selected rows whose native boundaries are not marked reviewed")
    args = parser.parse_args(argv)
    selections = []
    for appearance_id in args.appearance_id:
        selections.append({"appearance_id": appearance_id, "source_id": "", "reason": "", "selected_by": "command_line"})
    for source_id in args.source_id:
        selections.append({"appearance_id": "", "source_id": source_id, "reason": "", "selected_by": "command_line"})
    if args.selection_file:
        selections.extend(_read_selections(Path(args.selection_file)))
    units = build_units(_read_jsonl(Path(args.input)), selections,
                        include_flagged_boundaries=args.include_flagged_boundaries)
    _write_jsonl(Path(args.out), units)
    print(json.dumps({"selected_appearances": len(units), "output": str(Path(args.out)),
                      "source_only": True, "identity_merge": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
