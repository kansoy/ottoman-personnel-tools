"""Meaningful boundary and relation checks using invented text, no network."""
import copy
import csv
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from examples.synthetic_example import build_demo, pool_row, write_demo
from personnel_evidence import contract, export, intake


class OfflineEvidenceTests(unittest.TestCase):
    def test_source_boundary_and_explicit_selection(self):
        with self.assertRaisesRegex(ValueError, "explicit"):
            intake.build_units([pool_row()], [])
        row = pool_row()
        row["native_boundary_review_status"] = "not_reviewed"
        selection = [{"appearance_id": row["appearance_id"], "source_id": "",
                      "reason": "test", "selected_by": "test"}]
        with self.assertRaisesRegex(ValueError, "boundary not reviewed"):
            intake.build_units([row], selection)
        unit = intake.build_units([row], selection, include_flagged_boundaries=True)[0]
        self.assertEqual(unit["boundary_gate"], "flagged_candidate")

    def test_grounded_quotes_hashes_and_separate_calendars(self):
        unit, packet, result, evidence = build_demo()
        self.assertEqual(result["validation_errors"], [])
        self.assertEqual(result["source_pdf_sha256"], unit["source_pdf_sha256"])
        event = result["parsed"]["events"][0]
        self.assertEqual(event["source_quote"], packet["lines"][0]["text"])
        self.assertEqual(event["pdf_pages"], [1])
        self.assertEqual([(d["calendar"], d["year"]) for d in event["dates"]],
                         [("hijri", 1300), ("rumi", 1298)])
        self.assertEqual(evidence["money_anchor_count"], 1)
        self.assertEqual(evidence["missing_money"], [])

    def test_calendar_relabel_and_wrong_page_are_flagged(self):
        unit, _, result, _ = build_demo()
        changed = copy.deepcopy(result["parsed"])
        changed["events"][0]["dates"][0]["calendar"] = "rumi"
        self.assertIn("event:1:date_year_explicit_calendar_mismatch", contract.validate(changed, unit))
        changed["events"][0]["pdf_pages"] = [99]
        self.assertIn("event:1:quote_page_mismatch", contract.validate(changed, unit))

    def test_export_zero_missing_citation_and_cardinality_without_network(self):
        # Any accidental socket creation fails this complete example/test.
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            with tempfile.TemporaryDirectory() as temp:
                out = Path(temp) / "demo"
                summary = write_demo(out)
                self.assertEqual(summary["validation_issues"], [])
                self.assertEqual((summary["events"], summary["payments"], summary["event_dates"]), (2, 2, 2))
                with sqlite3.connect(summary["database"]) as con:
                    self.assertEqual(con.execute("SELECT amount FROM payments ORDER BY payment_index").fetchall(),
                                     [("0",), (None,)])
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM career_observations").fetchone()[0], 3)
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM events").fetchone()[0], 2)
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM event_dates").fetchone()[0], 2)
                    self.assertEqual(con.execute("SELECT DISTINCT calendar_pair_status FROM event_dates").fetchall(),
                                     [("same_event_date_field; relationship_unadjudicated",)])
                    self.assertEqual(con.execute("SELECT historical_status FROM candidates").fetchone()[0],
                                     "not_adjudicated_candidate")
                    self.assertEqual(con.execute("SELECT DISTINCT citation_status FROM payments").fetchall(),
                                     [("source_lines_quote_pages_match",)])
                    self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
                with (out / "export/payments.csv").open(encoding="utf-8-sig", newline="") as handle:
                    self.assertEqual([r["amount"] for r in csv.DictReader(handle)], ["0", ""])

    def test_mismatched_source_hash_rejected(self):
        unit, _, result, _ = build_demo()
        result["source_pdf_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.json"
            path.write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError, "source_pdf_sha256 mismatch"):
                export.collect_records([unit], [path])

    def test_schema_requires_correct_types_and_new_output_directory(self):
        _, _, result, _ = build_demo()
        changed = copy.deepcopy(result["parsed"])
        changed["events"][0]["dates"][0]["year"] = "1300"
        with self.assertRaisesRegex(ValueError, "schema_type_mismatch"):
            contract.schema_check(changed, contract.SCHEMA)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "new output directory"):
                write_demo(Path(temp))


if __name__ == "__main__":
    unittest.main()
