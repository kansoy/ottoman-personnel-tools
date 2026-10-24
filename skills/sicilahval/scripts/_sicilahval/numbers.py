"""Bounded literal-number checks; no currency conversion or date completion.

The Turkish cardinal routine follows the existing personnel_evidence helpers.
Ambiguous punctuation retains both decimal and grouping readings for review.
"""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal

TR = {"sifir": 0, "bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5, "alti": 6,
      "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10, "yirmi": 20, "otuz": 30,
      "kirk": 40, "elli": 50, "altmis": 60, "yetmis": 70, "seksen": 80, "doksan": 90}
EN = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
      "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
      "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
      "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
      "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower().replace("ı", "i"))
                   if not unicodedata.combining(c))


def _cardinal(text: str, words: dict, hundred: str, thousand: str, million: str) -> Decimal | None:
    raw = re.sub(r"[\s'’\-]", "", fold(text))
    half = Decimal(0)
    if raw.endswith("bucuk"):
        raw = raw[:-5]
        half = Decimal("0.5")
    tokens = re.findall("|".join(sorted(set(words) | {hundred, thousand, million}, key=len, reverse=True)), raw)
    if not raw or "".join(tokens) != raw:
        return None
    total = group = 0
    for token in tokens:
        if token in words:
            group += words[token]
        elif token == hundred:
            group = max(group, 1) * 100
        elif token == thousand:
            total += max(group, 1) * 1000
            group = 0
        else:
            total = (total + max(group, 1)) * 1000000
            group = 0
    return Decimal(total + group) + half


def literal_values(text: str) -> set[Decimal]:
    """Read complete amount literals; an empty set means mechanically unchecked."""
    raw = fold(text).strip()
    raw = re.sub(r"\s*(?:kurus|gurus|lira|para|piasters?|pounds?)\s*$", "", raw).strip()
    values: set[Decimal] = set()
    if re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", raw):
        values.add(Decimal(raw.replace(",", ".")))
    if re.fullmatch(r"[+-]?\d{1,3}(?:[.,\s]\d{3})+", raw):
        values.add(Decimal(re.sub(r"[.,\s]", "", raw)))
    for words, hundred, thousand, million in ((TR, "yuz", "bin", "milyon"), (EN, "hundred", "thousand", "million")):
        value = _cardinal(raw, words, hundred, thousand, million)
        if value is not None:
            values.add(value)
    return values


def _number_spans(text: str) -> list[tuple[int, int, set[Decimal]]]:
    matches = []
    raw = fold(text)
    for match in re.finditer(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?(?!\w)", raw):
        matches.append((match.start(), match.end(), literal_values(match.group())))
    for words, scales in ((TR, ("yuz", "bin", "milyon", "bucuk")), (EN, ("hundred", "thousand", "million"))):
        tokens = "|".join(sorted(set(words) | set(scales), key=len, reverse=True))
        for match in re.finditer(r"(?<!\w)(?:" + tokens + r")(?:[\s-]*(?:" + tokens + r"))*(?!\w)", raw):
            matches.append((match.start(), match.end(), literal_values(match.group())))
    return matches


def number_runs(text: str) -> set[Decimal]:
    return set().union(*(values for _, _, values in _number_spans(text)))


def day_values(text: str) -> set[int]:
    """Read bounded day expressions, including inflected Turkish forms.

    These are literal candidates, not a calendar parser. An empty set means the
    spelling remains unchecked; it must not be rejected because a year parsed.
    """
    raw = fold(text)
    year_spans = [(begin, end) for begin, end, _ in _number_spans(raw)
                  if re.match(r"\s*(?:senesi|senesinde|sene|yili|yilinda|year)\b", raw[end:])]
    matches = [(m.start(), m.end(), int(m.group(1))) for m in re.finditer(
        r"(?<!\d)([0-3]?\d)(?:st|nd|rd|th)?(?!\d)", raw) if 1 <= int(m.group(1)) <= 31]
    forms = {
        1: ("birinde", "birinci", "birincisinde"),
        2: ("ikisinde", "ikinci", "ikincisinde"),
        3: ("ucunde", "ucuncu", "ucuncusunde"),
        4: ("dordunde", "dorduncu", "dorduncusunde"),
        5: ("besinde", "besinci", "besincisinde"),
        6: ("altisinda", "altinci", "altincisinda"),
        7: ("yedisinde", "yedinci", "yedincisinde"),
        8: ("sekizinde", "sekizinci", "sekizincisinde"),
        9: ("dokuzunda", "dokuzuncu", "dokuzuncusunda"),
        10: ("onunda", "onuncu", "onuncusunda"),
        20: ("yirmisinde", "yirminci", "yirmincisinde"),
        30: ("otuzunda", "otuzuncu", "otuzuncusunda"),
    }
    for value in range(1, 32):
        tens, unit = divmod(value, 10)
        if value in forms:
            candidates = forms[value]
        else:
            prefix = {1: "on", 2: "yirmi", 3: "otuz"}[tens]
            candidates = tuple(prefix + " " + form for form in forms[unit])
        for candidate in candidates:
            pattern = r"(?<!\w)" + r"\s*".join(map(re.escape, candidate.split())) + r"(?!\w)"
            matches.extend((m.start(), m.end(), value) for m in re.finditer(pattern, raw))
    matches.extend((m.start(), m.end(), 1) for m in re.finditer(r"(?<!\w)gurre(?:si(?:nde|nin)?|sinde)?(?!\w)", raw))
    english = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
               7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth",
               13: "thirteenth", 14: "fourteenth", 15: "fifteenth", 16: "sixteenth", 17: "seventeenth",
               18: "eighteenth", 19: "nineteenth", 20: "twentieth", 30: "thirtieth"}
    for value in range(1, 32):
        phrase = english.get(value) or ("twenty" if value < 30 else "thirty") + " " + english[value % 10]
        pattern = r"(?<!\w)" + r"[\s-]+".join(map(re.escape, phrase.split())) + r"(?!\w)"
        matches.extend((m.start(), m.end(), value) for m in re.finditer(pattern, raw))
    selected = []
    for begin, end, value in sorted(matches, key=lambda item: (-(item[1] - item[0]), item[0])):
        if any(begin < stop and end > start for start, stop in year_spans):
            continue
        if not any(begin < stop and end > start for start, stop, _ in selected):
            selected.append((begin, end, value))
    result = {value for _, _, value in selected}
    for begin, end, values in _number_spans(raw):
        if not any(begin < stop and end > start for start, stop in year_spans) and not any(begin < stop and end > start for start, stop, _ in selected):
            result.update(int(value) for value in values if value == int(value) and 1 <= value <= 31)
    return result
