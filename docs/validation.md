# Validation / Doğrulama

Version 0.1.6, 24 October 2026. / Sürüm 0.1.6, 24 Ekim 2026.

**43 local tests passed, with no skips.** They cover source hashes, text integrity, exact quotations, linked facts/events, declared coverage, dates, payments, temporal limits on the conversion example, CSV/SQLite equality, package installation and standalone skill execution. / **43 yerel test, atlanan test olmadan geçti.** Kaynak özeti, metin bütünlüğü, alıntılar, olgu/olay bağlantıları, kapsam, tarihler, ödemeler, ihtida örneğinin zamana bağlı sınırları, CSV/SQLite eşitliği, paket kurulumu ve bağımsız beceri çalışması denetlendi.

| Input / Girdi | Checked scope / Denenen kapsam |
|---|---|
| TXT, Markdown | UTF-8 text and ordered lines / UTF-8 metin ve satır sırası |
| DOCX | Paragraphs, tables, notes, headers/footers, comments and revision warnings / Paragraflar, tablolar, notlar, üst/alt bilgiler, yorumlar ve değişiklik uyarıları |
| Text PDF / Metin PDF | Page/line locators; optional `pypdf`; empty-text pages flagged / Sayfa-satır konumu; isteğe bağlı `pypdf`; metinsiz sayfa uyarısı |
| HTML/HTM | Text, entities and table content; scripts not executed / Metin, karakter kodları ve tablo içeriği; betikler çalıştırılmaz |
| RTF | Common text, Unicode/code-page text and notes; limits reported / Yaygın metin, Unicode/karakter kodlaması ve notlar; sınırlar belirtilir |
| ODT | Text, tables and notes / Metin, tablolar ve notlar |

Scans/images need a checked visual transcription or OCR workflow available to the host. The package does not perform handwriting recognition. / Tarama ve görüntüler, ortamın sağlayabildiği denetlenmiş görsel çevriyazı veya OCR gerektirir. Paket el yazısı tanıma yapmaz.

Full test runs use `python -m pip install ".[pdf,dev]"` before `python -m unittest discover -s tests -v`, from a repository checkout. Without the optional dependencies, the PDF and JSON Schema integration checks are skipped. / Tam test için deponun yerel kopyasında önce `python -m pip install ".[pdf,dev]"`, ardından test komutu çalıştırılır. İsteğe bağlı bağımlılıklar olmadan PDF ve JSON Schema denetimleri atlanır.

## Real source checks / Gerçek kaynak denetimi

A fresh LLM reading followed the skill on two complete selected transcriptions. A second reading checked the results against the supplied text. No prior research CSV was used as the extraction input. / Beceri, seçilen iki tam çevriyazı üzerinde bağımsız bir LLM okumasıyla denendi. Sonuçlar ikinci okumada kaynak metinle karşılaştırıldı. Bilgi çıkarımında önceki araştırma CSV'si kullanılmadı.

| Record / Kayıt | Facts / Olgu | Events / Olay | Dates / Tarih | Payments / Ödeme |
|---|---:|---:|---:|---:|
| Manuk Filcancıyan / Mahmut Süreyya | 33 | 14 | 14 | 6 |
| Zenop Tangaryan | 38 | 21 | 25 | 10 |

All 28 source segments have coverage decisions. Both exports pass exact quotation/reference checks and CSV/SQLite cell comparisons. The real tests exposed a false rejection of inflected Turkish days such as “dördünde” and “gurresinde”; the parser and regression tests were corrected without changing direct source claims into inferences. / 28 kaynak parçasının tamamı için kapsam kararı vardır. Her iki çıktı alıntı/bağlantı ve CSV/SQLite hücre denetimlerinden geçti. Gerçek deneme, “dördünde” ve “gurresinde” gibi tarih biçimlerinin yanlış reddedildiğini gösterdi; kaynak ifadeleri çıkarım olarak yeniden etiketlenmeden okuyucu ve testler düzeltildi.

The wheel was installed outside the checkout without runtime dependencies. Both real examples also ran from the standalone skill using system Python. The skill format and citation metadata were validated separately. / Wheel, kaynak dizini dışında ve çalışma zamanı bağımlılığı olmadan kuruldu. Her iki gerçek örnek bağımsız beceriden sistem Python'u ile de çalıştı. Beceri biçimi ve atıf üstverisi ayrıca doğrulandı.

These checks do not measure general extraction accuracy or establish source truth. The examples are supplied transcriptions, not new inspections of archival facsimiles. Conflicting dates, contextual calendar readings and the Zenop birth-year disagreement remain explicit. / Bu denetimler genel bilgi çıkarım doğruluğunu ölçmez ve kaynak ifadelerini tarihsel gerçek olarak doğrulamaz. Örnekler sağlanan çevriyazılardır; özgün arşiv görüntüleri yeniden incelenmemiştir. Çelişen tarihler, bağlamsal takvim yorumları ve Zenop'un doğum yılı uyuşmazlığı açıkça korunur.

## Version 0.1.3 corrections / Sürüm 0.1.3 düzeltmeleri

Regression cases now reject nonzero direct amounts attached to unpaid wording and partial numeric matches such as `150 kuruş` inside `1150 kuruş`, including decimal, sign and grouping boundaries. Written-year calendar labels, the source's `Hicriyesi'nde` form and English cardinal years containing “and” are checked correctly. Whole amounts and sentence punctuation remain accepted. The two real readings are unchanged. / Yeni regresyon durumları, ücretsiz hizmet ifadesine bağlanan sıfır dışı doğrudan tutarları ve `1150 kuruş` içindeki `150 kuruş` gibi kısmi eşleşmeleri reddeder; ondalık, işaret ve basamak ayırıcıları da denetlenir. Yazıyla verilen yıl ve takvim ifadeleri, kaynaktaki `Hicriyesi'nde` biçimi ve İngilizce “and” içeren yıl okumaları doğru işlenir. Tam tutarlar ve cümle noktalaması kabul edilir. İki gerçek kayıt okuması değişmemiştir.

The schema now defines Rumi numeric months as civil month labels, January/Kânunusani=1 through December/Kânunuevvel=12, with the native year unchanged. This is not March-based fiscal numbering or Gregorian conversion. / Şema artık Rumî ay numaralarını Kânunusani=1 ile Kânunuevvel=12 arasındaki ay adı kodları olarak tanımlar; özgün yıl değişmez. Bu, Mart ile başlayan malî ay sırası veya Miladî tarih dönüşümü değildir.

## Version 0.1.4 conversion review / Sürüm 0.1.4 ihtida kontrolü

The real Manuk reading already contained the conversion-to-Islam fact, Mahmut Süreyya name and paired dates. The example now also makes the subsequent religion/name explicit in event details, with prior religion left unknown. A regression checks that the event, linked facts, certainty and both native dates survive JSON, CSV and SQLite. Conversion expressions and subject/negation/attribution pitfalls are reading guidance for the host model; the Python helpers do not perform automatic religious classification. / Gerçek Manuk okumasında Müslüman oluş, Mahmut Süreyya adı ve iki tarih zaten vardı. Örnekte olay ayrıntıları da sonraki din ve adı açıkça belirtir; önceki din bilinmiyor olarak kalır. Regresyon testi olayın, bağlı olguların, kesinlik durumunun ve iki özgün tarihin JSON, CSV ve SQLite çıktılarında korunduğunu denetler. İhtida ifadeleri ile özne, olumsuzluk ve rivayet ayrımları modeli yönlendirir; Python yardımcıları otomatik din sınıflaması yapmaz.

## Version 0.1.5 temporal applicability / Sürüm 0.1.5 zamana bağlı uygulama

The Manuk example now links its subsequent religion and name to the existing day-precision date pair, without assigning them to earlier periods, the whole of AH 1306 or later periods by extrapolation. Its prior religion remains unspecified. A regression checks the date IDs, native values, precision and certainty in CSV and SQLite, preserves the event-level applicability details and verifies that no lifetime `is_muslim` classification is supplied. No annual panel or continuous status spell is generated. The source text and all pre-existing assertions, quotations and dates are unchanged; counts remain 33 facts, 14 events, 14 dates and six payment components. This test protects this example's representation, not the semantic accuracy of unseen extractions. / Manuk örneğinde sonraki din ve ad, gün kesinliğindeki mevcut iki tarihe bağlanır; önceki dönemlere, Hicrî 1306 yılının tamamına veya çıkarım yoluyla sonraki dönemlere atanmaz. Önceki din belirtilmemiş olarak kalır. Regresyon testi tarih kimliklerini, özgün değerleri, kesinliği ve kaynak/çıkarım ayrımını CSV ve SQLite içinde denetler; olayın zaman kapsamını korur ve hayatın tamamına uygulanan bir `is_muslim` sınıfı üretilmediğini kontrol eder. Kişi-yıl paneli veya kesintisiz durum dizisi oluşturulmaz. Kaynak metni ile önceden mevcut bütün ifadeler, alıntılar ve tarihler aynıdır; 33 olgu, 14 olay, 14 tarih ve altı ödeme bileşeni korunur. Bu test, örneğin gösterimini korur; henüz incelenmemiş çıkarımların anlamsal doğruluğunu kanıtlamaz.

## Version 0.1.6 dative day forms / Sürüm 0.1.6 yönelme ekli günler

Date checks now recognize Turkish dative day forms such as “yirmi beşine” (25) and “on sekizine” (18) as complete compounds, rather than reading only their tens prefixes. Regressions cover all 31 day spellings, joined spelling, “gurresine”, preservation of direct certainty and 60 incorrect-day rejections. A complete four-digit year attached to a named month, such as “Zilhicce1299”, is also recognized without accepting a truncated or incorrect year. No source assertions or dates were changed. / Tarih denetimi artık “yirmi beşine” (25) ve “on sekizine” (18) gibi yönelme ekli günleri yalnız onluk kısmıyla değil, bütün olarak okur. Regresyonlar 31 günün yazımını, bitişik yazımı, “gurresine” biçimini, doğrudan kaynak kesinliğinin korunmasını ve 60 yanlış günün reddini kapsar. “Zilhicce1299” gibi bir ay adına bitişik yazılmış dört basamaklı yıl da eksik veya yanlış bir yıl kabul edilmeden tanınır. Kaynak ifadeleri veya tarihler değiştirilmedi.
