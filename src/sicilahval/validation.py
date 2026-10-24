"""Mechanical structure, evidence, association and coverage checks.

Exact quotations establish attachment to prepared text, not historical truth or
semantic completeness. The supplied source itself still needs source review.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .util import digest_bytes, json_text, read_json, schema_path
from .numbers import day_values, literal_values, number_runs, number_spans


def _type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _shape(value: Any, rule: dict, root: dict, at: str, errors: list[str]) -> None:
    if "$ref" in rule:
        target: Any = root
        for part in rule["$ref"].split("/")[1:]:
            target = target[part]
        _shape(value, target, root, at, errors)
        return
    if "const" in rule and value != rule["const"]:
        errors.append(f"{at}: expected {rule['const']!r}")
    if "enum" in rule and value not in rule["enum"]:
        errors.append(f"{at}: unsupported value {value!r}")
    typ = _type(value)
    expected = rule.get("type")
    if expected:
        expected = [expected] if isinstance(expected, str) else expected
        if typ not in expected and not (typ == "integer" and "number" in expected):
            errors.append(f"{at}: wrong type {typ}; expected {expected}")
            return
    if typ == "object":
        props = rule.get("properties", {})
        for key in rule.get("required", []):
            if key not in value:
                errors.append(f"{at}.{key}: required field missing")
        if rule.get("additionalProperties") is False:
            for key in set(value) - set(props):
                errors.append(f"{at}.{key}: unknown field; put arbitrary detail in details or a fact")
        for key in value.keys() & props.keys():
            _shape(value[key], props[key], root, f"{at}.{key}", errors)
    elif typ == "array":
        if len(value) < rule.get("minItems", 0):
            errors.append(f"{at}: too few items")
        for index, item in enumerate(value):
            _shape(item, rule.get("items", {}), root, f"{at}[{index}]", errors)
    elif typ == "string":
        if len(value.strip()) < rule.get("minLength", 0):
            errors.append(f"{at}: empty text")
    elif typ in ("integer", "number"):
        if not math.isfinite(value):
            errors.append(f"{at}: non-finite number")
        if "minimum" in rule and value < rule["minimum"]:
            errors.append(f"{at}: below minimum")
        if "maximum" in rule and value > rule["maximum"]:
            errors.append(f"{at}: above maximum")


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower().replace("ı", "i"))
                   if not unicodedata.combining(c))


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a monetary amount")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("amount must be a decimal number, decimal string or null") from exc
    if not amount.is_finite():
        raise ValueError("amount must be finite")
    return amount


def _numbers(text: str) -> list[Decimal]:
    return list(number_runs(text))


def _raw_attached(raw: str, quotes: list[str], *, monetary: bool = False) -> bool:
    if not monetary:
        return any(raw in quote for quote in quotes)
    for quote in quotes:
        # Check the source's complete digit tokens even when raw includes a
        # currency: "150 kuruş" must not attach to "1150 kuruş". A comma or
        # full stop extends a number only when another digit follows it.
        numbers = list(re.finditer(
            r"[+-]?\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?!\d)(?:[.,]\d+)*|[+-]?\d+(?:[.,]\d+)*", quote))
        for match in re.finditer(re.escape(raw), quote):
            if not any(number.start() < match.end() and number.end() > match.start()
                       and (number.start() < match.start() or number.end() > match.end())
                       for number in numbers):
                return True
    return False


def _calendar_labels(raw: str, year: int) -> set[str]:
    """Bind explicit labels without requiring an Arabic-digit year spelling."""
    folded = _fold(raw)
    labels = {"hijri": r"(?:hicri(?:ye(?:si)?)?|hijri|ah|h\.)",
              "rumi": r"(?:rumi(?:ye(?:si)?)?|r\.)",
              "gregorian": r"(?:miladi|gregorian|ad)"}
    present = {calendar for calendar, label in labels.items()
               if re.search(r"\b" + label + r"(?!\w)", folded)}
    if len(present) == 1:
        # A single explicit label also covers "1290 AH" and a written year.
        return present
    bound = set()
    for begin, _, values in number_spans(raw):
        if Decimal(year) not in values:
            continue
        for calendar, label in labels.items():
            if re.search(r"\b" + label + r"\s*[:.]?\s*$", folded[:begin]):
                bound.add(calendar)
    return bound


def validate_records(records: dict | str | Path, source: dict | str | Path,
                     *, original: str | Path | None = None) -> dict:
    """Return errors/warnings; perform no filling, correction or model calls."""
    data = read_json(records) if isinstance(records, (str, Path)) else records
    prepared = read_json(source) if isinstance(source, (str, Path)) else source
    errors: list[str] = []
    warnings: list[str] = []
    schema = read_json(schema_path())
    _shape(data, schema, schema, "$", errors)
    counts = {"records": 0, "facts": 0, "events": 0, "dates": 0, "payments": 0}
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings, "counts": counts,
                "claim": "Structure failed; evidence and coverage were not checked."}
    if not isinstance(prepared, dict) or not isinstance(prepared.get("segments"), list):
        return {"valid": False, "errors": ["Invalid prepared source"], "warnings": [], "counts": counts}
    if data["source_id"] != prepared.get("source_id"):
        errors.append("Source ID does not match prepared source")
    if prepared.get("source_id") != "src-" + str(prepared.get("sha256", ""))[:16]:
        errors.append("Prepared source ID does not match native SHA-256 prefix")
    if prepared.get("text_sha256") != digest_bytes(json_text(prepared["segments"]).encode("utf-8")):
        errors.append("Prepared source text checksum mismatch")
    if original is not None and digest_bytes(Path(original).read_bytes()) != prepared.get("sha256"):
        errors.append("Original file SHA-256 does not match prepared source")
    segment_list = prepared["segments"]
    if any(not isinstance(s, dict) or not isinstance(s.get("segment_id"), str)
           or not isinstance(s.get("text"), str) for s in segment_list):
        errors.append("Invalid source segment structure")
        return {"valid": False, "errors": errors, "warnings": warnings, "counts": counts}
    segments = {s["segment_id"]: s["text"] for s in segment_list}
    if len(segments) != len(segment_list):
        errors.append("Duplicate prepared source segment IDs")
    assignments: Counter = Counter()
    record_ids: set[str] = set()
    for record in data["records"]:
        rid = record["record_id"]
        counts["records"] += 1
        if rid in record_ids:
            errors.append(f"{rid}: duplicate record ID")
        record_ids.add(rid)
        owned = set(record["segment_ids"])
        assignments.update(owned)
        if len(owned) != len(record["segment_ids"]):
            errors.append(f"{rid}: repeated record segment IDs")
        if not owned <= segments.keys():
            errors.append(f"{rid}: unknown record segment IDs: {sorted(owned - segments.keys())}")
        if not any(record["name_raw"] in segments.get(sid, "") for sid in owned):
            errors.append(f"{rid}: name_raw does not occur in the assigned source text")
        facts = {f["fact_id"]: f for f in record["facts"]}
        if len(facts) != len(record["facts"]):
            errors.append(f"{rid}: duplicate fact IDs")
        items: dict[str, dict] = {}

        def item(obj: dict, kind: str) -> None:
            key = obj[kind + "_id"]
            counts[kind + "s"] += 1
            if key in items:
                errors.append(f"{rid}/{key}: repeated item ID")
            items[key] = obj
            if obj["certainty"] != "direct" and not obj["note"].strip():
                errors.append(f"{rid}/{key}: non-direct reading requires a rationale")
            for citation in obj["evidence"]:
                sid, quote = citation["segment_id"], citation["quote"]
                if sid not in owned:
                    errors.append(f"{rid}/{key}: evidence segment outside record: {sid}")
                if sid not in segments:
                    errors.append(f"{rid}/{key}: unknown evidence segment: {sid}")
                elif quote not in segments[sid]:
                    errors.append(f"{rid}/{key}: exact quotation mismatch in {sid}")
            quotes = [e["quote"] for e in obj["evidence"]]
            raw_key = {"fact": "value_raw", "event": "description_raw", "date": "raw", "payment": "amount_raw"}[kind]
            if obj["certainty"] == "direct" and obj[raw_key] and not _raw_attached(obj[raw_key], quotes, monetary=kind == "payment"):
                errors.append(f"{rid}/{key}: direct {raw_key} does not occur in its evidence quotations")
            if kind == "date":
                raw = obj["raw"]
                nums = _numbers(raw)
                if obj["certainty"] == "direct" and obj["year"] is not None and nums and Decimal(obj["year"]) not in nums:
                    errors.append(f"{rid}/{key}: direct numeric year does not occur in date raw text")
                if obj["certainty"] == "direct" and obj["year"] is not None and not nums:
                    warnings.append(f"{rid}/{key}: year literal is not mechanically parsed; inspect its numerical reading")
                if obj["certainty"] == "direct" and obj["day"] is not None:
                    days = day_values(raw)
                    if days and obj["day"] not in days:
                        errors.append(f"{rid}/{key}: direct day conflicts with recognizable date raw text")
                    elif not days:
                        warnings.append(f"{rid}/{key}: day literal is not mechanically parsed; inspect its reading")
                if obj["year"] is not None and obj["certainty"] == "direct":
                    calendars = _calendar_labels(raw, obj["year"])
                    if calendars and obj["calendar"] not in calendars:
                        errors.append(f"{rid}/{key}: calendar contradicts explicit raw label")
                    elif len(calendars) > 1:
                        warnings.append(f"{rid}/{key}: year has multiple explicit calendar labels; inspect their association")
                if obj["precision"] == "day" and any(obj[k] is None for k in ("year", "month", "day")):
                    errors.append(f"{rid}/{key}: day precision requires year, month and day")
                if obj["precision"] == "month" and any(obj[k] is None for k in ("year", "month")):
                    errors.append(f"{rid}/{key}: month precision requires year and month")
                if obj["precision"] == "year" and obj["year"] is None:
                    errors.append(f"{rid}/{key}: year precision requires a year")
                if obj["precision"] == "relative" and obj["year"] is not None and obj["certainty"] == "direct":
                    errors.append(f"{rid}/{key}: resolved relative year requires an inference label and rationale")
            elif kind == "payment":
                try:
                    amount = _decimal(obj["amount"])
                except ValueError as exc:
                    errors.append(f"{rid}/{key}: {exc}")
                    return
                raw = obj["amount_raw"]
                if obj["certainty"] == "direct" and amount is not None:
                    nums = literal_values(raw)
                    unpaid = re.search(r"\b(?:bila[\s-]*maas|maassiz|ucretsiz|unpaid|without pay|no salary)\b", _fold(raw))
                    if unpaid and amount != 0:
                        errors.append(f"{rid}/{key}: nonzero amount contradicts explicit unpaid amount raw text")
                    elif amount == 0 and not (Decimal(0) in nums or unpaid):
                        errors.append(f"{rid}/{key}: zero is not supported by an explicit zero/unpaid amount raw text")
                    elif nums and amount not in nums:
                        errors.append(f"{rid}/{key}: direct amount does not occur in amount raw text")
                    elif len(nums) > 1:
                        warnings.append(f"{rid}/{key}: monetary punctuation has more than one literal reading")
                    elif not nums and not unpaid:
                        warnings.append(f"{rid}/{key}: amount literal is not mechanically parsed; inspect its numerical reading")
                if obj["certainty"] == "direct":
                    for field in ("currency_raw", "period_raw"):
                        if obj[field] and not any(obj[field] in q for q in quotes):
                            errors.append(f"{rid}/{key}: direct {field} does not occur in its evidence quotations")

        for fact in record["facts"]:
            item(fact, "fact")
            for date in fact.get("dates", []):
                item(date, "date")
        for event in record["events"]:
            item(event, "event")
            if len(event["fact_ids"]) != len(set(event["fact_ids"])):
                errors.append(f"{rid}/{event['event_id']}: repeated linked fact IDs")
            for fid in event["fact_ids"]:
                if fid not in facts:
                    errors.append(f"{rid}/{event['event_id']}: unknown linked fact: {fid}")
            for date in event["dates"]:
                item(date, "date")
            for payment in event["payments"]:
                item(payment, "payment")
        coverage: dict[str, dict] = {}
        for decision in record["coverage"]:
            sid = decision["segment_id"]
            if sid in coverage:
                errors.append(f"{rid}: duplicate coverage segment: {sid}")
            coverage[sid] = decision
            if sid not in owned:
                errors.append(f"{rid}: coverage outside record: {sid}")
            if decision["status"] == "extracted" and not decision["item_ids"]:
                errors.append(f"{rid}/{sid}: extracted coverage requires linked items")
            if decision["status"] != "extracted" and not decision["note"].strip():
                errors.append(f"{rid}/{sid}: unresolved/nonbiographical coverage requires a reason")
            for iid in decision["item_ids"]:
                if iid not in items:
                    errors.append(f"{rid}/{sid}: unknown coverage item: {iid}")
                elif sid not in {e["segment_id"] for e in items[iid]["evidence"]}:
                    errors.append(f"{rid}/{sid}: coverage item has no evidence in this segment: {iid}")
        for sid in owned - coverage.keys():
            errors.append(f"{rid}: segment has no coverage decision: {sid}")
        cited_items = {iid for decision in record["coverage"] for iid in decision["item_ids"]}
        for iid in items.keys() - cited_items:
            errors.append(f"{rid}/{iid}: item absent from coverage links")
        if not record["facts"] and not record["events"]:
            warnings.append(f"{rid}: record contains no extracted assertions")
        if record.get("boundary_status") != "reviewed":
            warnings.append(f"{rid}: biography boundary is not marked reviewed")
    excluded: dict[str, str] = {}
    for decision in data["excluded_segments"]:
        sid = decision["segment_id"]
        if sid in excluded:
            errors.append(f"Repeated excluded segment: {sid}")
        excluded[sid] = decision["reason"]
        if sid not in segments:
            errors.append(f"Unknown excluded segment: {sid}")
        if sid in assignments:
            errors.append(f"Segment is both assigned and excluded: {sid}")
    for sid in segments.keys() - assignments.keys() - excluded.keys():
        errors.append(f"Source segment has no record or exclusion decision: {sid}")
    overlap = sorted(sid for sid, count in assignments.items() if count > 1)
    if overlap:
        warnings.append("Segments shared between records; review boundaries: " + ", ".join(overlap))
    warnings.extend(prepared.get("warnings", []))
    warnings.append("Quotation and coverage checks do not prove semantic completeness or historical accuracy.")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "counts": counts,
            "source_id": data["source_id"], "source_segments": len(segments),
            "excluded_segments": len(excluded),
            "claim": "Mechanical structure, exact evidence attachment and declared coverage only."}
