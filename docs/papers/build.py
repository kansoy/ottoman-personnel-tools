#!/usr/bin/env python3
"""Build and mechanically check the two sicilahval technical-note editions."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def run(args: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        args, cwd=cwd, text=True, capture_output=True, check=True,
        env={**os.environ, "SOURCE_DATE_EPOCH": "1792800000", "FORCE_SOURCE_DATE": "1"},
    )
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="also render review PNGs with Poppler")
    args = parser.parse_args()
    checks: dict[str, object] = {}
    for lang in ("en", "tr"):
        project = ROOT / lang
        build = ROOT / "build" / lang
        build.mkdir(parents=True, exist_ok=True)
        # Each editor project is self-contained; the shared copy is authoritative.
        shutil.copyfile(ROOT / "style" / "kansoy.sty", project / "kansoy.sty")
        assert (project / "kansoy.sty").read_bytes() == (ROOT / "style" / "kansoy.sty").read_bytes()
        run(
            ["latexmk", "-pdf", "-quiet", "-interaction=nonstopmode",
             "-halt-on-error", "-outdir=../build/" + lang, "main.tex"],
            cwd=project,
        )
        pdf = build / "main.pdf"
        info = run(["pdfinfo", str(pdf)])
        metadata = {}
        for line in info.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        assert metadata["Pages"] == "3", (lang, metadata["Pages"])
        assert metadata["Author"] == "Fatih Kansoy", (lang, metadata["Author"])
        assert metadata["Title"].startswith("sicilahval:"), (lang, metadata["Title"])
        text = run(["pdftotext", "-layout", str(pdf), "-"])
        for required in ("sicilahval", "Fatih Kansoy", "Manuk", "Zenop", "Sarıyıldız", "kansoy@gmail.com", "fatih.ai", "CITATION.cff"):
            assert required in text, (lang, required)
        assert "--language " + lang in text, (lang, "command hyphens")
        source = (project / "main.tex").read_text()
        heading = "\\section{References}" if lang == "en" else "\\section{Kaynakça}"
        assert source.split(heading)[1].count("\\smallref{") == 1, (lang, "one scholarly reference")
        for removed in ("Başaran", "Saylan", "Bergama", "Gümüşhane"):
            assert removed not in text, (lang, "removed reference", removed)
        assert "mailto:kansoy@gmail.com" in (project / "kansoy.sty").read_text()
        assert "https://fatih.ai" in (project / "kansoy.sty").read_text()
        assert "\ufffd" not in text and "\u25a0" not in text, (lang, "missing glyph")
        log = (build / "main.log").read_text(errors="replace")
        for forbidden in ("Overfull", "Missing character", "Undefined control sequence", "LaTeX Warning:"):
            assert forbidden not in log, (lang, forbidden)
        out = ROOT / ("sicilahval_" + lang + ".pdf")
        shutil.copyfile(pdf, out)
        if args.render:
            run(["pdftoppm", "-scale-to", "1500", "-png", str(out), str(build / "page")])
        checks[lang] = {
            "pdf": out.name,
            "pages": int(metadata["Pages"]),
            "author": metadata["Author"],
            "title": metadata["Title"],
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "bytes": out.stat().st_size,
            "source": lang + "/main.tex",
            "checks": [
                "exactly_three_pages", "author_and_title_metadata", "Turkish_glyph_text",
                "literal_command_hyphens", "no_missing_glyphs", "no_overfull_boxes",
                "no_LaTeX_warnings", "self_contained_style_matches_shared_copy",
                "single_scholar_reference_Sariyildiz_2009", "author_email_and_website",
            ],
        }
    receipt = {
        "version": "0.1.5",
        "release_date": "2026-10-24",
        "toolchain": "latexmk with pdfLaTeX; Poppler pdfinfo and pdftotext",
        "notes": checks,
        "visual_review": "See REVIEW.md; mechanical checks do not establish visual quality.",
    }
    (ROOT / "verification.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
