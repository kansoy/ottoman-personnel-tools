"""Text readers for common HTML, OpenDocument and RTF sources.

These readers preserve accessible text. They do not render layout or OCR images.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
from xml.etree import ElementTree as ET
import zipfile


def utf8(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Text input must be UTF-8; convert a copy and preserve its original separately.") from exc


class _HTMLText(HTMLParser):
    BLOCKS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th",
              "section", "article", "blockquote", "pre", "br", "hr", "header", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.segments: list[dict] = []
        self.parts: list[str] = []
        self.start_line = 1
        self.skip = 0
        self.images = False

    def flush(self):
        text = "".join(self.parts)
        if text.strip():
            self.segments.append({"text": text, "locator": {"part": "html", "line": self.start_line,
                                  "block": len(self.segments) + 1}})
        self.parts = []
        self.start_line = self.getpos()[0]

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.flush()
            self.skip += 1
        elif not self.skip:
            if tag in self.BLOCKS:
                self.flush()
            if tag == "img":
                self.images = True
                alt = dict(attrs).get("alt")
                if alt:
                    self.parts.append("[image alt: " + alt + "]")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        elif not self.skip and tag in self.BLOCKS:
            self.flush()

    def handle_data(self, data):
        if not self.skip:
            if not self.parts:
                self.start_line = self.getpos()[0]
            self.parts.append(data)


def html_segments(raw: bytes) -> tuple[list[dict], list[str]]:
    reader = _HTMLText()
    reader.feed(utf8(raw))
    reader.close()
    reader.flush()
    warnings = ["HTML accessible text is read without executing scripts or fetching links; navigation and hidden text need boundary review."]
    if reader.images:
        warnings.append("HTML contains images; only supplied alt text is retained, without OCR.")
    return reader.segments, warnings


def odt_segments(path: Path) -> tuple[list[dict], list[str]]:
    text_ns = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
    office_ns = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
    segments: list[dict] = []
    warnings = ["ODT locators describe XML paragraphs and notes, not printed page numbers; review layout and revisions."]

    def paragraph_text(node):
        parts = []

        def walk(element):
            if element.tag == text_ns + "note":
                kind = element.get(text_ns + "note-class", "footnote")
                parts.append(f"[{kind}:{element.get(text_ns + 'id', '?')}]")
                return
            if element.tag == text_ns + "tab":
                parts.append("\t")
            elif element.tag == text_ns + "line-break":
                parts.append("\n")
            elif element.tag == text_ns + "s":
                parts.append(" " * int(element.get(text_ns + "c", "1")))
            if element.text:
                parts.append(element.text)
            for child in element:
                walk(child)
                if child.tail:
                    parts.append(child.tail)
        walk(node)
        return "".join(parts)

    with zipfile.ZipFile(path) as archive:
        if "content.xml" not in archive.namelist():
            raise ValueError("ODT has no content.xml")
        root = ET.fromstring(archive.read("content.xml"))
        body = root.find(".//" + office_ns + "text")
        if body is None:
            raise ValueError("ODT has no office:text body")
        notes = list(body.iter(text_ns + "note"))
        note_descendants = {id(node) for note in notes for node in note.iter()}
        for number, paragraph in enumerate((p for p in body.iter() if p.tag in (text_ns + "p", text_ns + "h")
                                            and id(p) not in note_descendants), 1):
            text = paragraph_text(paragraph)
            if text.strip():
                segments.append({"text": text, "locator": {"part": "odt", "paragraph": number,
                    "element": paragraph.tag.rsplit("}", 1)[-1]}})
        for note in notes:
            for number, paragraph in enumerate(note.iter(text_ns + "p"), 1):
                text = paragraph_text(paragraph)
                if text.strip():
                    segments.append({"text": text, "locator": {"part": note.get(text_ns + "note-class", "footnote"),
                        "note_id": note.get(text_ns + "id", ""), "paragraph": number}})
        if "styles.xml" in archive.namelist():
            styles = ET.fromstring(archive.read("styles.xml"))
            for number, paragraph in enumerate(styles.iter(text_ns + "p"), 1):
                text = paragraph_text(paragraph)
                if text.strip():
                    segments.append({"text": text, "locator": {"part": "odt_style_editorial", "paragraph": number}})
        if any(name.startswith("Pictures/") for name in archive.namelist()):
            warnings.append("ODT contains images; image text is not extracted or OCR-checked.")
        if body.find(".//" + text_ns + "tracked-changes") is not None:
            warnings.append("ODT contains tracked changes; review editorial states in the original file.")
    return segments, warnings


def rtf_segments(raw: bytes) -> tuple[list[dict], list[str]]:
    """Decode common RTF text, Unicode escapes and paragraphs; skip binary objects."""
    source = raw.decode("latin-1")
    if not source.lstrip().startswith("{\\rtf"):
        raise ValueError("RTF header is missing")
    declared = re.search(r"\\ansicpg(\d+)", source)
    codec = "cp" + declared.group(1) if declared else "cp1252"
    try:
        b"".decode(codec)
    except LookupError as exc:
        raise ValueError("Unsupported RTF ANSI codepage: " + codec) from exc
    destination_skip = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "object", "filetbl",
                        "listtable", "listoverridetable", "generator", "xmlnstbl", "datastore", "fldinst"}
    stack: list[tuple[bool, int, str | None]] = []
    ignored = False
    unicode_skip = 1
    editorial = None
    fallback = 0
    output: list[str] = []
    skipped: set[str] = set()
    index = 0
    while index < len(source):
        char = source[index]
        if char == "{":
            stack.append((ignored, unicode_skip, editorial))
            editorial = None
            index += 1
            continue
        if char == "}":
            if not stack:
                raise ValueError("Unbalanced RTF group")
            if editorial and not ignored:
                output.append("\n[/" + editorial + "]\n")
            ignored, unicode_skip, editorial = stack.pop()
            index += 1
            continue
        if char != "\\":
            if char not in "\r\n" and not ignored:
                if fallback:
                    fallback -= 1
                else:
                    output.append(char.encode("latin-1").decode(codec, errors="replace"))
            index += 1
            continue
        index += 1
        if index >= len(source):
            break
        symbol = source[index]
        if symbol in "{}\\":
            if not ignored:
                if fallback:
                    fallback -= 1
                else:
                    output.append(symbol)
            index += 1
            continue
        if symbol == "'" and index + 2 < len(source):
            try:
                decoded = bytes.fromhex(source[index + 1:index + 3]).decode(codec)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError("Invalid RTF hexadecimal text escape") from exc
            if not ignored:
                if fallback:
                    fallback -= 1
                else:
                    output.append(decoded)
            index += 3
            continue
        if symbol == "*":
            ignored = True
            skipped.add("optional_destination")
            index += 1
            continue
        match = re.match(r"([A-Za-z]+)(-?\d+)? ?", source[index:])
        if not match:
            if not ignored and symbol in ("~", "_", "-"):
                output.append({"~": "\u00a0", "_": "\u2011", "-": "\u00ad"}[symbol])
            index += 1
            continue
        word, arg = match.group(1), match.group(2)
        index += match.end()
        if word in destination_skip:
            ignored = True
            skipped.add(word)
        elif word == "bin":
            count = max(0, int(arg or "0"))
            index += count
            skipped.add("binary")
        elif word == "uc":
            unicode_skip = max(0, int(arg or "1"))
        elif not ignored:
            if word == "u":
                value = int(arg or "0")
                output.append(chr(value if value >= 0 else value + 65536))
                fallback = unicode_skip
            elif word in ("par", "line", "row"):
                output.append("\n")
            elif word in ("tab", "cell"):
                output.append("\t")
            elif word in ("emdash", "endash", "lquote", "rquote", "ldblquote", "rdblquote", "bullet"):
                output.append({"emdash": "—", "endash": "–", "lquote": "‘", "rquote": "’", "ldblquote": "“", "rdblquote": "”", "bullet": "•"}[word])
            elif word in ("footnote", "header", "footer", "headerl", "headerr", "footerl", "footerr"):
                output.append("\n[" + word + "] ")
                editorial = word
    if stack:
        raise ValueError("Unbalanced RTF groups")
    text = "".join(output).encode("utf-16-le", errors="surrogatepass").decode("utf-16-le", errors="replace")
    segments = [{"text": line, "locator": {"part": "rtf", "paragraph": number}}
                for number, line in enumerate(text.splitlines(), 1) if line.strip()]
    warnings = ["Common RTF text is decoded without rendering; notes and headers are marked inline. Review layout, field results and revisions."]
    if skipped:
        warnings.append("RTF non-text destinations were skipped: " + ", ".join(sorted(skipped)) + "; no OCR is performed.")
    return segments, warnings
