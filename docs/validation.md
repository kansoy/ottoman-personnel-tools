# Validation / Doğrulama

Version 0.1.0, 24 October 2026. / Sürüm 0.1.0, 24 Ekim 2026.

**34 local tests passed.** They cover source hashes, text integrity, exact quotations, linked facts/events, declared coverage, dates, payments, CSV/SQLite equality, package installation and standalone skill execution. / **34 yerel test geçti.** Kaynak özeti, metin bütünlüğü, alıntılar, olgu/olay bağlantıları, kapsam, tarihler, ödemeler, CSV/SQLite eşitliği, paket kurulumu ve bağımsız beceri çalışması denetlendi.

| Input / Girdi | Checked scope / Denenen kapsam |
|---|---|
| TXT, Markdown | UTF-8 text and ordered lines / UTF-8 metin ve satır sırası |
| DOCX | Paragraphs, tables, notes, headers/footers, comments and revision warnings / Paragraflar, tablolar, notlar, üst/alt bilgiler, yorumlar ve değişiklik uyarıları |
| Text PDF / Metin PDF | Page/line locators; optional `pypdf`; empty-text pages flagged / Sayfa-satır konumu; isteğe bağlı `pypdf`; metinsiz sayfa uyarısı |
| HTML/HTM | Text, entities and table content; scripts not executed / Metin, karakter kodları ve tablo içeriği; betikler çalıştırılmaz |
| RTF | Common text, Unicode/code-page text and notes; limits reported / Yaygın metin, Unicode/karakter kodlaması ve notlar; sınırlar belirtilir |
| ODT | Text, tables and notes / Metin, tablolar ve notlar |

Scans/images need a checked visual transcription or OCR workflow available to the host. The package does not perform handwriting recognition. / Tarama ve görüntüler, ortamın sağlayabildiği denetlenmiş görsel çevriyazı veya OCR gerektirir. Paket el yazısı tanıma yapmaz.

## Real source checks / Gerçek kaynak denetimi

A fresh LLM reading followed the skill on two complete selected transcriptions. A second reading checked the results against the supplied text. No prior research CSV was used as the extraction input. / Beceri, seçilen iki tam çevriyazı üzerinde bağımsız bir LLM okumasıyla denendi. Sonuçlar ikinci okumada kaynak metinle karşılaştırıldı. Bilgi çıkarımında önceki araştırma CSV'si kullanılmadı.

| Record / Kayıt | Facts / Olgu | Events / Olay | Dates / Tarih | Payments / Ödeme |
|---|---:|---:|---:|---:|
| Manuk Filcancıyan / Mahmut Süreyya | 33 | 14 | 14 | 6 |
| Zenop Tangaryan | 38 | 21 | 25 | 10 |

All 28 source segments have coverage decisions. Both exports pass exact quotation/reference checks and CSV/SQLite cell comparisons. The real tests exposed a false rejection of inflected Turkish days such as “dördünde” and “gurresinde”; the parser and regression tests were corrected without changing direct source claims into inferences. / 28 kaynak parçasının tamamı için kapsam kararı vardır. Her iki çıktı alıntı/bağlantı ve CSV/SQLite hücre denetimlerinden geçti. Gerçek deneme, “dördünde” ve “gurresinde” gibi tarih biçimlerinin yanlış reddedildiğini gösterdi; kaynak ifadeleri çıkarım olarak yeniden etiketlenmeden okuyucu ve testler düzeltildi.

The wheel was installed outside the checkout without runtime dependencies. Both real examples also ran from the standalone skill using system Python. The skill format and citation metadata were validated separately. / Wheel, kaynak dizini dışında ve çalışma zamanı bağımlılığı olmadan kuruldu. Her iki gerçek örnek bağımsız beceriden sistem Python'u ile de çalıştı. Beceri biçimi ve atıf üstverisi ayrıca doğrulandı.

These checks do not measure general extraction accuracy or establish source truth. The examples are supplied transcriptions, not new inspections of archival facsimiles. Conflicting dates, contextual calendar readings and the Zenop birth-year disagreement remain explicit. / Bu denetimler genel bilgi çıkarım doğruluğunu ölçmez ve kaynak ifadelerini tarihsel gerçek olarak doğrulamaz. Örnekler sağlanan çevriyazılardır; özgün arşiv görüntüleri yeniden incelenmemiştir. Çelişen tarihler, bağlamsal takvim yorumları ve Zenop'un doğum yılı uyuşmazlığı açıkça korunur.
