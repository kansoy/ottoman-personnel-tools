# Real examples / Gerçek örnekler

Two complete biographies from an owner-supplied Latin-script transcription. The compiler is unverified; the original register images were not inspected for these examples. References below retain the transcription's exact wording. / Kullanıcının sağladığı Latin harfli metinden iki tam biyografi. Derleyici doğrulanmamıştır; bu örnekler için defter görüntüleri incelenmemiştir. Aşağıdaki künyeler metindeki biçimiyle korunur.

| Example / Örnek | What to check / Kontrol noktası |
|---|---|
| [Manuk Filcancıyan → Mahmut Süreyya](manuk/source.txt) · [facts CSV](manuk/data/facts.csv) · [payments CSV](manuk/data/payments.csv) | English annotations. School entry differs from employment; the 75-kuruş increment and resulting 675-kuruş salary remain distinct. Name/religion change and conflicting paired death dates are preserved. / Okula giriş ve memuriyet ayrılır; 75 kuruş zam ile 675 kuruş maaş ayrı tutulur. Ad/din değişimi ve uyuşmayan ölüm tarihleri korunur. `DH_SAİD_8_86; 167`. |
| [Zenop Tangaryan](zenop/source.txt) · [facts CSV](zenop/data/facts.csv) · [payments CSV](zenop/data/payments.csv) | Türkçe açıklamalar. Başlıktaki 1273 ile doğum cümlesindeki 1270 birlikte tutulur. Maaş değişimleri, yerel takvimler, madalya ve görev gereği yargılanmadığına dair sınırlı beyan korunur. / Conflicting birth statements, salary changes, native calendars, medal and the limited statement about official-duty proceedings remain visible. `DH_SAİD_5_356; 709`. |

Each folder includes the complete source excerpt, prepared segments, structured reading, validation report, CSV relations and SQLite. / Her klasör tam biyografi metnini, kaynak parçalarını, yapılandırılmış okumayı, kontrol raporunu, CSV tablolarını ve SQLite dosyasını içerir.

Manuk's [conversion event](manuk/data/events.csv) records Islam and the new name Mahmut Süreyya on 4 Rebiülevvel AH 1306, paired with 28 Teşrinievvel 1304 (contextually read as Rumi). The previous religion is unspecified in the supplied passage. These are dated changes, not a lifetime religious classification. / Manuk'un [ihtida olayı](manuk/data/events.csv), 4 Rebiülevvel 1306'da Müslüman oluşunu ve Mahmut Süreyya adını alışını kaydeder; yanında 28 Teşrinievvel 1304 tarihi korunur ve takvimi bağlamdan Rumî olarak okunur. Verilen pasajda önceki din belirtilmez. Bu, hayatının tamamına uygulanan bir din sınıfı değil, tarihli bir değişikliktir.

Reproduce in a new directory / Yeni klasörde yeniden üretin:

```sh
sicilahval demo --out demo-en --language en
sicilahval demo --out demo-tr --language tr
```

The commands export reviewed cached readings; they make no new model call. A new document requires a fresh reading by the host model or a human. / Komutlar önceden okunup kontrol edilmiş kayıtları dışa aktarır; yeni model çağrısı yapmaz. Yeni belgeyi ev sahibi modelin veya insanın yeniden okuması gerekir.
