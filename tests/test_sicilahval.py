"""Offline boundary tests for the public extraction contract, not model accuracy."""
from __future__ import annotations

from contextlib import closing
import csv
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from sicilahval.demo import TEXTS, build_example, write_demo
from sicilahval.export import export_records
from sicilahval.install import install_skill
from sicilahval.intake import prepare_source
from sicilahval.numbers import day_values, literal_values
from sicilahval.util import read_json, schema_path
from sicilahval.validation import validate_records


class SicilahvalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def reading(self, example="pay_legal", language="tr"):
        original = self.base / f"{example}.txt"
        original.write_text(TEXTS[example], encoding="utf-8")
        workspace = self.base / f"work-{example}"
        prepare_source(original, workspace, language)
        source = read_json(workspace / "source.json")
        return original, source, build_example(example, source, language)

    def test_two_complete_bilingual_demos_without_network(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            english = write_demo(self.base / "en", "en", synthetic=True)
            turkish = write_demo(self.base / "tr", "tr", synthetic=True)
        self.assertEqual(english["counts"], {"records": 1, "facts": 15, "events": 6, "dates": 7, "payments": 5})
        self.assertEqual(turkish["counts"], {"records": 1, "facts": 16, "events": 6, "dates": 7, "payments": 4})
        self.assertFalse(english["semantic_completeness_proven"])
        self.assertIn("Sonraki", read_json(self.base / "tr/work/records.json")["records"][0]["facts"][4]["note"])

    def test_reviewed_real_examples_are_default_and_languages_are_not_retagged(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            english = write_demo(self.base / "real-en", "en")
            turkish = write_demo(self.base / "real-tr", "tr")
        self.assertEqual((english["example"], english["synthetic"]), ("manuk", False))
        self.assertEqual((turkish["example"], turkish["synthetic"]), ("zenop", False))
        self.assertEqual(english["counts"], {"records": 1, "facts": 33, "events": 14, "dates": 14, "payments": 6})
        self.assertEqual(turkish["counts"], {"records": 1, "facts": 38, "events": 21, "dates": 25, "payments": 10})
        self.assertIn("DH_SAİD_8_86; 167", (self.base / "real-en/source.txt").read_text())
        self.assertIn("DH_SAİD_5_356; 709", (self.base / "real-tr/source.txt").read_text())
        with self.assertRaisesRegex(ValueError, "cached example has en annotations"):
            write_demo(self.base / "wrong-language", "tr", "manuk")
        self.assertFalse((self.base / "wrong-language").exists())

    def test_utf8_exact_text_and_original_hash(self):
        original, source, records = self.reading()
        self.assertEqual(source["sha256"], hashlib.sha256(original.read_bytes()).hexdigest())
        self.assertIn("İstanbul", source["segments"][1]["text"])
        self.assertTrue(validate_records(records, source, original=original)["valid"])
        original.write_text("changed", encoding="utf-8")
        self.assertIn("Original file SHA-256", " ".join(validate_records(records, source, original=original)["errors"]))

    def test_tampered_prepared_text_detected(self):
        _, source, records = self.reading()
        source["segments"][1]["text"] += " altered"
        self.assertIn("text checksum mismatch", " ".join(validate_records(records, source)["errors"]))

    def test_exact_quote_and_direct_value_attachment(self):
        _, source, records = self.reading()
        records["records"][0]["facts"][0]["evidence"][0]["quote"] = "Rafael  Efendi"
        self.assertIn("exact quotation mismatch", " ".join(validate_records(records, source)["errors"]))
        records = build_example("pay_legal", source, "tr")
        records["records"][0]["events"][2]["payments"][0]["amount_raw"] = "999"
        records["records"][0]["events"][2]["payments"][0]["amount"] = 999
        self.assertIn("amount_raw does not occur", " ".join(validate_records(records, source)["errors"]))

    def test_unknown_pay_does_not_become_zero(self):
        _, source, records = self.reading()
        payment = records["records"][0]["events"][0]["payments"][0]
        self.assertIsNone(payment["amount"])
        payment["amount"] = 0
        self.assertIn("zero is not supported", " ".join(validate_records(records, source)["errors"]))

    def test_currency_period_and_calendar_relabel_rejected(self):
        _, source, records = self.reading()
        records["records"][0]["events"][3]["dates"][0]["calendar"] = "hijri"
        records["records"][0]["events"][3]["payments"][0]["currency_raw"] = "kuruş"
        records["records"][0]["events"][3]["payments"][0]["period_raw"] = "aylık"
        errors = " ".join(validate_records(records, source)["errors"])
        self.assertIn("calendar contradicts", errors)
        self.assertIn("currency_raw", errors)
        self.assertIn("period_raw", errors)

    def test_abbreviated_year_is_not_silently_completed(self):
        _, source, records = self.reading()
        date = records["records"][0]["events"][0]["dates"][0]
        date["year"] = 1390
        self.assertIn("direct numeric year", " ".join(validate_records(records, source)["errors"]))

    def test_inference_requires_rationale_and_preserves_alternatives(self):
        _, source, records = self.reading("appointment", "en")
        inferred = records["records"][0]["events"][1]["payments"][1]
        self.assertEqual((inferred["amount"], inferred["certainty"]), (175, "inferred"))
        self.assertIsNone(inferred["alternatives"][0]["amount"])
        inferred["note"] = ""
        self.assertIn("non-direct reading requires", " ".join(validate_records(records, source)["errors"]))

    def test_every_segment_and_item_needs_coverage(self):
        _, source, records = self.reading()
        records["records"][0]["coverage"].pop()
        self.assertIn("segment has no coverage", " ".join(validate_records(records, source)["errors"]))
        records = build_example("pay_legal", source, "tr")
        records["excluded_segments"] = []
        self.assertIn("Source segment has no record", " ".join(validate_records(records, source)["errors"]))

    def test_coverage_wrong_item_and_cross_record_evidence_rejected(self):
        _, source, records = self.reading()
        records["records"][0]["coverage"][0]["item_ids"] = ["e04"]
        records["records"][0]["facts"][0]["evidence"][0]["segment_id"] = "s000001"
        errors = " ".join(validate_records(records, source)["errors"])
        self.assertIn("coverage item has no evidence", errors)
        self.assertIn("evidence segment outside record", errors)

    def test_fact_dates_corrections_and_legal_history_survive_export(self):
        _, source, records = self.reading()
        records["records"][0]["facts"][0]["details"] = {"arbitrary_new_detail": ["a", 0, None, {"nested": "ç"}]}
        summary = export_records(records, source, self.base / "data")
        with closing(sqlite3.connect(summary["database"])) as con:
            self.assertEqual(json.loads(con.execute("SELECT payload_json FROM extraction_document").fetchone()[0]), records)
            self.assertEqual(json.loads(con.execute("SELECT payload_json FROM prepared_source_document").fetchone()[0]), source)
            self.assertEqual(con.execute("SELECT amount FROM payments ORDER BY rowid").fetchall(), [(None,), ("0",), ("200",), ("15",)])
            self.assertEqual(con.execute("SELECT calendar FROM dates WHERE date_id='d05'").fetchone()[0], "rumi")
            self.assertEqual(con.execute("SELECT year FROM dates WHERE date_id='d06'").fetchone()[0], None)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM dates WHERE owner_type='fact'").fetchone()[0], 2)
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
        with (self.base / "data/payments.csv").open(encoding="utf-8-sig", newline="") as handle:
            self.assertEqual([r["amount"] for r in csv.DictReader(handle)], ["", "0", "200", "15"])

    def test_concurrent_posts_and_increment_not_collapsed_or_summed(self):
        _, source, records = self.reading("appointment", "en")
        summary = export_records(records, source, self.base / "data")
        with closing(sqlite3.connect(summary["database"])) as con:
            self.assertEqual(con.execute("SELECT owner_id,year FROM dates WHERE year='1286' ORDER BY rowid").fetchall(),
                             [("e02", "1286"), ("e03", "1286")])
            self.assertEqual(con.execute("SELECT amount,amount_role,certainty FROM payments WHERE event_id='e02' ORDER BY rowid").fetchall(),
                             [("25", "increment", "direct"), ("175", "level", "inferred")])
            self.assertEqual(con.execute("SELECT COUNT(*) FROM events").fetchone()[0], 6)

    def test_missing_fields_wrong_types_duplicate_ids_fail(self):
        _, source, records = self.reading()
        records["records"][0]["events"][0]["dates"][0]["year"] = "1290"
        self.assertIn("wrong type", " ".join(validate_records(records, source)["errors"]))
        records = build_example("pay_legal", source, "tr")
        records["records"][0]["events"][1]["event_id"] = "e01"
        self.assertIn("repeated item ID", " ".join(validate_records(records, source)["errors"]))
        del records["records"][0]["facts"][0]["evidence"]
        self.assertIn("required field missing", " ".join(validate_records(records, source)["errors"]))

    def test_existing_outputs_and_invalid_export_are_preserved(self):
        original, source, records = self.reading()
        with self.assertRaisesRegex(ValueError, "already exists"):
            prepare_source(original, self.base / "work-pay_legal")
        records["source_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "Validation failed"):
            export_records(records, source, self.base / "bad")
        self.assertFalse((self.base / "bad").exists())

    def test_docx_tables_footnotes_endnotes_headers_and_revisions(self):
        namespace = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        document = f'''<w:document {namespace}><w:body>
          <w:p><w:r><w:t>Rafael Efendi</w:t><w:footnoteReference w:id="2"/></w:r></w:p>
          <w:tbl><w:tr><w:tc><w:p><w:r><w:t>İstanbul 150 kuruş</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
          <w:sdt><w:sdtContent><w:p><w:r><w:t>Sonraki tashih</w:t><w:endnoteReference w:id="3"/></w:r></w:p></w:sdtContent></w:sdt>
          <w:p><w:del w:id="4"><w:r><w:delText>eski yıl 1268</w:delText></w:r></w:del><w:ins w:id="5"><w:r><w:t>yeni yıl 1269</w:t></w:r></w:ins></w:p>
          </w:body></w:document>'''
        path = self.base / "source.docx"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document)
            archive.writestr("word/footnotes.xml", f'<w:footnotes {namespace}><w:footnote w:id="-1" w:type="separator"/><w:footnote w:id="2"><w:p><w:r><w:t>Varak 12b</w:t></w:r></w:p></w:footnote></w:footnotes>')
            archive.writestr("word/endnotes.xml", f'<w:endnotes {namespace}><w:endnote w:id="3"><w:p><w:r><w:t>Hicrî 1269 tashihi</w:t></w:r></w:p></w:endnote></w:endnotes>')
            archive.writestr("word/header1.xml", f'<w:hdr {namespace}><w:p><w:r><w:t>Kaynak künyesi</w:t></w:r></w:p></w:hdr>')
        prepare_source(path, self.base / "docx")
        source = read_json(self.base / "docx/source.json")
        segments = source["segments"]
        self.assertEqual(segments[0]["text"], "Rafael Efendi[footnote:2]")
        self.assertEqual(segments[1]["locator"]["cell"], 1)
        self.assertTrue(any(s["locator"].get("container") == "sdt" for s in segments))
        for kind in ("footnote", "endnote", "header", "tracked_deletion"):
            self.assertTrue(any(s["locator"]["part"] == kind for s in segments), kind)
        self.assertIn("eski yıl 1268", [s["text"] for s in segments])
        self.assertTrue(any("Tracked insertions" in w for w in source["warnings"]))

    def test_standalone_skill_runs_without_installed_package(self):
        installed = install_skill(path=self.base / "skills")
        script = Path(installed["path"]) / "scripts/sicilahval.py"
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        run = subprocess.run([sys.executable, str(script), "demo", "--out", str(self.base / "standalone"), "--language", "tr", "--synthetic"],
            cwd=self.base, env=environment, text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(run.stdout)["counts"]["facts"], 16)
        self.assertTrue((Path(installed["path"]) / "references/schema.md").is_file())
        with self.assertRaisesRegex(ValueError, "already exists"):
            install_skill(path=self.base / "skills")

    def test_turkish_english_cardinals_and_ambiguous_punctuation(self):
        self.assertEqual(literal_values("yüz elli"), {150})
        self.assertEqual(literal_values("one hundred fifty"), {150})
        self.assertEqual(literal_values("1.500"), {1500, 1.5})

    def test_word_amount_mismatch_and_truncated_decimal_are_rejected(self):
        original = self.base / "words.txt"
        original.write_text(TEXTS["appointment"].replace("150 kuruş", "yüz elli kuruş"), encoding="utf-8")
        prepare_source(original, self.base / "words")
        source = read_json(self.base / "words/source.json")
        records = build_example("appointment", source, "en")
        payment = records["records"][0]["events"][0]["payments"][0]
        payment["amount_raw"] = "yüz elli"
        self.assertTrue(validate_records(records, source)["valid"])
        payment["amount"] = 115
        self.assertIn("direct amount does not occur", " ".join(validate_records(records, source)["errors"]))
        original = self.base / "decimal.txt"
        original.write_text(TEXTS["appointment"].replace("150 kuruş", "150,50 kuruş"), encoding="utf-8")
        prepare_source(original, self.base / "decimal")
        source = read_json(self.base / "decimal/source.json")
        records = build_example("appointment", source, "en")
        self.assertIn("amount_raw does not occur", " ".join(validate_records(records, source)["errors"]))

    def test_date_precision_and_unknown_link_fail(self):
        _, source, records = self.reading()
        records["records"][0]["events"][0]["dates"][0]["precision"] = "day"
        records["records"][0]["events"][0]["fact_ids"] = ["not-a-fact"]
        errors = " ".join(validate_records(records, source)["errors"])
        self.assertIn("day precision requires", errors)
        self.assertIn("unknown linked fact", errors)

    def test_inflected_turkish_and_english_date_days(self):
        cases = [
            ("bin üç yüz altı senesi Rebiülevvelinin dördünde", 4),
            ("bin üç yüz on bir senesi Rebiülahirinin on beşinde", 15),
            ("bin üç yüz on dört senesi Şevvalinin dokuzunda", 9),
            ("bin üç yüz on sekiz senesi Cemaziyelevveli gurresinde", 1),
            ("bin üç yüz yirmi bir senesi Şabanının on dördünde", 14),
            ("the first of May 1860", 1), ("the third of May 1860", 3),
            ("22nd May 1860", 22), ("the twenty-first of May 1860", 21),
        ]
        for raw, day in cases:
            with self.subTest(raw=raw):
                self.assertEqual(day_values(raw), {day})
        self.assertEqual(day_values("bin üç yüz altı senesi Rebiülevvelinin okunamayan gününde"), set())
        self.assertEqual(day_values("21 senesi Şabanının okunamayan gününde"), set())

    def test_ordinal_day_acceptance_and_unparsed_day_warns_not_false_fails(self):
        raw = "bin üç yüz altı senesi Rebiülevvelinin dördünde"
        original = self.base / "ordinal.txt"
        original.write_text(TEXTS["appointment"].replace("Hicrî 1285", raw), encoding="utf-8")
        prepare_source(original, self.base / "ordinal")
        source = read_json(self.base / "ordinal/source.json")
        records = build_example("appointment", source, "en")
        date = records["records"][0]["events"][0]["dates"][0]
        date.update(raw=raw, year=1306, month=3, day=4, precision="day")
        self.assertTrue(validate_records(records, source)["valid"])
        date["day"] = 5
        self.assertIn("direct day conflicts", " ".join(validate_records(records, source)["errors"]))
        raw_unknown = raw.replace("dördünde", "okunamayan gününde")
        original = self.base / "unknown-day.txt"
        original.write_text(TEXTS["appointment"].replace("Hicrî 1285", raw_unknown), encoding="utf-8")
        prepare_source(original, self.base / "unknown-day")
        source = read_json(self.base / "unknown-day/source.json")
        records = build_example("appointment", source, "en")
        records["records"][0]["events"][0]["dates"][0].update(raw=raw_unknown, year=1306, month=3, day=4, precision="day")
        report = validate_records(records, source)
        self.assertTrue(report["valid"])
        self.assertIn("day literal is not mechanically parsed", " ".join(report["warnings"]))

    def test_html_entities_tables_notes_without_script_execution(self):
        original = self.base / "source.html"
        original.write_text('<html><head><title>Sicill kaydı</title><script>DO NOT EXECUTE</script></head><body>'
            '<h1>Rafael Efendi</h1><p>İstanbul &amp; İzmir <a href="#n1">[1]</a></p>'
            '<table><tr><td>150 kuruş</td><td>Hicrî 1290</td></tr></table>'
            '<p id="n1">Varak 12b</p><img alt="Belge sureti" src="https://invalid.example/image.jpg"></body></html>', encoding="utf-8")
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            prepare_source(original, self.base / "html")
        source = read_json(self.base / "html/source.json")
        text = "\n".join(s["text"] for s in source["segments"])
        self.assertIn("İstanbul & İzmir", text)
        self.assertIn("150 kuruş", text)
        self.assertIn("Varak 12b", text)
        self.assertNotIn("DO NOT EXECUTE", text)
        self.assertTrue(any("no OCR" in warning or "without OCR" in warning for warning in source["warnings"]))

    def test_odt_body_table_note_and_style_header(self):
        original = self.base / "source.odt"
        ns = 'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
        content = f'<office:document-content {ns}><office:body><office:text><text:h>Rafael Efendi</text:h>'
        content += '<text:p>İstanbul<text:note text:id="n1" text:note-class="footnote"><text:note-citation>1</text:note-citation><text:note-body><text:p>Varak 12b</text:p></text:note-body></text:note></text:p>'
        content += '<table:table><table:table-row><table:table-cell><text:p>150 kuruş</text:p></table:table-cell></table:table-row></table:table></office:text></office:body></office:document-content>'
        with zipfile.ZipFile(original, "w") as archive:
            archive.writestr("content.xml", content)
            archive.writestr("styles.xml", f'<office:document-styles {ns}><text:p>Kaynak künyesi</text:p></office:document-styles>')
        prepare_source(original, self.base / "odt")
        source = read_json(self.base / "odt/source.json")
        text = "\n".join(s["text"] for s in source["segments"])
        self.assertIn("İstanbul[footnote:n1]", text)
        self.assertEqual(text.count("Varak 12b"), 1)
        self.assertIn("150 kuruş", text)
        self.assertTrue(any(s["locator"]["part"] == "footnote" for s in source["segments"]))
        self.assertTrue(any(s["locator"]["part"] == "odt_style_editorial" for s in source["segments"]))

    def test_rtf_unicode_codepage_paragraphs_and_footnote(self):
        original = self.base / "source.rtf"
        original.write_bytes(br"{\rtf1\ansi\ansicpg1254\uc1{\fonttbl{\f0 Arial;}}\u304?stanbul Rafael Efendi\par 150 kuru\u351?{\footnote Varak 12b} metnin devami\par \'deehir}")
        prepare_source(original, self.base / "rtf")
        source = read_json(self.base / "rtf/source.json")
        text = "\n".join(s["text"] for s in source["segments"])
        self.assertIn("İstanbul Rafael Efendi", text)
        self.assertIn("150 kuruş", text)
        self.assertIn("Varak 12b", text)
        self.assertIn("metnin devami", text)
        self.assertIn("Şehir", text)
        self.assertNotIn("Arial", text)
        original = self.base / "broken.rtf"
        original.write_text(r"{\rtf1 broken", encoding="ascii")
        with self.assertRaisesRegex(ValueError, "Unbalanced RTF"):
            prepare_source(original, self.base / "broken")

    def test_schema_is_standard_json_schema_and_examples_conform(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("optional jsonschema development dependency is not installed")
        schema = read_json(schema_path())
        jsonschema.Draft202012Validator.check_schema(schema)
        _, _, records = self.reading()
        jsonschema.validate(records, schema)

    def test_text_pdf_pages_and_no_text_pages_are_reported(self):
        try:
            from pypdf import PdfWriter
            from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        except ImportError:
            self.skipTest("optional pypdf dependency is not installed")
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        content = DecodedStreamObject()
        content.set_data(b"BT /F1 12 Tf 72 720 Td (Hicri 1290, salary 150 kurus.) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(content)
        writer.add_blank_page(width=612, height=792)
        pdf = self.base / "text.pdf"
        writer.write(pdf)
        prepare_source(pdf, self.base / "pdf")
        source = read_json(self.base / "pdf/source.json")
        self.assertEqual(source["segments"][0]["locator"]["page"], 1)
        self.assertIn("150 kurus", source["segments"][0]["text"])
        self.assertTrue(any("no extracted text: 2" in w for w in source["warnings"]))
        self.assertTrue(any("no OCR" in w for w in source["warnings"]))

    def test_scan_only_pdf_fails_instead_of_claiming_extraction(self):
        try:
            from pypdf import PdfWriter
        except ImportError:
            self.skipTest("optional pypdf dependency is not installed")
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        pdf = self.base / "scan.pdf"
        writer.write(pdf)
        with self.assertRaisesRegex(ValueError, "No text was extracted"):
            prepare_source(pdf, self.base / "scan")
        self.assertFalse((self.base / "scan").exists())


if __name__ == "__main__":
    unittest.main()
