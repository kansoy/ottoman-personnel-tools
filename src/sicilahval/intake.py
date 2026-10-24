"""Preserve native file hashes and stable text segments without OCR."""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .util import digest_bytes, json_text, new_directory, schema_path, write_json
from .formats import html_segments, odt_segments, rtf_segments, utf8

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == W + "tab":
            parts.append("\t")
        elif node.tag in (W + "br", W + "cr"):
            parts.append("\n")
        elif node.tag in (W + "footnoteReference", W + "endnoteReference"):
            kind = "footnote" if node.tag == W + "footnoteReference" else "endnote"
            parts.append(f"[{kind}:{node.attrib.get(W + 'id', '?')}]")
    return "".join(parts)


def _docx_segments(path: Path) -> tuple[list[dict], list[str]]:
    segments: list[dict] = []
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        if "word/document.xml" not in archive.namelist():
            raise ValueError("DOCX has no word/document.xml")
        root = ET.fromstring(archive.read("word/document.xml"))
        body = root.find(W + "body")
        if body is None:
            raise ValueError("DOCX has no document body")
        paragraph_no = 0
        table_no = 0
        for block in body:
            if block.tag == W + "p":
                paragraph_no += 1
                text = _paragraph_text(block)
                if text.strip():
                    segments.append({"text": text, "locator": {"part": "document", "paragraph": paragraph_no}})
            elif block.tag == W + "tbl":
                table_no += 1
                for row_no, row in enumerate(block.findall(W + "tr"), 1):
                    for cell_no, cell in enumerate(row.findall(W + "tc"), 1):
                        for para_no, paragraph in enumerate(cell.iter(W + "p"), 1):
                            text = _paragraph_text(paragraph)
                            if text.strip():
                                segments.append({"text": text, "locator": {"part": "document", "table": table_no,
                                    "row": row_no, "cell": cell_no, "paragraph": para_no}})
            else:
                paragraphs = list(block.iter(W + "p"))
                for para_no, paragraph in enumerate(paragraphs, 1):
                    text = _paragraph_text(paragraph)
                    if text.strip():
                        segments.append({"text": text, "locator": {"part": "document",
                            "container": block.tag.rsplit("}", 1)[-1], "paragraph": para_no}})
                if paragraphs:
                    warnings.append("Text in a document container was preserved; review its order and boundaries.")
        for kind, part in (("footnote", "word/footnotes.xml"), ("endnote", "word/endnotes.xml")):
            if part not in archive.namelist():
                continue
            notes = ET.fromstring(archive.read(part))
            for note in notes:
                note_id = note.attrib.get(W + "id", "")
                if note.attrib.get(W + "type") in ("separator", "continuationSeparator"):
                    continue
                for para_no, paragraph in enumerate(note.iter(W + "p"), 1):
                    text = _paragraph_text(paragraph)
                    if text.strip():
                        segments.append({"text": text, "locator": {"part": kind, "note_id": note_id, "paragraph": para_no}})
        # Comments and tracked deletions may be editorial evidence; expose their presence.
        if "word/comments.xml" in archive.namelist():
            comments = ET.fromstring(archive.read("word/comments.xml"))
            for comment in comments:
                for para_no, paragraph in enumerate(comment.iter(W + "p"), 1):
                    text = _paragraph_text(paragraph)
                    if text.strip():
                        segments.append({"text": text, "locator": {"part": "comment",
                            "comment_id": comment.attrib.get(W + "id", ""), "paragraph": para_no}})
            warnings.append("Editorial comments are included separately; review whether they are source evidence.")
        for part in sorted(archive.namelist()):
            if not re.fullmatch(r"word/(?:header|footer)\d+\.xml", part):
                continue
            editorial = ET.fromstring(archive.read(part))
            for para_no, paragraph in enumerate(editorial.iter(W + "p"), 1):
                text = _paragraph_text(paragraph)
                if text.strip():
                    segments.append({"text": text, "locator": {"part": "header" if "header" in part else "footer",
                        "xml_part": part, "paragraph": para_no}})
        # Deleted text is evidence of an editorial state, not silently accepted text.
        revision_parts = [part for part in archive.namelist() if re.fullmatch(
            r"word/(?:document|footnotes|endnotes|comments|header\d+|footer\d+)\.xml", part)]
        deleted = inserted = False
        for part in revision_parts:
            revision_root = ET.fromstring(archive.read(part))
            inserted = inserted or revision_root.find(".//" + W + "ins") is not None
            for number, deletion in enumerate(revision_root.iter(W + "del"), 1):
                text = "".join(node.text or "" for node in deletion.iter() if node.tag in (W + "delText", W + "t"))
                if text.strip():
                    deleted = True
                    segments.append({"text": text, "locator": {"part": "tracked_deletion", "xml_part": part,
                        "deletion": number, "revision_id": deletion.attrib.get(W + "id", "")}})
        if root.find(".//" + W + "drawing") is not None or any(n.startswith("word/media/") for n in archive.namelist()):
            warnings.append("DOCX contains embedded images; image text is not extracted or OCR-checked.")
        if deleted:
            warnings.append("Tracked deletions are preserved as separate editorial segments; review revisions in the original document.")
        if inserted:
            warnings.append("Tracked insertions are present in running text; review revisions before choosing a reading.")
        warnings.append("DOCX locators describe XML order, not printed page numbers; headers and footers are separate editorial segments.")
    return segments, warnings


def _pdf_segments(path: Path) -> tuple[list[dict], list[str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF input requires pypdf; install pypdf or the optional pdf extra from the project repository.") from exc
    reader = PdfReader(path)
    segments: list[dict] = []
    empty_pages: list[int] = []
    for page_no, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if not text.strip():
            empty_pages.append(page_no)
        for line_no, line in enumerate(text.splitlines(), 1):
            if line.strip():
                segments.append({"text": line, "locator": {"part": "pdf", "page": page_no, "line": line_no}})
    warnings = ["PDF text order and page boundaries require visual review; no OCR is performed."]
    if empty_pages:
        warnings.append("Pages with no extracted text: " + ", ".join(map(str, empty_pages)))
    return segments, warnings


def prepare_source(input_path: str | Path, out: str | Path, language: str = "en", *,
                   title: str | None = None, author: str | None = None,
                   citation: str | None = None, url: str | None = None) -> dict:
    """Prepare a new workspace. Does not identify or extract biographies."""
    if language not in ("en", "tr"):
        raise ValueError("language must be en or tr")
    path = Path(input_path)
    if not path.is_file():
        raise ValueError(f"Input file does not exist: {path}")
    suffix = path.suffix.lower()
    raw = path.read_bytes()
    warnings: list[str] = []
    if suffix in (".txt", ".md", ".markdown"):
        text = utf8(raw)
        segments = [{"text": line, "locator": {"part": "text", "line": number}}
                    for number, line in enumerate(text.splitlines(), 1) if line.strip()]
    elif suffix == ".docx":
        segments, warnings = _docx_segments(path)
    elif suffix == ".pdf":
        segments, warnings = _pdf_segments(path)
    elif suffix in (".html", ".htm"):
        segments, warnings = html_segments(raw)
    elif suffix == ".odt":
        segments, warnings = odt_segments(path)
    elif suffix == ".rtf":
        segments, warnings = rtf_segments(raw)
    else:
        raise ValueError("Supported inputs: .txt, .md, .docx, text-based .pdf, .html/.htm, .odt, common .rtf")
    if not segments:
        raise ValueError("No text was extracted. Supply a transcription or separately reviewed OCR text.")
    sha256 = digest_bytes(raw)
    source_id = "src-" + sha256[:16]
    for number, segment in enumerate(segments, 1):
        segment["segment_id"] = f"s{number:06d}"
    source = {"schema_version": "1.0", "source_id": source_id, "sha256": sha256,
              "file_name": path.name, "format": suffix.lstrip("."), "language": language,
              "metadata": {"title": title, "author": author, "citation": citation, "url": url},
              "warnings": warnings, "segments": segments,
              "text_sha256": digest_bytes(json_text(segments).encode("utf-8"))}
    target = new_directory(out)
    write_json(target / "source.json", source)
    write_json(target / "records.template.json", {"schema_version": "1.0", "source_id": source_id,
        "language": language, "records": [], "excluded_segments": []})
    (target / "source.txt").write_text("\n\n".join(
        f"[{s['segment_id']}] {s['text']}" for s in segments) + "\n", encoding="utf-8")
    shutil.copyfile(schema_path(), target / "schema.json")
    return {"source_id": source_id, "sha256": sha256, "segments": len(segments),
            "workspace": str(target), "language": language, "warnings": warnings,
            "next": "Read the complete source and use the sicilahval skill to create records.json."}
