# sicilahval

**Fatih Kansoy** · [English](README.md) · [Türkçe yöntem notu](docs/papers/sicilahval_tr.pdf) · [English paper](docs/papers/sicilahval_en.pdf)

Tam Sicill-i Ahvâl biyografilerini kaynak alıntılarıyla bağlantılı **CSV, JSON ve SQLite** dosyalarına dönüştüren Python paketi ve LLM becerisi. Kişi/aile bilgilerini, eğitimi, dilleri, görevleri, özgün tarihleri, ödeme bileşenlerini, hukuki ifadeleri, düzeltmeleri ve diğer ayrıntıları kaydeder.

Metni LLM okur ve yapılandırır. Python metni hazırlar, alıntıları ve bağlantıları denetler, tabloları dışa aktarır. Beceri mevcut asistanınızda kullanıldığında ayrıca API anahtarı gerekmez.

## Kurulum

Python 3.10 veya üzeri:

```sh
python -m pip install "sicilahval @ git+https://github.com/kansoy/ottoman-personnel-tools.git@v0.1.0"
sicilahval install-skill --target codex --scope user
# Veya: sicilahval install-skill --target claude --scope user
```

`--scope project` mevcut projeye, `--target agents` ortak Agent Skills dizinine kurar. `--path` ile farklı üst dizin seçilebilir. [Bağımsız beceri](skills/sicilahval) Python yardımcılarını içerir; yüklenebilir ZIP [sürüm sayfasındadır](https://github.com/kansoy/ottoman-personnel-tools/releases/tag/v0.1.0). Dosya erişimi ve Python çalıştırma gerekir; beceri tanıma desteği istemciye göre değişir.

## Kullanım

Codex'te:

> $sicilahval ile bu belgedeki bütün tam biyografileri ve eklerini çıkar. Her ayrıntıyı ve belirsizliği koru. CSV ve SQLite dosyaları ile Türkçe kontrol özeti hazırla.

Claude Code'da aynı isteği `/sicilahval` ile verin. Özet ve yorumlar Türkçe veya İngilizce olabilir. Kaynak alıntıları, kişi ve yer adları özgün yazımıyla korunur; alan adları değişmez.

```sh
sicilahval prepare kayitlar.docx --out calisma --language tr
# LLM metni okuyarak calisma/records.json dosyasını oluşturur.
sicilahval validate calisma/records.json --source calisma/source.json
sicilahval export calisma/records.json --source calisma/source.json --out veri
```

TXT, Markdown, DOCX, metin PDF, HTML, RTF ve ODT desteklenir. Metin PDF için `pypdf` gerekir; diğer okuyucular Python standart kütüphanesini kullanır. Tarama ve görüntüler için beceri, mevcut çevriyazı/OCR araçlarını kullanır ve kontrol sınırlarını kaydeder. [Denenen biçimler](docs/validation.md).

## Örnekler ve denetimler

```sh
sicilahval demo --out example-output --language tr
python -m unittest discover -s tests -v
```

[İki gerçek kayıt](examples/sicilahval), Manuk Filcancıyan’ın eğitimini, atamalarını, maaş değişikliklerini ve sonraki ad/din değişikliğini; Zenop Tangaryan’ın kariyerini ve çelişen doğum yılı ifadelerini gösterir. Kullanılan çevriyazı ve özgün arşiv künyeleri okumalara eklenmiştir. Yapılan denetimler [doğrulama notunda](docs/validation.md) açıklanır.

Kayıtlar, olgular, olaylar, tarihler, ödemeler, alıntılar, kapsam denetimi ve kaynak parçaları bağlantılı tablolarda saklanır. Bilinmeyen değer sıfırdan; kaynak ifadesi çıkarımdan ayrılır. Araştırma sınıflandırmaları, sayısal yer/görev kodları, kimlik birleştirmesi ve kişi-yıl panelleri ayrı işlemlerdir.

Mekanik doğrulama tarihsel doğruluğu veya bütün anlam ayrıntılarının çıkarıldığını kanıtlamaz. Güç okumaları kaynak üzerinden denetleyin. [Okuma kuralları](src/sicilahval/skill/references/workflow.md) · [Şema](src/sicilahval/schema.json).

## Atıf

Kansoy, Fatih. 2026. *sicilahval: Evidence-linked extraction of Ottoman personnel records*. Sürüm 0.1.0. https://github.com/kansoy/ottoman-personnel-tools.

[CITATION.cff](CITATION.cff) · [BibTeX](docs/citation.bib) · [Türkçe yöntem notu](docs/papers/sicilahval_tr.pdf) · [English methods note](docs/papers/sicilahval_en.pdf)

Kullanılan yayına ve arşiv belgelerine ayrıca atıf verin. Yazılım Apache-2.0 lisanslıdır; özel [Ottoman Bureaucracy](https://ottomanbureaucracy.com) veri seti bu depoda dağıtılmaz; yalnızca seçilen iki çevriyazı örneği paylaşılır. Önceki `personnel_evidence` modülü korunmuştur: [köken bilgisi](SOURCE_ATTRIBUTION.md).
