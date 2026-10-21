"""Deterministic source-line and monetary-occurrence anchors for public-source units.
Every currency mention is retained; an anchor does not by itself imply salary.
"""
from __future__ import annotations
import re
from . import literals as LITERAL

TOKEN = re.compile(r"\d+(?:[.,]\d+)*|[^\W\d_]+|[^\w\s]")
CURRENCY = re.compile(
    r"(?<!\w)(?P<unit>[gk]uru[şsĢġ]|santim|mecidiye|alt[ıi]n|altun|frank|franc|lira|lire|akçe|para)(?P<suffix>\w*)", re.I)
SUBUNITS = {"para", "santim"}
DISTRIBUTIVES = {"birer": 1, "ikiser": 2, "ucer": 3, "dorder": 4,
                "beser": 5, "altisar": 6, "yediser": 7, "sekizer": 8,
                "dokuzar": 9, "onar": 10, "yirmiser": 20, "otuzar": 30,
                "kirkar": 40, "elliser": 50, "yuzer": 100, "biner": 1000}
DISTRIBUTIVE_CARDINALS = dict(zip(DISTRIBUTIVES,
    ("bir", "iki", "uc", "dort", "bes", "alti", "yedi", "sekiz", "dokuz",
     "on", "yirmi", "otuz", "kirk", "elli", "yuz", "bin")))


def numeric_literal(raw):
    """Literal cardinal or explicitly distributive reading, never arithmetic."""
    folded = LITERAL.fold(raw)
    value = LITERAL.numeric_literal(raw)
    if any(char.isdigit() for char in folded):
        return value
    words = folded.split()
    if any(word in DISTRIBUTIVE_CARDINALS for word in words):
        folded = " ".join(DISTRIBUTIVE_CARDINALS.get(word, word) for word in words)
        value = LITERAL.numeric_literal(folded)
    if value is None:
        return None
    compact = re.sub(r"\bbucuk\b", "", folded).replace(" ", "")
    tokens = re.findall(LITERAL.TOKEN_NUMBER, compact)
    if "".join(tokens) != compact:
        return None

    def under_hundred(group):
        if not group:
            return True
        vals = [LITERAL.UNITS.get(token) for token in group]
        return (len(vals) == 1 and vals[0] is not None
                or len(vals) == 2 and vals[0] in range(10, 100, 10) and vals[1] in range(1, 10))

    def under_thousand(group):
        if group.count("yuz") > 1:
            return False
        if "yuz" not in group:
            return under_hundred(group)
        at = group.index("yuz")
        prefix = group[:at]
        return ((not prefix or len(prefix) == 1 and LITERAL.UNITS.get(prefix[0]) in range(1, 10))
                and under_hundred(group[at + 1:]))

    group, previous_scale = [], float("inf")
    for token in tokens:
        if token in ("bin", "milyon"):
            scale = {"bin": 1000, "milyon": 1000000}[token]
            if scale >= previous_scale or not under_thousand(group):
                return None
            previous_scale, group = scale, []
        else:
            group.append(token)
    return value if under_thousand(group) else None


def _number_before(text, tokens, position):
    """Immediately preceding complete amount phrase with native offsets."""
    before = [token for token in tokens if token.end() <= position]
    if not before or text[before[-1].end():position].strip():
        return None
    selected, cursor, unsafe = [], position, []
    nearest_digits = before[-1].group()[0].isdigit()
    for index in range(len(before) - 1, max(-1, len(before) - 19), -1):
        token = before[index]
        if text[token.end():cursor].strip():
            break
        folded = LITERAL.fold(token.group())
        accepted = (numeric_literal(token.group()) is not None or folded == "bucuk")
        # Keep an observed corrupt numeric word or imprecise suffix attached to
        # its numeric prefix. Stopping here would silently turn 'yüz almış beş'
        # into clean5, or discard the quantity in 'on yedi bin küsur'. These
        # spellings are preserved; neither an OCR correction nor an exact total
        # is inferred. Ordinary prose 'almış beş guruş' has no numeric prefix.
        prior = before[index - 1] if index else None
        numeric_prefix = (prior is not None
                          and not text[prior.end():token.start()].strip()
                          and numeric_literal(prior.group()) is not None)
        if not accepted and numeric_prefix:
            if folded == "almis" and selected:
                accepted = True
                unsafe.append("malformed_numeric_phrase; native word almış is not a clean cardinal")
            elif folded == "kusur":
                accepted = True
                unsafe.append("imprecise_numeric_phrase; küsur does not state an exact amount")
        if not accepted:
            break
        if folded != "bucuk" and token.group()[0].isdigit() != nearest_digits:
            break
        selected.append(token)
        cursor = token.start()
    if not selected:
        return None
    start, end = selected[-1].start(), selected[0].end()
    literal = text[start:end]
    return {"start": start, "end": end, "raw": literal,
            "value": None if unsafe else numeric_literal(literal), "flags": unsafe}


def _line_ids(lines, start, end):
    return [line["id"] for line in lines
            if line["source_offset_start"] < end and line["source_offset_end"] > start]


def _pages(lines, ids):
    selected = set(ids)
    return sorted({line["pdf_page"] for line in lines if line["id"] in selected})


def _currency_mentions(text, lines):
    tokens = list(TOKEN.finditer(text))
    mentions = []
    for match in CURRENCY.finditer(text):
        number = _number_before(text, tokens, match.start())
        start = number["start"] if number else match.start()
        ids = _line_ids(lines, start, match.end())
        mentions.append({"source_offset_start": start, "source_offset_end": match.end(),
                         "currency_offset_start": match.start(), "currency_offset_end": match.end(),
                         "amount_literal": number["raw"] if number else "",
                         "amount": number["value"] if number else None,
                         "currency_raw": match.group("unit"),
                         "currency_token_raw": match.group(),
                         "currency_unit": LITERAL.fold(match.group("unit")),
                         "line_ids": ids, "pdf_pages": _pages(lines, ids),
                         "source_raw": text[start:match.end()],
                         "reading_status": ("literal_reading" if number and number["value"] is not None
                                            else "unresolved_amount"),
                         "flags": ((number.get("flags", []) if number else [])
                                   + ([] if number and number["value"] is not None else
                                      ["currency_mention_without_clean_immediate_amount; classify_or_explicitly_exclude"]))})
    return mentions


def _implicit_mentions(text, lines, explicit):
    """Bounded, source-visible currency ellipsis and distributive candidates.

    A cardinal immediately after a closing date parenthesis and before 've'
    is retained when a nearby following clause supplies an explicit currency.
    The source statement remains an ellipsis, never a calculated salary level.
    All other unresolved currency tokens are already retained separately.
    """
    tokens = list(TOKEN.finditer(text))
    implicit = []
    for conjunction in re.finditer(r"(?<!\w)ve(?!\w)", text, re.I):
        number = _number_before(text, tokens, conjunction.start())
        if not number:
            continue
        before = text[max(0, number["start"] - 100):number["start"]]
        following = next((m for m in explicit if m["currency_offset_start"] > conjunction.end()
                          and m["currency_offset_start"] - conjunction.end() <= 280), None)
        if not following:
            continue
        words = LITERAL.fold(number["raw"]).split()
        distributive = bool(words and words[0] in DISTRIBUTIVES)
        follows_date = before.rstrip().endswith(")")
        if not distributive and not follows_date:
            continue
        # A source number already attached to a currency is not an ellipsis.
        if any(m["source_offset_start"] <= number["start"] < m["source_offset_end"] for m in explicit):
            continue
        ids = _line_ids(lines, number["start"], number["end"])
        proof_ids = _line_ids(lines, number["start"], following["source_offset_end"])
        flags = ["currency_elliptical; supplied_by_following_source_clause_not_repeated_in_literal"]
        if distributive:
            flags.append("distributive_amount; one_statement_can_apply_to_explicitly_stated_multiple_intervals")
        implicit.append({"source_offset_start": number["start"], "source_offset_end": number["end"],
                         "currency_offset_start": None, "currency_offset_end": None,
                         "amount_literal": number["raw"], "amount": number["value"],
                         "currency_raw": "", "currency_token_raw": "", "currency_unit": "",
                         "line_ids": ids, "pdf_pages": _pages(lines, ids),
                         "source_raw": text[number["start"]:number["end"]],
                         "reading_status": "distributive_literal_reading" if distributive else
                                           "currency_elliptical_literal_reading" if number["value"] is not None else
                                           "unresolved_amount",
                         "following_currency_evidence_line_ids": proof_ids,
                         "following_currency_evidence_raw": text[number["start"]:following["source_offset_end"]],
                         "flags": flags})
    return implicit


def prepare(unit):
    """Return a fresh deterministic source packet; input unit remains untouched."""
    lines, bits, offset = [], [], 0
    for segment in unit["body_segments"]:
        # split('\n') retains empty native lines and every original character.
        for raw in segment["text_raw"].split("\n"):
            line = {"id": f"L{len(lines) + 1:03d}", "text": raw,
                    "pdf_page": segment["pdf_page"], "printed_page": segment.get("printed_page"),
                    "segment_id": segment.get("segment_id", ""),
                    "source_offset_start": offset, "source_offset_end": offset + len(raw)}
            lines.append(line)
            bits.append(raw)
            offset += len(raw) + 1
    text = "\n".join(bits)
    explicit = _currency_mentions(text, lines)
    implicit = _implicit_mentions(text, lines, explicit)
    anchors, used = [], set()
    for n, mention in enumerate(explicit):
        if n in used:
            continue
        members = [mention]
        if n + 1 < len(explicit):
            next_mention = explicit[n + 1]
            bridge = text[mention["currency_offset_end"]:next_mention["source_offset_start"]]
            if (mention["currency_unit"] in ("gurus", "kurus")
                    and next_mention["currency_unit"] in SUBUNITS
                    and (mention["amount"] is not None or mention["amount_literal"])
                    and next_mention["amount"] is not None
                    and not bridge.strip()):
                members.append(next_mention)
                used.add(n + 1)
        sub = members[1] if len(members) == 2 else None
        end = members[-1]["source_offset_end"]
        ids = _line_ids(lines, mention["source_offset_start"], end)
        anchors.append({**mention, "anchor_kind": "compound_currency" if sub else "currency_mention",
                        "source_offset_end": end, "source_raw": text[mention["source_offset_start"]:end],
                        "line_ids": ids, "pdf_pages": _pages(lines, ids),
                        "subunit_amount_literal": sub["amount_literal"] if sub else "",
                        "subunit_amount": sub["amount"] if sub else None,
                        "subunit_currency_raw": sub["currency_raw"] if sub else "",
                        "subunit_currency_token_raw": sub["currency_token_raw"] if sub else "",
                        "currency_mentions": members})
    for mention in implicit:
        anchors.append({**mention, "anchor_kind": "currency_ellipsis",
                        "subunit_amount_literal": "", "subunit_amount": None,
                        "subunit_currency_raw": "", "subunit_currency_token_raw": "",
                        "currency_mentions": []})
    anchors.sort(key=lambda a: (a["source_offset_start"], a["source_offset_end"], a["anchor_kind"]))
    for n, anchor in enumerate(anchors, 1):
        anchor["id"] = f"M{n:03d}"
        line_positions = [i for i, line in enumerate(lines) if line["id"] in anchor["line_ids"]]
        if line_positions:
            lo, hi = max(0, min(line_positions) - 1), min(len(lines), max(line_positions) + 2)
            anchor["context_line_ids"] = [line["id"] for line in lines[lo:hi]]
        else:
            anchor["context_line_ids"] = []
    assert sum(len(a["currency_mentions"]) for a in anchors) == len(explicit)
    return {"person_key": unit.get("person_key"), "section": unit["section"], "name": unit["name"],
            "source_id": unit.get("source_id"), "source_pdf_sha256": unit.get("source_pdf_sha256"),
            "lines": lines, "money_anchors": anchors,
            "coverage": {"native_lines": len(lines), "currency_mentions": len(explicit),
                         "resolved_currency_mentions": sum(m["amount"] is not None for m in explicit),
                         "unresolved_currency_mentions": sum(m["amount"] is None for m in explicit),
                         "compound_anchors": sum(a["anchor_kind"] == "compound_currency" for a in anchors),
                         "currency_elliptical_anchors": len(implicit), "money_anchors": len(anchors)},
            "interpretation": "Native text anchors for model classification; currency mentions are not automatically focal salary; no silent currency exclusions."}


