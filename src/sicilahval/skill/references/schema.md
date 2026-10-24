# Structured reading

Use the `schema.json` written by `prepare`; it defines the accepted fields and types. JSON `null` means unknown. Numeric `0` means an asserted zero. Use UTF-8.

The root contains `schema_version`, `source_id`, `language`, `records` and `excluded_segments`. Copy the prepared `source_id`. Each excluded segment needs a specific reason; do not silently skip parts of the document.

Each record contains:

- `record_id`: stable, source-local identifier; never a guessed cross-source person ID.
- `name_raw`: source heading/name, preserving meaningful variants.
- `segment_ids`: complete biography, continuations and related notes.
- `facts`: open-ended assertions with `fact_id`, `category`, `key`, `value_raw`, `value`, `certainty`, `evidence`, `note`; optional `dates`, `alternatives` and `details` preserve additional structure.
- `events`: `event_id`, `event_type`, `description_raw`, linked `fact_ids`, `dates`, `payments`, `certainty`, `evidence`, `note`; optional `details` and `alternatives`.
- `coverage`: each record segment's `status`, linked `item_ids` and explanatory `note`.
- `notes`; optional `boundary_status`, `citation_raw` and `details`.

Evidence is a list of `{ "segment_id": "...", "quote": "exact text" }`. Quotes must be exact substrings of the named prepared segment. Use sufficient context to support the attached interpretation. A correct quotation does not automatically validate a normalized value.

Certainty is `direct`, `inferred`, `uncertain` or `unresolved`. Give a reason for any nondirect value. Alternatives can retain the literal reading, another interpretation and a reason; do not invent numerical confidence probabilities.

Dates retain `date_id`, `raw`, `calendar`, `year`, `month`, `day`, `precision`, `certainty`, `evidence`, `note`. A missing component is `null`. Preserve separate paired expressions with their own IDs and shared parent event/fact. Use `role` to distinguish a start, end, report or correction date. Explain abbreviated or contextual dates.

Numeric months encode month names. Hijri months run from Muharrem=1 to Zilhicce=12. For Gregorian, Julian and Rumi dates use January/Kânunusani=1, Şubat=2, Mart=3, Nisan=4, Mayıs=5, Haziran=6, Temmuz=7, Ağustos=8, Eylül=9, Teşrinievvel=10, Teşrinisani=11 and Kânunuevvel=12. This is a civil month-label encoding, not the Rumi fiscal ordinal convention starting with Mart=1. Preserve the native year unchanged, including January/February; this encoding does not convert the date to Gregorian. Retain the month wording in `raw`; use `null` if it cannot be identified.

Payments retain `payment_id`, `component`, `amount_raw`, `amount`, `currency_raw`, `period_raw`, `amount_role`, `certainty`, `evidence`, `note`. `amount_role` distinguishes level, increment, decrement, allowance, fee, arrears, deduction, total and unknown. The amount is not automatically a monthly kuruş salary. Keep the exact unit and basis.

The exporter creates linked CSV tables and SQLite, preserving the original structured JSON and all prepared source segments. Read the generated column headers rather than assume the old research dataset's column names. Derived education scores, numeric place/job classifications, reconciled identities and annual panels are outside this extraction contract.
