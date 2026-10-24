# sicilahval technical note

Fatih Kansoy, 24 October 2026, version 0.1.3.

- [English PDF](sicilahval_en.pdf): *From personnel biographies to auditable data*.
- [Türkçe PDF](sicilahval_tr.pdf): *Memur biyografilerinden denetlenebilir veriye*.

These are two language editions of the same three-page note. They explain the problem, source-level design, reading rules, two real source examples, installation, use and limits. The sole scholarly reference is Gülden Sarıyıldız (2009), TDV İslâm Ansiklopedisi 37: 134-136; software and archival references are separate. Both title blocks include the author’s email and personal website.

## Build

A TeX Live installation with Source Serif Pro, Source Code Pro and the packages named in style/kansoy.sty, plus latexmk and Poppler, is required:

~~~sh
python3 docs/papers/build.py --render
~~~

This builds both PDFs, checks page counts, metadata, command hyphens, extracted Turkish text and LaTeX diagnostics, and writes verification.json. Review PNGs and TeX intermediates stay in the ignored build/ folder. Visual review is recorded in [REVIEW.md](REVIEW.md).

style/kansoy.sty is an article adaptation of Fatih Kansoy's kansoy-article.sty (10 October 2026), preserving its Source Serif/Source Code typography. It uses compact spacing and a short-note layout, omits the original project-specific bibliography configuration, and supports pdfLaTeX and the editor's XeTeX-based compiler. This is separate from Kansoy's Beamer presentation style. The original styles are unchanged. Identical copies in en/ and tr/ make both LaTeX editor projects self-contained; the build script synchronizes them.

The repository's [CITATION.cff](../../CITATION.cff) supplies the software citation. The note is attributed to Fatih Kansoy. No DOI or journal publication is claimed.
