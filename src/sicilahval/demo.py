"""Reviewed real demonstrations and invented internal regression fixtures."""
from __future__ import annotations

from pathlib import Path

from .export import export_records
from .intake import prepare_source
from .util import new_directory, read_json, write_json
from .validation import validate_records

TEXTS = {
    "appointment": """SENTETİK ÖRNEK — Arşiv kaydı değildir; bütün kişiler ve olaylar uydurulmuştur.
Antranik Efendi, kuyumcu Kirkor'un oğludur. Hicrî 1265'te Erzurum'da doğmuştur; Ermeni milletindendir.
Erzurum Rüşdiye Mektebini bitirmiştir. Türkçe okuyup yazar, Fransızca konuşur ve Farsça okur.
Hicrî 1285'te Erzurum Vilayeti Tahrirat Kalemine aylık 150 kuruş maaşla kâtip tayin edilmiştir.
Hicrî 1286'da aynı görevde maaşına aylık 25 kuruş zam yapılmıştır.
Aynı Hicrî 1286 yılında mevcut görevi yanında Erzurum Rüşdiyesinde muallimlik yapmış; ders başına 10 kuruş ücret almıştır.
Hicrî 1290'da üçüncü rütbeden Mecidî nişanı verilmiştir.
Hicrî 1292'de sağlık sebebiyle emekliye ayrılmış ve aylık 90 kuruş emekli maaşı bağlanmıştır.
Hicrî 1293'te Erzurum'da vefat etmiştir.
""",
    "pay_legal": """SENTETİK ÖRNEK — Arşiv kaydı değildir; bütün kişiler ve olaylar uydurulmuştur.
Rafael Efendi, tüccar Yusuf'un oğludur. İlk beyanda Hicrî 1268'de İstanbul'da doğduğu yazılıdır.
Musevi cemaatine mensuptur. Mahallî Musevi mektebinde okumuş; Türkçe okuyup yazdığını, Yahudi İspanyolcası konuştuğunu bildirmiştir.
Hicrî 1290'da Maliye Nezareti Muhasebe Kalemine mülâzım olarak girmiştir; bu devrenin maaşı belirtilmemiştir.
Hicrî 1291'de aynı kalemde bilâ maaş çalıştığı açıkça kaydedilmiştir.
Hicrî 1292'de aylık 200 kuruşla aynı kalemin kâtipliğine tayin edilmiştir.
Rumi 1291'de bu görevi sürerken İstanbul'daki bir mahkemede geçici tercümanlık yapmış ve bir defaya mahsus 15 lira ücret almıştır.
Tarihi belirtilmeyen bir tahkikatta zimmet iddiasıyla sorgulanmış; yargılama sonunda beraat ettiği bildirilmiştir. Mahkûmiyet kaydı yoktur ifadesi kullanılmamıştır.
Sonradan eklenen tashihte doğum yılının Hicrî 1268 değil, Hicrî 1269 olduğu yazılıdır.
Defter: DH.SAİDd 999, varak 12b. Bu arşiv künyesi de sentetiktir.
"""
}


def build_example(name: str, source: dict, language: str = "en") -> dict:
    if name not in TEXTS:
        raise ValueError("Unknown example")
    segments = source["segments"]
    lookup = {index: {"segment_id": segment["segment_id"], "quote": segment["text"]}
              for index, segment in enumerate(segments, 1)}
    facts: list[dict] = []
    events: list[dict] = []

    def say(en: str, tr: str) -> str:
        return tr if language == "tr" else en

    def citations(*lines: int) -> list[dict]:
        return [dict(lookup[line]) for line in lines]

    def date(key: str, raw: str, year: int | None, line: int, calendar: str = "hijri",
             certainty: str = "direct", note: str = "", **extra) -> dict:
        return {"date_id": key, "raw": raw, "calendar": calendar, "year": year, "month": None, "day": None,
                "precision": "year" if year is not None else "unknown", "certainty": certainty,
                "evidence": citations(line), "note": note, **extra}

    def fact(key: str, category: str, field: str, raw: str, value, line: int, **extra) -> str:
        facts.append({"fact_id": key, "category": category, "key": field, "value_raw": raw, "value": value,
                      "certainty": "direct", "evidence": citations(line), "note": "", **extra})
        return key

    def payment(key: str, component: str, raw: str, amount, currency: str, period: str, line: int,
                role: str = "level", certainty: str = "direct", note: str = "", evidence_lines=None, **extra) -> dict:
        return {"payment_id": key, "component": component, "amount_raw": raw, "amount": amount,
                "currency_raw": currency, "period_raw": period, "amount_role": role,
                "certainty": certainty, "evidence": citations(*(evidence_lines or [line])), "note": note, **extra}

    def event(key: str, kind: str, line: int, *, dates=None, payments=None, fact_ids=None, **extra) -> None:
        events.append({"event_id": key, "event_type": kind, "description_raw": lookup[line]["quote"],
            "fact_ids": fact_ids or [], "dates": dates or [], "payments": payments or [],
            "certainty": "direct", "evidence": citations(line), "note": "", **extra})

    if name == "appointment":
        person_name = "Antranik Efendi"
        fact("f01", "identity", "name", person_name, person_name, 2)
        fact("f02", "family", "father_name", "Kirkor", "Kirkor", 2)
        fact("f03", "family", "father_occupation", "kuyumcu", say("goldsmith", "kuyumcu"), 2)
        fact("f04", "birth", "birthplace", "Erzurum", "Erzurum", 2)
        fact("f05", "community", "community", "Ermeni milletindendir", say("Armenian community", "Ermeni milleti"), 2)
        fact("f06", "birth", "birth_year", "Hicrî 1265", 1265, 2, dates=[date("d01", "Hicrî 1265", 1265, 2)])
        fact("f07", "education", "school_completed", "Erzurum Rüşdiye Mektebini bitirmiştir", "Erzurum Rüşdiye Mektebi", 3)
        fact("f08", "language", "Turkish", "Türkçe okuyup yazar", {"reading": True, "writing": True}, 3)
        fact("f09", "language", "French", "Fransızca konuşur", {"speaking": True}, 3)
        fact("f10", "language", "Persian", "Farsça okur", {"reading": True}, 3)
        job = fact("f11", "employment", "appointment", "Erzurum Vilayeti Tahrirat Kalemine", {
            "place_raw": "Erzurum", "institution_raw": "Erzurum Vilayeti Tahrirat Kalemi", "title_raw": "kâtip"}, 4)
        event("e01", "appointment", 4, dates=[date("d02", "Hicrî 1285", 1285, 4)],
            payments=[payment("p01", "salary", "150", 150, "kuruş", "aylık", 4)], fact_ids=[job])
        event("e02", "pay_change", 5, dates=[date("d03", "Hicrî 1286", 1286, 5)], fact_ids=[job], payments=[
            payment("p02", "salary", "25", 25, "kuruş", "aylık", 5, role="increment"),
            payment("p03", "salary", "150 + 25", 175, "kuruş", "aylık", 5, certainty="inferred", evidence_lines=[4, 5],
                note=say("150 + 25 = 175; preferred resulting monthly level, inferred from the same post. The source states the increment, not this total.",
                         "150 + 25 = 175; aynı görevdeki artıştan çıkarılan aylık seviye. Kaynak toplamı değil, zam miktarını belirtir."),
                alternatives=[{"amount": None, "reason": say("Keep only the explicitly stated increment.", "Yalnız açıkça belirtilen zam tutarını kullan.")}])])
        teaching = fact("f12", "employment", "concurrent_post", "Erzurum Rüşdiyesinde muallimlik", {
            "place_raw": "Erzurum", "institution_raw": "Erzurum Rüşdiyesi", "title_raw": "muallim", "relation": "concurrent"}, 6)
        event("e03", "concurrent_appointment", 6, dates=[date("d04", "Hicrî 1286", 1286, 6)], fact_ids=[teaching],
              payments=[payment("p04", "teaching_fee", "10", 10, "kuruş", "ders başına", 6, role="fee")])
        fact("f13", "honour", "decoration", "üçüncü rütbeden Mecidî nişanı", {"name_raw": "Mecidî nişanı", "grade_raw": "üçüncü"}, 7)
        event("e04", "honour", 7, dates=[date("d05", "Hicrî 1290", 1290, 7)], fact_ids=["f13"])
        fact("f14", "retirement", "reason", "sağlık sebebiyle", say("health", "sağlık"), 8)
        event("e05", "retirement", 8, dates=[date("d06", "Hicrî 1292", 1292, 8)], fact_ids=["f14"],
            payments=[payment("p05", "pension", "90", 90, "kuruş", "aylık", 8)])
        fact("f15", "death", "deathplace", "Erzurum'da vefat", "Erzurum", 9)
        event("e06", "death", 9, dates=[date("d07", "Hicrî 1293", 1293, 9)], fact_ids=["f15"])
    else:
        person_name = "Rafael Efendi"
        fact("f01", "identity", "name", person_name, person_name, 2)
        fact("f02", "family", "father_name", "Yusuf", "Yusuf", 2)
        fact("f03", "family", "father_occupation", "tüccar", say("merchant", "tüccar"), 2)
        fact("f04", "birth", "birthplace", "İstanbul", "İstanbul", 2)
        fact("f05", "birth", "initial_birth_year", "Hicrî 1268", 1268, 2,
            dates=[date("d01", "Hicrî 1268", 1268, 2, role="superseded_statement")],
            note=say("Initial statement, explicitly superseded by the later correction; retained verbatim.",
                     "Sonraki açık tashihle değiştirilen ilk beyan; aynen korunmuştur."),
            details={"status": "superseded", "superseded_by_fact_id": "f13"})
        fact("f06", "community", "community", "Musevi cemaatine mensuptur", say("Jewish community", "Musevi cemaati"), 3)
        fact("f07", "education", "school_attended", "Mahallî Musevi mektebinde okumuş", "Mahallî Musevi mektebi", 3)
        fact("f08", "language", "Turkish", "Türkçe okuyup yazdığını", {"reading": True, "writing": True}, 3)
        fact("f09", "language", "Judeo-Spanish", "Yahudi İspanyolcası konuştuğunu", {"speaking": True}, 3)
        job = fact("f10", "employment", "internship", "Maliye Nezareti Muhasebe Kalemine mülâzım", {
            "institution_raw": "Maliye Nezareti Muhasebe Kalemi", "title_raw": "mülâzım"}, 4)
        event("e01", "internship_entry", 4, dates=[date("d02", "Hicrî 1290", 1290, 4)], fact_ids=[job],
            payments=[payment("p01", "salary", "maaşı belirtilmemiştir", None, "", "", 4,
                note=say("Unknown pay; the title mülâzım alone does not establish zero.", "Maaş bilinmiyor; mülâzım unvanı tek başına sıfır maaş göstermez."))])
        event("e02", "unpaid_service", 5, dates=[date("d03", "Hicrî 1291", 1291, 5)], fact_ids=[job],
              payments=[payment("p02", "salary", "bilâ maaş", 0, "", "", 5)])
        clerk = fact("f11", "employment", "appointment", "aynı kalemin kâtipliğine", {
            "institution_raw": "Maliye Nezareti Muhasebe Kalemi", "title_raw": "kâtip"}, 6,
            certainty="inferred", evidence=citations(4, 6),
            note=say("The institution is resolved from 'the same office' and the earlier named office.",
                     "Kurum, 'aynı kalem' ifadesi ile önceki açık kurum adından tamamlanmıştır."))
        event("e03", "appointment", 6, dates=[date("d04", "Hicrî 1292", 1292, 6)], fact_ids=[clerk],
              payments=[payment("p03", "salary", "200", 200, "kuruş", "aylık", 6)])
        translation = fact("f12", "employment", "concurrent_temporary_post", "İstanbul'daki bir mahkemede geçici tercümanlık", {
            "place_raw": "İstanbul", "institution_raw": "bir mahkeme", "title_raw": "tercüman", "relation": "concurrent", "temporary": True}, 7)
        event("e04", "concurrent_appointment", 7, dates=[date("d05", "Rumi 1291", 1291, 7, calendar="rumi")],
            fact_ids=[translation], payments=[payment("p04", "translation_fee", "15", 15, "lira", "bir defaya mahsus", 7, role="fee")])
        legal = fact("f14", "legal_history", "proceeding_and_outcome", "zimmet iddiasıyla sorgulanmış; yargılama sonunda beraat", {
            "allegation_raw": "zimmet", "proceeding_raw": "tahkikat; yargılama", "outcome_raw": "beraat"}, 8,
            note=say("An allegation and acquittal are distinct; no guilt or absence-of-all-records indicator is inferred.",
                     "İddia ile beraat ayrı tutulur; suçluluk veya hiç kayıt bulunmadığı sonucu çıkarılmaz."))
        event("e05", "legal_proceeding", 8, dates=[date("d06", "Tarihi belirtilmeyen", None, 8, calendar="unknown")],
              fact_ids=[legal], details={"outcome_raw": "beraat", "guilt_inferred": False})
        fact("f15", "legal_history", "qualification_on_absence", "Mahkûmiyet kaydı yoktur ifadesi kullanılmamıştır", None, 8,
            note=say("The text does not certify absence of convictions; null is not a negative record.",
                     "Metin mahkûmiyet bulunmadığını doğrulamaz; boş değer olumsuz kayıt değildir."))
        fact("f13", "birth", "corrected_birth_year", "Hicrî 1268 değil, Hicrî 1269", 1269, 9,
            dates=[date("d07", "Hicrî 1269", 1269, 9, role="corrected_birth")],
            details={"status": "preferred_explicit_correction", "supersedes_fact_id": "f05"})
        event("e06", "source_correction", 9, fact_ids=["f05", "f13"],
            note=say("The correction is explicit; its own date is not supplied.", "Tashih açıktır; tashihin tarihi verilmemiştir."))
        fact("f16", "archive_reference", "citation_raw", "DH.SAİDd 999, varak 12b", "DH.SAİDd 999, varak 12b", 10,
            note=say("Invented reference for illustration; do not cite as an archival record.", "Örnek için uydurulmuş künye; arşiv kaydı olarak atıf yapmayın."))
    items = []
    for f in facts:
        items.append((f["fact_id"], f))
        items.extend((d["date_id"], d) for d in f.get("dates", []))
    for e in events:
        items.append((e["event_id"], e))
        items.extend((d["date_id"], d) for d in e["dates"])
        items.extend((p["payment_id"], p) for p in e["payments"])
    coverage = [{"segment_id": s["segment_id"], "status": "extracted", "item_ids": [iid for iid, obj in items
        if any(c["segment_id"] == s["segment_id"] for c in obj["evidence"])], "note": ""} for s in segments[1:]]
    return {"schema_version": "1.0", "source_id": source["source_id"], "language": language,
        "records": [{"record_id": "r0001", "name_raw": person_name,
            "segment_ids": [s["segment_id"] for s in segments[1:]], "boundary_status": "reviewed",
            "facts": facts, "events": events, "coverage": coverage,
            "notes": [say("Synthetic teaching example; no historical claim.", "Sentetik öğretim örneği; tarihsel iddia içermez.")]}],
        "excluded_segments": [{"segment_id": segments[0]["segment_id"],
            "reason": say("Synthetic-example notice, not part of the biography.", "Sentetik örnek açıklaması; biyografinin parçası değildir.")}]}


def write_demo(out: str | Path, language: str = "en", example: str | None = None, *, synthetic: bool = False) -> dict:
    if language not in ("en", "tr"):
        raise ValueError("language must be en or tr")
    if not synthetic:
        name = example or ("manuk" if language == "en" else "zenop")
        resource = Path(__file__).with_name("examples") / name
        if not all((resource / f).is_file() for f in ("source.txt", "source.json", "records.json")):
            raise ValueError("Reviewed real example is unavailable in this installation: " + name)
        source, records = read_json(resource / "source.json"), read_json(resource / "records.json")
        if records["language"] != language:
            raise ValueError(f"This cached example has {records['language']} annotations; select that language or request a fresh reading from the host model.")
        report = validate_records(records, source, original=resource / "source.txt")
        if not report["valid"]:
            raise ValueError("Cached real example failed validation: " + "; ".join(report["errors"][:8]))
        target = new_directory(out)
        input_path = target / "source.txt"
        input_path.write_bytes((resource / "source.txt").read_bytes())
        work = target / "work"
        work.mkdir()
        write_json(work / "source.json", source)
        write_json(work / "records.json", records)
        summary = export_records(records, source, target / "data")
        summary.update(example=name, language=language, synthetic=False,
            basis="Reviewed cached reading of a real source transcription; no new model extraction is performed.")
        return summary
    name = example or ("appointment" if language == "en" else "pay_legal")
    if name not in TEXTS:
        raise ValueError("Synthetic example must be appointment or pay_legal")
    target = new_directory(out)
    input_path = target / f"{name}.txt"
    input_path.write_text(TEXTS[name], encoding="utf-8")
    prepare_source(input_path, target / "work", language, title="Synthetic Sicilahval example",
                   author="Fatih Kansoy", citation="Invented teaching material, not an archival record")
    source = read_json(target / "work/source.json")
    records = build_example(name, source, language)
    write_json(target / "work/records.json", records)
    summary = export_records(records, source, target / "data")
    summary.update(example=name, language=language, synthetic=True)
    return summary
