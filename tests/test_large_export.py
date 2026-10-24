"""Regression for full-biography JSON cells larger than csv's default limit."""
from contextlib import closing
import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from sicilahval.demo import TEXTS, build_example
from sicilahval.export import export_records
from sicilahval.intake import prepare_source


class LargeExportTests(unittest.TestCase):
    def test_large_biography_exports_losslessly_and_restores_csv_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            original = base / 'source.txt'
            original.write_text(TEXTS['pay_legal'], encoding='utf-8')
            prepare_source(original, base / 'prepared', 'en')
            source = json.loads((base / 'prepared/source.json').read_text())
            records = build_example('pay_legal', source, 'en')
            # A long annotation has no source-number or quotation implications.
            note = 'Reviewed complete biography; original evidence retained. ' * 6000
            records['records'][0]['notes'].append(note)
            previous = csv.field_size_limit()
            try:
                csv.field_size_limit(65536)
                summary = export_records(records, source, base / 'data')
                self.assertTrue(summary['csv_sqlite_cells_match'])
                self.assertEqual(csv.field_size_limit(), 65536)
                with closing(sqlite3.connect(summary['database'])) as connection:
                    payload = connection.execute('SELECT payload_json FROM records').fetchone()[0]
                self.assertEqual(json.loads(payload), records['records'][0])
                self.assertGreater(len(payload), 131072)
            finally:
                csv.field_size_limit(previous)


if __name__ == '__main__':
    unittest.main()
