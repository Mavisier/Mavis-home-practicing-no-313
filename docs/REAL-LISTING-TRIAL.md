# Gerçek ilanlarla yerel deneme — 13 Ekim 2026

Kullanıcı isteği doğrultusunda arabam.com'un herkese açık listesinde bulunan beş güncel ilan seçildi. Arama motorundaki eski örneklerden biri kategori sayfasına yönlendi; o kayıt canlı ilan gibi kullanılmadı.

Normal HTTP isteği erişim kontrolü döndürdüğünden sayfalar normal tarayıcı görünümünden kaydedildi. Giriş yapılmadı, CAPTCHA çözülmedi, özel API veya gizli hesap verisi kullanılmadı.

## Kaydedilen dosyalar

Her örnek `data/real_listings/<ilan_no>/` altında bulunur:

- `original.html`: tarayıcıdaki tam DOM HTML kopyası; son HTML etiketi ve kesilme durumu kontrol edildi.
- `capture.json`: kaynak URL, yakalama zamanı ve sayfada bulunan görsel adresleri.
- `images/`: toplam 122 fotoğraf; kaynak URL, dosya hash'i ve gerçek piksel boyutları ölçüldü.
- `normalized.json`: yalnızca araçla ilgili alanlar, açıklama, kaynak ve görsel metadata'sı.
- `offline.html`: fotoğrafları yerel dosyalardan açan okunabilir kopya. Satıcı markup'ı escape edilir; sayfa script çalıştırmaz.

Üst dizinde `index.html` ve `report.json` bulunur. Ham kopyalar ve üçüncü taraf fotoğrafları Git/Docker build kapsamı dışında bırakıldı. Bu dosyalar yerel test içindir; hiçbir ilan veya mesaj gerçek platforma gönderilmedi.

## Sonuçlar

| İlan | Fotoğraf | Mevcut kuralların bulduğu teyit başlıkları |
| --- | ---: | --- |
| 37570454 | 28 | Başlıkta 99.000 km, alanda 104.000 km; yapılandırılmış Tramer tutarı boş |
| 42746085 | 26 | Boya detayları ve Tramer tutarı belirtilmemiş |
| 43145023 | 30 | Mevcut kontrol kuralları bulgu üretmedi |
| 44742589 | 29 | Hasar tutarı açıklamada geçiyor, Tramer alanında belirtilmemiş |
| 44785121 | 9 | Yapılandırılmış Tramer tutarı belirtilmemiş |

Bunlar ilan beyanları üstündeki kontrollerdir. Başlığın eski kalması bir açıklama olabilir; km müdahalesi veya satıcının kötü niyeti sonucuna varılmaz. Bulgu çıkmaması da araç durumunun doğrulandığı anlamına gelmez.

Fotoğrafların hepsi sitedeki 580×435 önizleme varyantlarıdır. Bu boyut, satıcının yüklediği orijinal fotoğrafın kalitesini kanıtlamaz. Açı sınıflandırması yapılmadığından eksik ön/arka/iç/motor fotoğrafı sonucu üretilmedi. Fotoğraflardan hasar, plaka veya araç kimliği çıkarımı yapılmadı.

## Testin sağladığı iyileştirmeler

- Başlık ve kilometre alanı farklılıklarını teyit sorusuna dönüştürme.
- Açıklamadaki hasar tutarını, boş Tramer alanına doğrulanmış bilgi gibi otomatik yazmama.
- `Boyasız değil` ve `boyasız göçük düzeltme` ifadelerinde yanlış boya çelişkisini azaltma.
- Önizleme boyutunu ve sınıflandırılmamış fotoğraf açısını yanlış alarm olarak kullanmama.
- HTML kopyasını ve görselleri mevcut demo kimliğiyle sunma; ham orijinal dosyayı uygulama origin'inde çalıştırmama.

30 backend testi, lint, TypeScript ve production build geçti. Beş gerçek girdi mevcut fixture workflow ile işlendi; dışarıya veri gönderilmedi, canlı LLM veya vision doğrulaması yapılmadı. Ayrı dört sentetik değerlendirme vakası da geçti.

## Tekrar deneme

Yakalamalar ve görseller mevcutsa, backend ortamında:

```powershell
.\.venv\Scripts\python.exe -m scripts.import_real_listings --reuse-images
```

Bu komut dosya hash'lerini kontrol eder, normalizasyonu ve değerlendirmeyi yeniden çalıştırır; görselleri tekrar indirmez. Yeni bir siteden genel crawl yapılmaz. API anahtarı yapılandırılmış canlı model modunda bu komut çalışmaz; yerel gerçek-ilan denemesi fixture moduyla sınırlandırılmıştır.

Ekranda **İndirilen gerçek ilanlar** sekmesi, fotoğraf galerisi, kaynak bağlantısı ve **HTML kopyasını aç** bağlantısı bulunur. Kurgusal örnekler ayrı sekmede korunmuştur.
