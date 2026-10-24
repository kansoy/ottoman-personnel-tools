"""Lossless JSON, normalized CSV and SQLite exports of supplied readings."""
from __future__ import annotations

import csv
from contextlib import closing
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from .util import json_text, new_directory, read_json, schema_path, write_json
from .validation import validate_records

TABLES = {
    "sources": ["source_id", "sha256", "text_sha256", "file_name", "format", "language", "metadata_json", "warnings_json"],
    "source_segments": ["source_id", "segment_id", "locator_json", "text"],
    "records": ["source_id", "record_id", "name_raw", "boundary_status", "citation_raw", "segment_ids_json", "notes_json", "details_json", "payload_json"],
    "facts": ["record_id", "fact_id", "category", "key", "value_raw", "value_json", "certainty", "note", "alternatives_json", "details_json", "payload_json"],
    "events": ["record_id", "event_id", "event_type", "description_raw", "certainty", "note", "alternatives_json", "details_json", "payload_json"],
    "event_facts": ["record_id", "event_id", "fact_id"],
    "dates": ["record_id", "owner_type", "owner_id", "date_id", "role", "raw", "calendar", "year", "month", "day", "precision", "certainty", "note", "alternatives_json", "details_json", "payload_json"],
    "payments": ["record_id", "event_id", "payment_id", "component", "amount_raw", "amount", "currency_raw", "period_raw", "amount_role", "certainty", "note", "alternatives_json", "details_json", "payload_json"],
    "evidence": ["record_id", "item_type", "item_id", "citation_index", "segment_id", "quote"],
    "coverage": ["record_id", "segment_id", "status", "item_ids_json", "note"],
    "excluded_segments": ["source_id", "segment_id", "reason"],
}


def _scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json_text(value)


def collect_tables(data: dict, source: dict) -> dict[str, list[dict]]:
    tables: dict[str, list[dict]] = {name: [] for name in TABLES}
    tables["sources"].append({key: source.get(key) for key in TABLES["sources"] if not key.endswith("_json")})
    tables["sources"][0].update(metadata_json=json_text(source.get("metadata", {})), warnings_json=json_text(source.get("warnings", [])))
    tables["source_segments"] = [{"source_id": source["source_id"], "segment_id": s["segment_id"],
        "locator_json": json_text(s["locator"]), "text": s["text"]} for s in source["segments"]]
    for record in data["records"]:
        rid = record["record_id"]
        tables["records"].append({"source_id": source["source_id"], "record_id": rid,
            "name_raw": record["name_raw"], "boundary_status": record.get("boundary_status"),
            "citation_raw": record.get("citation_raw"), "segment_ids_json": json_text(record["segment_ids"]),
            "notes_json": json_text(record["notes"]), "details_json": json_text(record.get("details", {})),
            "payload_json": json_text(record)})

        def evidence(obj: dict, kind: str) -> None:
            for index, citation in enumerate(obj["evidence"], 1):
                tables["evidence"].append({"record_id": rid, "item_type": kind, "item_id": obj[kind + "_id"],
                    "citation_index": index, "segment_id": citation["segment_id"], "quote": citation["quote"]})

        def date_rows(dates: list[dict], owner_type: str, owner_id: str) -> None:
            for date in dates:
                row = {key: date.get(key) for key in TABLES["dates"] if key in date}
                row.update(record_id=rid, owner_type=owner_type, owner_id=owner_id,
                    alternatives_json=json_text(date.get("alternatives", [])),
                    details_json=json_text(date.get("details", {})), payload_json=json_text(date))
                tables["dates"].append(row)
                evidence(date, "date")

        for fact in record["facts"]:
            row = {key: fact.get(key) for key in TABLES["facts"] if key in fact}
            row.update(record_id=rid, value_json=json_text(fact["value"]),
                alternatives_json=json_text(fact.get("alternatives", [])),
                details_json=json_text(fact.get("details", {})), payload_json=json_text(fact))
            tables["facts"].append(row)
            evidence(fact, "fact")
            date_rows(fact.get("dates", []), "fact", fact["fact_id"])
        for event in record["events"]:
            row = {key: event.get(key) for key in TABLES["events"] if key in event}
            row.update(record_id=rid, alternatives_json=json_text(event.get("alternatives", [])),
                details_json=json_text(event.get("details", {})), payload_json=json_text(event))
            tables["events"].append(row)
            evidence(event, "event")
            for fact_id in event["fact_ids"]:
                tables["event_facts"].append({"record_id": rid, "event_id": event["event_id"], "fact_id": fact_id})
            date_rows(event["dates"], "event", event["event_id"])
            for payment in event["payments"]:
                row = {key: payment.get(key) for key in TABLES["payments"] if key in payment}
                row.update(record_id=rid, event_id=event["event_id"], alternatives_json=json_text(payment.get("alternatives", [])),
                    details_json=json_text(payment.get("details", {})), payload_json=json_text(payment))
                tables["payments"].append(row)
                evidence(payment, "payment")
        for decision in record["coverage"]:
            tables["coverage"].append({"record_id": rid, "segment_id": decision["segment_id"],
                "status": decision["status"], "item_ids_json": json_text(decision["item_ids"]), "note": decision["note"]})
    tables["excluded_segments"] = [{"source_id": source["source_id"], **decision} for decision in data["excluded_segments"]]
    return tables


def export_records(records: dict | str | Path, source: dict | str | Path, out: str | Path) -> dict:
    """Validate first; export to a new directory, preserving all supplied detail."""
    data = read_json(records) if isinstance(records, (str, Path)) else records
    prepared = read_json(source) if isinstance(source, (str, Path)) else source
    report = validate_records(data, prepared)
    if not report["valid"]:
        raise ValueError("Validation failed: " + "; ".join(report["errors"][:8]))
    tables = collect_tables(data, prepared)
    target = new_directory(out)
    write_json(target / "records.json", data)
    write_json(target / "source.json", prepared)
    write_json(target / "validation.json", report)
    shutil.copyfile(schema_path(), target / "schema.json")
    database = target / "sicilahval.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        for table, columns in TABLES.items():
            constraints = {
                "sources": ["PRIMARY KEY(source_id)"],
                "source_segments": ["PRIMARY KEY(source_id,segment_id)", "FOREIGN KEY(source_id) REFERENCES sources(source_id)"],
                "records": ["PRIMARY KEY(record_id)", "FOREIGN KEY(source_id) REFERENCES sources(source_id)"],
                "facts": ["PRIMARY KEY(record_id,fact_id)", "FOREIGN KEY(record_id) REFERENCES records(record_id)"],
                "events": ["PRIMARY KEY(record_id,event_id)", "FOREIGN KEY(record_id) REFERENCES records(record_id)"],
                "event_facts": ["PRIMARY KEY(record_id,event_id,fact_id)", "FOREIGN KEY(record_id,event_id) REFERENCES events(record_id,event_id)", "FOREIGN KEY(record_id,fact_id) REFERENCES facts(record_id,fact_id)"],
                "dates": ["PRIMARY KEY(record_id,date_id)", "FOREIGN KEY(record_id) REFERENCES records(record_id)"],
                "payments": ["PRIMARY KEY(record_id,payment_id)", "FOREIGN KEY(record_id,event_id) REFERENCES events(record_id,event_id)"],
                "evidence": ["PRIMARY KEY(record_id,item_id,citation_index)", "FOREIGN KEY(record_id) REFERENCES records(record_id)"],
                "coverage": ["PRIMARY KEY(record_id,segment_id)", "FOREIGN KEY(record_id) REFERENCES records(record_id)"],
                "excluded_segments": ["PRIMARY KEY(source_id,segment_id)", "FOREIGN KEY(source_id,segment_id) REFERENCES source_segments(source_id,segment_id)"],
            }.get(table, [])
            definitions = [f'"{column}" TEXT' for column in columns] + constraints
            connection.execute(f'CREATE TABLE "{table}" (' + ",".join(definitions) + ")")
            rows = [[_scalar(row.get(column)) for column in columns] for row in tables[table]]
            connection.executemany(f'INSERT INTO "{table}" VALUES (' + ",".join("?" for _ in columns) + ")", rows)
            with (target / f"{table}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)
                writer.writerows(rows)
            saved = connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
            if saved != [tuple(row) for row in rows]:
                raise RuntimeError(f"SQLite round-trip mismatch in {table}")
            # A complete biography payload can exceed csv's 128 KiB default.
            # Raise the limit only for this verification and restore the caller's
            # process setting even when parsing fails.
            previous_limit = csv.field_size_limit()
            largest_field = max((len(value) for row in rows for value in row
                                 if isinstance(value, str)), default=0)
            try:
                csv.field_size_limit(max(previous_limit, largest_field))
                with (target / f"{table}.csv").open(encoding="utf-8-sig", newline="") as handle:
                    saved_csv = list(csv.reader(handle))
            finally:
                csv.field_size_limit(previous_limit)
            if saved_csv != [columns] + [["" if value is None else value for value in row] for row in rows]:
                raise RuntimeError(f"CSV round-trip mismatch in {table}")
        connection.execute("CREATE TABLE extraction_document (payload_json TEXT NOT NULL)")
        connection.execute("INSERT INTO extraction_document VALUES (?)", (json_text(data),))
        connection.execute("CREATE TABLE prepared_source_document (payload_json TEXT NOT NULL)")
        connection.execute("INSERT INTO prepared_source_document VALUES (?)", (json_text(prepared),))
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign-key check failed")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed")
        connection.commit()
    summary = {"output": str(target), "database": str(database), "counts": report["counts"],
        "tables": {name: len(rows) for name, rows in tables.items()}, "csv_sqlite_cells_match": True,
        "semantic_completeness_proven": False}
    write_json(target / "export_summary.json", summary)
    return summary
