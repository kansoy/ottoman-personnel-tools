"""Command-line interface; semantic extraction belongs to the reader/model."""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from . import __version__
from .demo import write_demo
from .export import export_records
from .install import install_skill
from .intake import prepare_source
from .util import read_json, schema_path, write_json
from .validation import validate_records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sicilahval", description="Prepare, check and export source-grounded Sicill-i Ahval readings.")
    parser.add_argument("--version", action="version", version=f"sicilahval {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Prepare text and source IDs; does not extract biographies")
    prepare.add_argument("input")
    prepare.add_argument("--out", required=True)
    prepare.add_argument("--language", choices=("en", "tr"), default="en")
    for name in ("title", "author", "citation", "url"):
        prepare.add_argument("--" + name)
    validate = commands.add_parser("validate", help="Check structure, exact citations and declared coverage")
    validate.add_argument("records")
    validate.add_argument("--source", required=True)
    validate.add_argument("--original", help="Also verify the original input file hash")
    validate.add_argument("--report")
    export = commands.add_parser("export", help="Export a validated reading to JSON, CSV relations and SQLite")
    export.add_argument("records")
    export.add_argument("--source", required=True)
    export.add_argument("--out", required=True)
    schema = commands.add_parser("schema", help="Print or save the extraction JSON schema")
    schema.add_argument("--out")
    demo = commands.add_parser("demo", help="Export a reviewed real example without a new model call")
    demo.add_argument("--out", required=True)
    demo.add_argument("--language", choices=("en", "tr"), default="en")
    demo.add_argument("--example", choices=("manuk", "zenop", "appointment", "pay_legal"))
    demo.add_argument("--synthetic", action="store_true", help="Use invented internal regression fixtures")
    install = commands.add_parser("install-skill", help="Install the bundled offline skill into a new folder")
    install.add_argument("--target", choices=("codex", "claude", "agents"), default="codex")
    install.add_argument("--scope", choices=("project", "user"), default="project")
    install.add_argument("--path", help="Custom parent directory; creates PARENT/sicilahval")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_source(args.input, args.out, args.language, title=args.title,
                                    author=args.author, citation=args.citation, url=args.url)
        elif args.command == "validate":
            result = validate_records(args.records, args.source, original=args.original)
            if args.report:
                report_path = Path(args.report)
                if report_path.exists():
                    raise ValueError(f"Report already exists: {report_path}")
                report_path.parent.mkdir(parents=True, exist_ok=True)
                write_json(report_path, result)
        elif args.command == "export":
            result = export_records(args.records, args.source, args.out)
        elif args.command == "demo":
            result = write_demo(args.out, args.language, args.example, synthetic=args.synthetic)
        elif args.command == "install-skill":
            result = install_skill(args.target, args.scope, args.path)
        else:
            result = read_json(schema_path())
            if args.out:
                output = Path(args.out)
                if output.exists():
                    raise ValueError(f"Schema output already exists: {output}")
                output.parent.mkdir(parents=True, exist_ok=True)
                write_json(output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "validate" and not result["valid"] else 0
    except (ValueError, OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
