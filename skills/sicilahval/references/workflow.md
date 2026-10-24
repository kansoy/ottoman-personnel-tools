# Reading Sicill-i Ahvâl records

## Source and boundaries

Distinguish a Latin-script transcription, modern narrative, text PDF and original Ottoman image. A prepared text file is not an OCR-verified facsimile. If a PDF has no usable text, or the input is an image, use available host vision/OCR tools to create a checked transcript. Keep the original file hash and page/image references alongside it; preserve uncertain characters rather than complete them by guesswork. Run `prepare` on the transcript and disclose that quotation checks apply to the transcript. If the host cannot inspect images, a checked transcription is needed. Do not claim that the Python package reads handwriting.

Keep the supplied file hash, source citation and exact archival reference. A thesis page number and an archival register/folio are different references. Do not invent either. Record headings, continuation paragraphs, marginal/additional entries, corrections and footnotes in their source order. Attach each note to its related record. Shared notes may require explicit attribution to several records.

Each record is a source appearance, not an automatically resolved historical person. Preserve ambiguous joint biographies, repeated copies and cross-references with a reason. A name match or a locality heading is insufficient to merge records.

## Details to retain

Use one fact per distinct assertion where practical, with open-ended keys and structured details for relationships:

- Names and changes of name; parents, relatives, family descriptions and occupations.
- Birth date/place, with each administrative level separately named when present.
- Schools, subjects, attendance, completion, diplomas and examinations. Enrollment is not employment. Literal attendance years are not a standardized schooling score.
- Each language and the actual competence claimed: studied, understands, speaks, reads or writes. A speaking claim does not establish inability to write.
- Nationality, community and religion only as stated, or as an explicitly marked inference. An Armenian school, surname or document title does not prove denomination. A dated conversion is not a lifetime category.
- Office, institution, jurisdiction, rank, acting/deputy status, concurrent duties, appointments not taken up, transfers, absences and exits. Preserve titles rather than replace them with a research classification.
- Salary, increments, reductions, allowances, fees, arrears, deductions, pensions, lump sums and currency/period. Keep their event associations.
- Training/mülazemet, service interruptions, honours, medals, publications, legal inquiries and outcomes, health, retirement and death.
- Other source details as facts even if their analytical use is not yet known.

## Dates and chronology

Keep every native expression, calendar and precision. AH/Hijri, Rumi/mali, Julian and Gregorian years are not interchangeable. Civil month names such as Şubat and Teşrinievvel require calendar attention; a heading alone may not establish a calendar. A paired AH/Rumi date belongs to one event, not two appointments or two payments.

Follow the numeric month-label convention in [schema.md](schema.md): Rumi Kânunusani=1 and Mart=3, while the native year remains unchanged. This representation is not a calendar conversion or March-based fiscal month numbering.

Attach dates to the claim they qualify: appointment, salary change, birth correction, later certification or report. A report date is not automatically the event date. Relative dates and abbreviated years can be interpreted only from their actual antecedent; state the inference and preserve alternatives.

Retain conflicting age and birth/entry claims. AH year subtraction is not exact attained age. A one-year difference may involve ordinal counting; a later birth correction may leave an older narrative age unchanged. Never repair a number solely to force arithmetic agreement.

Do not carry an office or salary through unexplained gaps. This tool stores source assertions and events; constructing annual spells or person-year rows is a separate task.

## Payments and first work

Keep the recorded amount and its role. “A fifty-kuruş increase” is an increment, not a fifty-kuruş salary. A salary level and an allowance are separate components unless the source explicitly gives a combined total. Daily or foreign-currency amounts stay in their native unit; no silent monthly conversion or exchange rate.

Unknown amount is `null`; explicit zero is numeric `0`. Mülazemet can support a training interpretation without proving zero pay. If contextual evidence supports unpaid entry before a later first stipend, record it as an inference with a reason and a blank/unknown alternative. Never propagate an inferred first wage into every later salary.

Preserve school enrollment, first actual work, first public appointment and first paid appointment as distinct events where the source distinguishes them. Do not force them into one “first job” definition.

## Legal claims and corrections

An inquiry, accusation, suspension, prosecution, acquittal and conviction are different assertions. Record the source's wording, authority, date and outcome where available. “No prosecution up to this statement” is a bounded assertion, not lifetime innocence. A father's or colleague's proceeding is not the official's criminal history.

For later corrections, retain the earlier assertion, the correction, its basis and timing. If a preferred reading is selected, label it and retain the competing values. The model must not hide disagreement by replacing the source quotation.

## Review and coverage

Check all biographies and additions. For each segment, link the extracted items or give a specific nonbiographical/unresolved reason. A segment containing several details may need many linked facts; marking it “extracted” does not prove complete reading. Review numbers/dates/pay changes and the longest records independently when possible.

Use separate reviewers for boundaries, extraction and difficult interpretations when available; otherwise perform a distinct second reading. Review against the source, not only a prior generated CSV. Do not describe model agreement, schema validity or a populated cell as historical verification.

Summarize uncertain names, places, dates, payments and identities for human review. The source text and unclassified details remain available even when the structured reading is incomplete.
