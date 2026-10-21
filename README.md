# Personnel Evidence Toolkit

**First open software component of [Ottoman Bureaucracy](https://ottomanbureaucracy.com), released 21 October 2026 under Apache-2.0.**

This is a functional first module extracted from the Ottoman Bureaucracy research project. It prepares explicitly selected source appearances, identifies literal monetary occurrences, binds structured readings to exact source lines and page references, checks their mechanical consistency, and exports review candidates to relational SQLite and CSV. It preserves separate calendar expressions, unknown values, explicit zero amounts and event/payment relationships.

It is a limited software component, not the complete research platform, an OCR engine, a model, or the approximately 50,000-official dataset. Source-local appearance IDs do not establish that two records describe the same historical person. A mechanically supported quotation does not establish historical truth or extraction completeness.

## Run locally

Use Python 3.10 or later with SQLite JSON functions. The toolkit has been tested with Python 3.13.9 and 3.14. There are no third-party Python dependencies and no installation step. Run from this directory:

```sh
python3 -m unittest discover -s tests -v
python3 -m examples.synthetic_example --out example-output
```

The example contains wholly invented text and a hand-written structured reading. It makes no model call. The synthetic document hashes do not represent a real PDF or archival image. The example refuses to overwrite an existing output directory. Tests use temporary directories; one complete export test forbids socket creation.

The example creates one source-local candidate, two events, two separate calendar records and two payment components. A literal salary of `0` remains `0`; an allowance with no recorded amount remains SQL `NULL` and a blank CSV numeric field. Multiple calendar expressions do not multiply payment rows. The derived `career_observations` view has three rows: two payment components for the dated event and one row retaining its undated event. These are not annual observations.

For your own **lawfully usable** text and already obtained candidate readings:

```sh
python3 -m personnel_evidence.intake --input appearance-pool.jsonl \
  --appearance-id selected-source-appearance --out units.jsonl
python3 -m personnel_evidence.export --units units.jsonl \
  --results candidate-readings.json --out-dir new-export-directory
```

The intake requires explicit selection, source/native-text SHA256 fields and page-labelled source segments. It rejects unreviewed source boundaries unless deliberately included as flagged candidates. Hash fields are carried and compared; this module does not fetch a PDF or independently prove its hash against an absent original. The exporter rejects mismatched result/source identifiers or source hashes and marks exported results as candidates requiring source review. It retains citation mismatches and validation issues rather than silently declaring them corrected. Use a new export directory: the inherited export function replaces its output database if the same destination is reused.

## Contents and provenance

- `personnel_evidence/`: nine byte-identical files copied from the project's existing `tools/public_personnel/` module. `SOURCE_MANIFEST.json` records original relative paths and SHA256 values. Relative imports are preserved under the new package directory.
- `schema.json` and `prompt.txt`: the existing output contract and extraction instructions. The prompt describes a desired model-assisted workflow; including it does not claim a particular model meets those requirements. No model runner is included.
- `examples/` and `tests/`: newly written, entirely synthetic demonstration and six offline tests.
- `LICENSE` and `NOTICE`: software licence and attribution.

The optional Anthropic runner in the parent project, its provider pricing, credential-helper support and runner-dependent reprocessing code are deliberately excluded. This toolkit has no API execution path and is not an OpenAI API integration. The parent project separately uses Codex; those workflows are outside this first module. There are no external runtime imports, network clients, credentials, real personnel records, publication text, scans, saved model responses or usage logs in this repository.

## Licence and data boundary

The software, schema, prompt and synthetic examples/tests in this repository are licensed under the Apache License, Version 2.0; see `LICENSE` and `NOTICE`. This grant does not cover the private parent repository, research datasets, source publications, historical records or images, none of which is distributed here. You are responsible for obtaining appropriate rights for any inputs you use with the software.

The larger project aims to build a validated corpus covering approximately 50,000 Ottoman officials. This is planned coverage, not a completed dataset or a promise of processing capacity. The completed, validated research data and documentation are intended for a later public research release after construction, source verification, quality checks and rights review, under separately announced terms. Current website access terms remain in effect.

## Contributing

This is a new public module; no broad software adoption or historical extraction accuracy is claimed. Issues and pull requests are welcome, especially reproducible bugs, source-grounding checks, calendar preservation and safer export behaviour. Use invented fixtures with no real source quotations, research records, credentials or private inputs. Run the offline tests before proposing a change. For software provenance and scope, see `SOURCE_ATTRIBUTION.md`.
