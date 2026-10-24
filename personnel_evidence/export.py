"""Export completed source-local candidates to SQLite and flat CSV relations.

Exports are candidate readings for review. They do not merge identities,
adjudicate historical truth, construct annual observations, or carry pay across
years. This module uses only the intake units and this package's result files.
"""
from __future__ import annotations

import argparse
import csv
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any

from . import anchors


TABLE_COLUMNS = {
    "candidates": [
        "candidate_id", "source_person_id", "appearance_id", "source_id", "source_pdf_sha256",
        "source_native_sha256", "name", "section", "source_title", "source_author", "source_year",
        "entry_locator_raw", "entry_role", "evidence_form", "archive_refs_raw_json",
        "archive_reference_status", "identity_resolution_status", "identity_status",
        "native_boundary_review_status", "boundary_gate", "selection_json", "source_pdf_path",
        "source_native_path", "source_url", "pdf_pages_json", "requested_model", "actual_model",
        "result_status", "review_status", "historical_status", "validation_errors_json",
        "extraction_warnings_json", "usage_priced_usd", "request_id",
    ],
    "facts": [
        "candidate_id", "source_person_id", "fact_index", "field", "value_raw", "related_name",
        "detail", "date_raw", "quote", "source_lines_json", "pdf_pages_json", "citation_status",
    ],
    "events": [
        "candidate_id", "source_person_id", "event_id", "event_index", "event_no", "event_type", "description",
        "date_raw", "dates_json", "end_date_raw", "end_dates_json", "office_raw", "title_raw",
        "place_raw", "locality_raw", "kaza_raw", "sancak_raw", "vilayet_raw", "institution_raw",
        "employer_raw", "ministry_raw", "authority_raw", "office_basis", "context_quote",
        "office_reference_event_no", "age_raw", "age", "duration_raw", "status", "honorary",
        "award_raw", "grade_raw", "grade", "legal_outcome", "office_relation", "document_number_raw",
        "reason_raw", "source_quote", "source_lines_json", "context_lines_json", "pdf_pages_json",
        "warnings_json", "citation_status", "payload_json",
    ],
    "payments": [
        "candidate_id", "source_person_id", "event_id", "event_index", "event_no", "payment_index", "payment_id", "component",
        "term_raw", "amount_literal", "amount", "currency_raw", "subunit_amount_literal",
        "subunit_amount", "subunit_currency_raw", "frequency_raw", "basis", "reference_event_no",
        "amount_scope", "amount_role", "recipient_raw", "reuse_reason", "paid_amount", "pay_anchor_id",
        "quote", "source_lines_json", "pdf_pages_json", "reading_flags_json", "warnings_json",
        "citation_status", "payload_json",
    ],
    "event_dates": [
        "candidate_id", "source_person_id", "event_id", "event_index", "event_no", "date_role",
        "date_index", "date_group_id", "calendar_pair_status", "calendar", "year", "proposed_year",
        "month", "day", "year_basis", "calendar_basis", "year_abbreviated", "date_raw",
        "date_quote", "context_quote", "reference_event_no", "source_lines_json",
        "context_lines_json", "pdf_pages_json", "citation_status",
    ],
}

CREATE_SQL = {
    "candidates": """CREATE TABLE candidates (
        candidate_id TEXT PRIMARY KEY,
        source_person_id TEXT NOT NULL,
        appearance_id TEXT NOT NULL,
        source_id TEXT NOT NULL,
        source_pdf_sha256 TEXT NOT NULL,
        source_native_sha256 TEXT,
        name TEXT, section TEXT, source_title TEXT, source_author TEXT, source_year TEXT,
        entry_locator_raw TEXT, entry_role TEXT, evidence_form TEXT,
        archive_refs_raw_json TEXT, archive_reference_status TEXT,
        identity_resolution_status TEXT, identity_status TEXT,
        native_boundary_review_status TEXT, boundary_gate TEXT, selection_json TEXT,
        source_pdf_path TEXT, source_native_path TEXT, source_url TEXT, pdf_pages_json TEXT,
        requested_model TEXT, actual_model TEXT, result_status TEXT NOT NULL,
        review_status TEXT NOT NULL, historical_status TEXT NOT NULL,
        validation_errors_json TEXT, extraction_warnings_json TEXT,
        usage_priced_usd TEXT, request_id TEXT
    )""",
    "facts": """CREATE TABLE facts (
        candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
        source_person_id TEXT NOT NULL, fact_index INTEGER NOT NULL,
        field TEXT, value_raw TEXT, related_name TEXT, detail TEXT, date_raw TEXT,
        quote TEXT, source_lines_json TEXT, pdf_pages_json TEXT, citation_status TEXT NOT NULL,
        PRIMARY KEY(candidate_id, fact_index)
    )""",
    "events": """CREATE TABLE events (
        candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
        source_person_id TEXT NOT NULL, event_id TEXT NOT NULL UNIQUE, event_index INTEGER NOT NULL, event_no INTEGER,
        event_type TEXT, description TEXT, date_raw TEXT, dates_json TEXT, end_date_raw TEXT,
        end_dates_json TEXT, office_raw TEXT, title_raw TEXT, place_raw TEXT, locality_raw TEXT,
        kaza_raw TEXT, sancak_raw TEXT, vilayet_raw TEXT, institution_raw TEXT, employer_raw TEXT,
        ministry_raw TEXT, authority_raw TEXT, office_basis TEXT, context_quote TEXT,
        office_reference_event_no INTEGER, age_raw TEXT, age TEXT, duration_raw TEXT, status TEXT,
        honorary TEXT, award_raw TEXT, grade_raw TEXT, grade TEXT, legal_outcome TEXT,
        office_relation TEXT, document_number_raw TEXT, reason_raw TEXT, source_quote TEXT,
        source_lines_json TEXT, context_lines_json TEXT, pdf_pages_json TEXT, warnings_json TEXT,
        citation_status TEXT NOT NULL, payload_json TEXT NOT NULL,
        PRIMARY KEY(candidate_id, event_index)
    )""",
    "payments": """CREATE TABLE payments (
        candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
        source_person_id TEXT NOT NULL, event_id TEXT NOT NULL REFERENCES events(event_id), event_index INTEGER NOT NULL, event_no INTEGER,
        payment_index INTEGER NOT NULL, payment_id TEXT NOT NULL UNIQUE, component TEXT, term_raw TEXT, amount_literal TEXT,
        amount TEXT, currency_raw TEXT, subunit_amount_literal TEXT, subunit_amount TEXT,
        subunit_currency_raw TEXT, frequency_raw TEXT, basis TEXT, reference_event_no INTEGER,
        amount_scope TEXT, amount_role TEXT, recipient_raw TEXT, reuse_reason TEXT, paid_amount TEXT,
        pay_anchor_id TEXT, quote TEXT, source_lines_json TEXT, pdf_pages_json TEXT,
        reading_flags_json TEXT, warnings_json TEXT, citation_status TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        PRIMARY KEY(candidate_id, event_index, payment_index)
    )""",
    "event_dates": """CREATE TABLE event_dates (
        candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
        source_person_id TEXT NOT NULL, event_id TEXT NOT NULL REFERENCES events(event_id),
        event_index INTEGER NOT NULL, event_no INTEGER, date_role TEXT NOT NULL,
        date_index INTEGER NOT NULL, date_group_id TEXT NOT NULL, calendar_pair_status TEXT NOT NULL,
        calendar TEXT, year INTEGER, proposed_year INTEGER, month INTEGER, day INTEGER,
        year_basis TEXT, calendar_basis TEXT, year_abbreviated INTEGER, date_raw TEXT,
        date_quote TEXT, context_quote TEXT, reference_event_no INTEGER,
        source_lines_json TEXT, context_lines_json TEXT, pdf_pages_json TEXT,
        citation_status TEXT NOT NULL,
        PRIMARY KEY(candidate_id, event_index, date_role, date_index)
    )""",
}

CAREER_OBSERVATIONS_VIEW_SQL = """CREATE VIEW career_observations AS
WITH date_summary AS (
    SELECT candidate_id, event_index,
           COALESCE(json_group_array(json_object(
               'date_index', date_index, 'date_group_id', date_group_id,
               'calendar_pair_status', calendar_pair_status, 'calendar', calendar,
               'year', year, 'proposed_year', proposed_year, 'month', month, 'day', day,
               'year_basis', year_basis, 'calendar_basis', calendar_basis,
               'year_abbreviated', year_abbreviated, 'reference_event_no', reference_event_no,
               'date_quote', date_quote, 'context_quote', context_quote,
               'source_lines', json(source_lines_json), 'context_lines', json(context_lines_json),
               'pdf_pages', json(pdf_pages_json), 'citation_status', citation_status
           )) FILTER (WHERE date_role='start'), '[]') AS start_date_variants_json,
           COALESCE(json_group_array(json_object(
               'date_index', date_index, 'date_group_id', date_group_id,
               'calendar_pair_status', calendar_pair_status, 'calendar', calendar,
               'year', year, 'proposed_year', proposed_year, 'month', month, 'day', day,
               'year_basis', year_basis, 'calendar_basis', calendar_basis,
               'year_abbreviated', year_abbreviated, 'reference_event_no', reference_event_no,
               'date_quote', date_quote, 'context_quote', context_quote,
               'source_lines', json(source_lines_json), 'context_lines', json(context_lines_json),
               'pdf_pages', json(pdf_pages_json), 'citation_status', citation_status
           )) FILTER (WHERE date_role='end'), '[]') AS end_date_variants_json,
           SUM(CASE WHEN date_role='start' THEN 1 ELSE 0 END) AS start_date_count,
           SUM(CASE WHEN date_role='end' THEN 1 ELSE 0 END) AS end_date_count,
           SUM(CASE WHEN year IS NULL THEN 1 ELSE 0 END) AS unresolved_year_count
    FROM event_dates
    GROUP BY candidate_id, event_index
)
SELECT e.candidate_id, e.source_person_id, e.event_id, e.event_index, e.event_no,
       c.name, c.section, c.source_id, c.source_pdf_sha256, c.source_native_sha256,
       c.source_title, c.source_author, c.review_status, c.historical_status,
       e.event_type, e.description, e.status AS event_status,
       e.date_raw AS start_date_raw, e.end_date_raw,
       COALESCE(d.start_date_variants_json, '[]') AS start_date_variants_json,
       COALESCE(d.end_date_variants_json, '[]') AS end_date_variants_json,
       COALESCE(d.start_date_count, 0) AS start_date_count,
       COALESCE(d.end_date_count, 0) AS end_date_count,
       COALESCE(d.unresolved_year_count, 0) AS unresolved_year_count,
       CASE WHEN COALESCE(d.start_date_count, 0) + COALESCE(d.end_date_count, 0)=0
            THEN 'undated_event'
            WHEN COALESCE(d.unresolved_year_count, 0)>0 THEN 'date_year_missing_or_unresolved'
            ELSE 'source_date_variants_recorded' END AS date_status,
       e.office_raw, e.title_raw, e.place_raw, e.locality_raw, e.kaza_raw, e.sancak_raw,
       e.vilayet_raw, e.institution_raw, e.employer_raw, e.ministry_raw, e.authority_raw,
       e.office_basis, e.context_quote, e.office_reference_event_no,
       e.reason_raw, e.legal_outcome, e.award_raw, e.grade_raw, e.document_number_raw,
       e.source_quote AS event_quote, e.source_lines_json AS event_source_lines_json,
       e.context_lines_json AS event_context_lines_json, e.pdf_pages_json AS event_pdf_pages_json,
       e.citation_status AS event_citation_status, e.warnings_json AS event_warnings_json,
       p.payment_index, p.payment_id, p.component AS payment_component, p.term_raw,
       p.amount_literal, p.amount, p.currency_raw, p.subunit_amount_literal, p.subunit_amount,
       p.subunit_currency_raw, p.frequency_raw, p.basis AS payment_basis,
       p.reference_event_no AS payment_reference_event_no, p.amount_scope, p.amount_role,
       p.recipient_raw, p.reuse_reason, p.paid_amount, p.pay_anchor_id,
       p.quote AS payment_quote, p.source_lines_json AS payment_source_lines_json,
       p.pdf_pages_json AS payment_pdf_pages_json, p.citation_status AS payment_citation_status,
       p.reading_flags_json, p.warnings_json AS payment_warnings_json
FROM events AS e
JOIN candidates AS c ON c.candidate_id=e.candidate_id
LEFT JOIN payments AS p ON p.candidate_id=e.candidate_id AND p.event_index=e.event_index
LEFT JOIN date_summary AS d ON d.candidate_id=e.candidate_id AND d.event_index=e.event_index
"""


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def scalar_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    return json_text(value)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_no}: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"line {line_no} is not an object")
            rows.append(row)
    return rows


def result_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    result_dir = path / "results" if (path / "results").is_dir() else path
    return sorted(result_dir.glob("*.json"))


def line_context(unit: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    packet = anchors.prepare(unit)
    lines = {str(row["id"]): row for row in packet["lines"]}
    money = {str(row["id"]): row for row in packet["money_anchors"]}
    return lines, money


def check_citation(
    source_lines: Any,
    quote: Any,
    claimed_pages: Any,
    line_map: dict[str, dict[str, Any]],
    *,
    fallback_lines: list[str] | None = None,
) -> tuple[str, list[str], list[int]]:
    ids = [str(x) for x in source_lines] if isinstance(source_lines, list) else []
    if not ids and fallback_lines:
        ids = [str(x) for x in fallback_lines]
    if not ids:
        return "missing_source_lines", ids, sorted({int(x) for x in (claimed_pages or []) if str(x).isdigit()})
    if any(x not in line_map for x in ids):
        return "invalid_source_lines", ids, sorted({int(x) for x in (claimed_pages or []) if str(x).isdigit()})
    positions = {line_id: i for i, line_id in enumerate(line_map)}
    lo, hi = min(positions[x] for x in ids), max(positions[x] for x in ids)
    ordered = list(line_map.values())[lo:hi + 1]
    exact_quote = "\n".join(x["text"] for x in ordered)
    pages = sorted({int(x["pdf_page"]) for x in ordered})
    pages_were_claimed = isinstance(claimed_pages, list) and bool(claimed_pages)
    claimed = sorted({int(x) for x in (claimed_pages or []) if str(x).isdigit()})
    if quote != exact_quote or (pages_were_claimed and claimed != pages):
        return "citation_mismatch", ids, pages
    return "source_lines_quote_pages_match", ids, pages


def _row(table: str, values: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(values.get(col) for col in TABLE_COLUMNS[table])


def _typed_integer(value: Any) -> int | None:
    """Keep year/month/day fields numeric only when the payload gives an integer."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _date_citation(
    date: dict[str, Any], line_map: dict[str, dict[str, Any]],
) -> tuple[str, list[str], list[str], list[int]]:
    source_ids = [str(x) for x in date.get("source_lines", [])]
    context_ids = [str(x) for x in date.get("context_lines", [])]
    date_status, source_ids, source_pages = check_citation(
        source_ids, date.get("date_quote"), None, line_map,
    )
    context_quote = date.get("context_quote")
    if context_quote or context_ids:
        context_status, context_ids, context_pages = check_citation(
            context_ids, context_quote, None, line_map,
        )
    else:
        context_status, context_pages = "context_not_recorded", []
    pages = sorted(set(source_pages) | set(context_pages))
    if date_status == "source_lines_quote_pages_match" and context_status in (
        "context_not_recorded", "source_lines_quote_pages_match",
    ):
        status = "source_lines_quote_pages_match"
    else:
        status = f"date:{date_status};context:{context_status}"
    return status, source_ids, context_ids, pages


def collect_records(units: list[dict[str, Any]], files: list[Path]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    unit_by_id: dict[str, dict[str, Any]] = {}
    line_maps = {}
    money_maps = {}
    for unit in units:
        key = str(unit.get("person_key") or unit.get("appearance_id") or "")
        if not key:
            raise ValueError("intake unit missing person_key/appearance_id")
        if key in unit_by_id:
            raise ValueError(f"duplicate intake source-person ID: {key}")
        unit_by_id[key] = unit
        line_maps[key], money_maps[key] = line_context(unit)

    tables = {name: [] for name in TABLE_COLUMNS}
    counts = {"read": 0, "completed": 0, "skipped_noncompleted": 0}
    candidate_ids: set[str] = set()
    for file in files:
        counts["read"] += 1
        try:
            result = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid result JSON in {file}: {exc.msg}") from exc
        if not isinstance(result, dict):
            raise ValueError(f"result is not an object: {file}")
        if result.get("status") != "completed":
            counts["skipped_noncompleted"] += 1
            continue
        parsed = result.get("parsed")
        if not isinstance(parsed, dict):
            counts["skipped_noncompleted"] += 1
            continue
        counts["completed"] += 1
        source_person_id = str(result.get("person_key") or parsed.get("person_key") or "")
        if not source_person_id or source_person_id not in unit_by_id:
            raise ValueError(f"completed candidate has no matching intake unit: {file.name}")
        unit = unit_by_id[source_person_id]
        if parsed.get("person_key") != source_person_id:
            raise ValueError(f"parsed person_key mismatch for {file.name}")
        for key in ("source_id", "source_pdf_sha256"):
            if result.get(key) != unit.get(key):
                raise ValueError(f"{key} mismatch between result and source unit for {file.name}")
        candidate_id = str(result.get("request_id") or file.stem)
        if candidate_id in candidate_ids:
            raise ValueError(f"duplicate candidate_id: {candidate_id}")
        candidate_ids.add(candidate_id)
        candidate = {
            "candidate_id": candidate_id,
            "source_person_id": source_person_id,
            "appearance_id": unit.get("appearance_id", source_person_id),
            "source_id": unit.get("source_id"),
            "source_pdf_sha256": unit.get("source_pdf_sha256"),
            "source_native_sha256": unit.get("source_native_sha256"),
            "name": unit.get("name"), "section": unit.get("section"),
            "source_title": unit.get("source_title"), "source_author": unit.get("source_author"),
            "source_year": scalar_text(unit.get("source_year")),
            "entry_locator_raw": unit.get("entry_locator_raw"), "entry_role": unit.get("entry_role"),
            "evidence_form": unit.get("evidence_form"),
            "archive_refs_raw_json": json_text(unit.get("archive_refs_raw", [])),
            "archive_reference_status": unit.get("archive_reference_status"),
            "identity_resolution_status": unit.get("identity_resolution_status"),
            "identity_status": unit.get("identity_status", "source_appearance_not_merged"),
            "native_boundary_review_status": unit.get("native_boundary_review_status"),
            "boundary_gate": unit.get("boundary_gate"),
            "selection_json": json_text(unit.get("selection", [])),
            "source_pdf_path": unit.get("source_pdf_path"), "source_native_path": unit.get("source_native_path"),
            "source_url": unit.get("source_url"), "pdf_pages_json": json_text(unit.get("pdf_pages", [])),
            "requested_model": result.get("requested_model"), "actual_model": result.get("actual_model"),
            "result_status": result.get("status"),
            "review_status": result.get("review_status") or "candidate_requires_source_review",
            "historical_status": "not_adjudicated_candidate",
            "validation_errors_json": json_text(result.get("validation_errors", [])),
            "extraction_warnings_json": json_text(parsed.get("warnings", [])),
            "usage_priced_usd": scalar_text(result.get("usage_priced_usd")),
            "request_id": result.get("request_id"),
        }
        tables["candidates"].append(candidate)

        line_map = line_maps[source_person_id]
        for fact_index, fact in enumerate(parsed.get("facts", [])):
            status, ids, pages = check_citation(fact.get("source_lines"), fact.get("quote"),
                                                fact.get("pdf_pages"), line_map)
            tables["facts"].append({
                "candidate_id": candidate_id, "source_person_id": source_person_id,
                "fact_index": fact_index, "field": fact.get("field"), "value_raw": fact.get("value_raw"),
                "related_name": fact.get("related_name"), "detail": fact.get("detail"),
                "date_raw": fact.get("date_raw"), "quote": fact.get("quote"),
                "source_lines_json": json_text(ids), "pdf_pages_json": json_text(pages),
                "citation_status": status,
            })

        for event_index, event in enumerate(parsed.get("events", [])):
            event_id = f"{candidate_id}:event:{event_index:04d}"
            status, ids, pages = check_citation(event.get("source_lines"), event.get("source_quote"),
                                                event.get("pdf_pages"), line_map)
            event_row = {
                "candidate_id": candidate_id, "source_person_id": source_person_id,
                "event_id": event_id,
                "event_index": event_index, "event_no": event.get("event_no"),
                "event_type": event.get("event_type"), "description": event.get("description"),
                "date_raw": event.get("date_raw"), "dates_json": json_text(event.get("dates", [])),
                "end_date_raw": event.get("end_date_raw"), "end_dates_json": json_text(event.get("end_dates", [])),
                "office_raw": event.get("office_raw"), "title_raw": event.get("title_raw"),
                "place_raw": event.get("place_raw"), "locality_raw": event.get("locality_raw"),
                "kaza_raw": event.get("kaza_raw"), "sancak_raw": event.get("sancak_raw"),
                "vilayet_raw": event.get("vilayet_raw"), "institution_raw": event.get("institution_raw"),
                "employer_raw": event.get("employer_raw"), "ministry_raw": event.get("ministry_raw"),
                "authority_raw": event.get("authority_raw"), "office_basis": event.get("office_basis"),
                "context_quote": event.get("context_quote"),
                "office_reference_event_no": event.get("office_reference_event_no"),
                "age_raw": event.get("age_raw"), "age": scalar_text(event.get("age")),
                "duration_raw": event.get("duration_raw"), "status": event.get("status"),
                "honorary": scalar_text(event.get("honorary")), "award_raw": event.get("award_raw"),
                "grade_raw": event.get("grade_raw"), "grade": scalar_text(event.get("grade")),
                "legal_outcome": event.get("legal_outcome"), "office_relation": event.get("office_relation"),
                "document_number_raw": event.get("document_number_raw"), "reason_raw": event.get("reason_raw"),
                "source_quote": event.get("source_quote"), "source_lines_json": json_text(ids),
                "context_lines_json": json_text(event.get("context_lines", [])),
                "pdf_pages_json": json_text(pages), "warnings_json": json_text(event.get("warnings", [])),
                "citation_status": status, "payload_json": json_text(event),
            }
            tables["events"].append(event_row)
            for date_role, date_key, raw_key in (
                ("start", "dates", "date_raw"), ("end", "end_dates", "end_date_raw"),
            ):
                date_items = event.get(date_key, [])
                if not isinstance(date_items, list):
                    continue
                group_id = f"{event_id}:{date_role}"
                pair_status = (
                    "same_event_date_field; relationship_unadjudicated"
                    if len(date_items) > 1 else "single_event_date_entry"
                )
                for date_index, date in enumerate(date_items):
                    if not isinstance(date, dict):
                        continue
                    date_status, date_ids, context_ids, date_pages = _date_citation(date, line_map)
                    tables["event_dates"].append({
                        "candidate_id": candidate_id,
                        "source_person_id": source_person_id,
                        "event_id": event_id,
                        "event_index": event_index,
                        "event_no": event.get("event_no"),
                        "date_role": date_role,
                        "date_index": date_index,
                        "date_group_id": group_id,
                        "calendar_pair_status": pair_status,
                        "calendar": date.get("calendar"),
                        "year": _typed_integer(date.get("year")),
                        "proposed_year": _typed_integer(date.get("proposed_year")),
                        "month": _typed_integer(date.get("month")),
                        "day": _typed_integer(date.get("day")),
                        "year_basis": date.get("year_basis"),
                        "calendar_basis": date.get("calendar_basis"),
                        "year_abbreviated": _typed_integer(date.get("year_abbreviated")),
                        "date_raw": event.get(raw_key),
                        "date_quote": date.get("date_quote"),
                        "context_quote": date.get("context_quote"),
                        "reference_event_no": date.get("reference_event_no"),
                        "source_lines_json": json_text(date_ids),
                        "context_lines_json": json_text(context_ids),
                        "pdf_pages_json": json_text(date_pages),
                        "citation_status": date_status,
                    })
            for payment_index, payment in enumerate(event.get("payments", [])):
                pay_lines = payment.get("source_lines")
                anchor = money_maps[source_person_id].get(str(payment.get("pay_anchor_id", "")), {})
                status, ids, pay_pages = check_citation(
                    pay_lines, payment.get("quote"), None, line_map,
                    fallback_lines=anchor.get("line_ids"),
                )
                # Grounding can widen a payment citation to include the exact
                # monetary anchor. Reproduce that deterministic citation span.
                if status == "citation_mismatch" and anchor.get("line_ids"):
                    expanded = list(dict.fromkeys(
                        [str(x) for x in (pay_lines or [])] + [str(x) for x in anchor["line_ids"]]
                    ))
                    status, ids, pay_pages = check_citation(
                        expanded, payment.get("quote"), None, line_map,
                    )
                tables["payments"].append({
                    "candidate_id": candidate_id, "source_person_id": source_person_id,
                    "event_id": event_id, "event_index": event_index,
                    "event_no": event.get("event_no"), "payment_index": payment_index,
                    "payment_id": f"{event_id}:payment:{payment_index:04d}",
                    "component": payment.get("component"),
                    "term_raw": payment.get("term_raw"), "amount_literal": payment.get("amount_literal"),
                    "amount": scalar_text(payment.get("amount")), "currency_raw": payment.get("currency_raw"),
                    "subunit_amount_literal": payment.get("subunit_amount_literal"),
                    "subunit_amount": scalar_text(payment.get("subunit_amount")),
                    "subunit_currency_raw": payment.get("subunit_currency_raw"),
                    "frequency_raw": payment.get("frequency_raw"), "basis": payment.get("basis"),
                    "reference_event_no": payment.get("reference_event_no"),
                    "amount_scope": payment.get("amount_scope"), "amount_role": payment.get("amount_role"),
                    "recipient_raw": payment.get("recipient_raw"), "reuse_reason": payment.get("reuse_reason"),
                    "paid_amount": scalar_text(payment.get("paid_amount")),
                    "pay_anchor_id": payment.get("pay_anchor_id"), "quote": payment.get("quote"),
                    "source_lines_json": json_text(ids), "pdf_pages_json": json_text(pay_pages),
                    "reading_flags_json": json_text(payment.get("reading_flags", [])),
                    "warnings_json": json_text(payment.get("warnings", [])),
                    "citation_status": status, "payload_json": json_text(payment),
                })
    return tables, counts


def write_export(out_dir: Path, tables: dict[str, list[dict[str, Any]]]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "public_personnel.sqlite"
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("CREATE TABLE export_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.executemany("INSERT INTO export_metadata VALUES (?,?)", [
            ("status", "source-local extraction candidates; not historically adjudicated"),
            ("identity", "source-person IDs are appearance-local; no identity merging"),
            ("time_series", "no annual panel, salary carry-forward, or interpolated service"),
            ("source_citations", "quotes, source line IDs, and PDF page numbers retained per record"),
        ])
        for table, sql in CREATE_SQL.items():
            connection.execute(sql)
            columns = TABLE_COLUMNS[table]
            placeholders = ",".join("?" for _ in columns)
            quoted = ",".join('"' + x + '"' for x in columns)
            connection.executemany(
                f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})',
                [_row(table, row) for row in tables[table]],
            )
        connection.execute(CAREER_OBSERVATIONS_VIEW_SQL)
        connection.commit()
    finally:
        connection.close()
    for table, columns in TABLE_COLUMNS.items():
        path = out_dir / f"{table}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(tables[table])
    with closing(sqlite3.connect(db_path)) as connection:
        rows = connection.execute("SELECT * FROM career_observations").fetchall()
        columns = [item[0] for item in connection.execute("SELECT * FROM career_observations LIMIT 0").description]
    with (out_dir / "career_observations.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
    return db_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--units", required=True, help="source-only intake JSONL")
    parser.add_argument("--results", required=True, help="runner results directory or one result JSON")
    parser.add_argument("--out-dir", required=True, help="directory for SQLite and CSV outputs")
    args = parser.parse_args(argv)
    units = read_jsonl(Path(args.units))
    files = result_files(Path(args.results))
    tables, counts = collect_records(units, files)
    db_path = write_export(Path(args.out_dir), tables)
    print(json.dumps({"database": str(db_path), "result_files": counts["read"],
                      "completed_candidates": len(tables["candidates"]),
                      "skipped_noncompleted": counts["skipped_noncompleted"],
                      "facts": len(tables["facts"]), "events": len(tables["events"]),
                      "event_dates": len(tables["event_dates"]),
                      "payments": len(tables["payments"]),
                      "historically_adjudicated": False, "identity_merge": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
