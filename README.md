# sicilahval

**Fatih Kansoy** · [Türkçe](README.tr.md) · [English paper](docs/papers/sicilahval_en.pdf) · [Türkçe makale](docs/papers/sicilahval_tr.pdf)

A Python package and LLM skill for converting complete Sicill-i Ahvâl biographies into evidence-linked **CSV, JSON and SQLite**. It retains personal/family details, education, languages, careers, native dates, payment components, legal statements, corrections and open-ended facts.

The LLM reads and structures the source. Python prepares the text, validates quotations and links, and exports the tables. Using the skill in your existing assistant requires no separate API key.

## Install

Python 3.10 or later:

```sh
python -m pip install "sicilahval @ git+https://github.com/kansoy/ottoman-personnel-tools.git@v0.1.0"
sicilahval install-skill --target codex --scope user
# Or: sicilahval install-skill --target claude --scope user
```

Use `--scope project` for the current project, `--target agents` for a shared Agent Skills directory, or `--path` for a custom parent directory. The [standalone skill](skills/sicilahval) includes Python helpers; an uploadable ZIP is on the [release page](https://github.com/kansoy/ottoman-personnel-tools/releases/tag/v0.1.0). A host with file access and Python execution is required; skill discovery varies by client.

## Use

In Codex, request:

> Use $sicilahval to extract every complete biography and addition from this document. Preserve details and uncertainty. Return CSV and SQLite with an English review summary.

In Claude Code, invoke `/sicilahval` with the same request. Turkish and English summaries/notes are supported; original quotations and names retain their spelling. Field names stay stable.

```sh
sicilahval prepare records.docx --out work --language en
# The LLM reads the text and writes work/records.json.
sicilahval validate work/records.json --source work/source.json
sicilahval export work/records.json --source work/source.json --out data
```

TXT, Markdown, DOCX, text PDF, HTML, RTF and ODT are supported. Text PDFs require `pypdf`; the other readers use the Python standard library. For scans and images, the skill uses an available transcription/OCR workflow and retains its review limits. See [tested formats](docs/validation.md).

## Examples and checks

```sh
sicilahval demo --out example-output --language en
python -m unittest discover -s tests -v
```

[Two real records](examples/sicilahval) show Manuk Filcancıyan’s schooling, appointments, pay changes and later name/faith change, and Zenop Tangaryan’s career with conflicting birth-year statements. The supplied transcription and exact archival references accompany the readings. [Validation notes](docs/validation.md) report the checks actually run.

The output contains linked records, facts, events, dates, payments, evidence, coverage and source segments. Unknown values remain distinct from zero; source claims remain distinct from inference. Research classifications, numeric place/job codes, identity merging and annual panels are separate tasks.

Mechanical validation cannot prove historical accuracy or complete semantic extraction. Review difficult readings against the source. [Reading rules](src/sicilahval/skill/references/workflow.md) · [Schema](src/sicilahval/schema.json).

## Cite

Kansoy, Fatih. 2026. *sicilahval: Evidence-linked extraction of Ottoman personnel records*. Version 0.1.0. https://github.com/kansoy/ottoman-personnel-tools.

[CITATION.cff](CITATION.cff) · [BibTeX](docs/citation.bib) · [English methods note](docs/papers/sicilahval_en.pdf) · [Türkçe yöntem notu](docs/papers/sicilahval_tr.pdf)

Cite historical publications and archival records separately. Apache-2.0 covers the software; the private [Ottoman Bureaucracy](https://ottomanbureaucracy.com) dataset is not distributed here; only the two selected transcription examples are included. The earlier `personnel_evidence` module is preserved: [provenance](SOURCE_ATTRIBUTION.md).
