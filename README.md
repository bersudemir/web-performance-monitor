# Web Performans İzleme Sistemi

Python/FastAPI üzerinde, Jinja2, Bootstrap 5 ve Chart.js ile hazırlanmış Türkçe arayüz önizlemesi.

## Çalıştırma

Python 3.12 önerilir. Proje kökünde PowerShell ile:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Mevcut `.venv` ortamınız varsa ilk adımı atlayın. Linux/macOS üzerinde `python3 -m venv .venv` ve `.venv/bin/python` kullanabilirsiniz.

Tarayıcıda **http://127.0.0.1:8000/dashboard** adresini açın.

| Adres | İçerik |
| --- | --- |
| `/dashboard` | Toplam, çalışan ve çalışmayan site sayıları; son kontroller |
| `/sites` | Site listesi, durum, HTTP kodu, yanıt süresi ve detay bağlantıları |
| `/sites/new` | Site adı, HTTP/HTTPS URL ve kontrol aralığı; yalnızca form önizlemesi |
| `/sites/1` … `/sites/4` | Son durum, uptime, ortalama yanıt süresi, geçmiş ve Chart.js grafiği |
| `/` | Mevcut JSON karşılama yanıtı |
| `/health` | Mevcut JSON sağlık kontrolü |
| `/docs` | FastAPI API dokümantasyonu |

## Demo kapsamı

**Dört ekranın tamamı henüz gerçek backend'e bağlı değildir.** Tüm ekranlarda “Örnek veri” uyarısı vardır. Dört örnek site ve site başına 12 sabit kontrol, `app/presentation/demo.py` dosyasından gelir. Tarihler 27.11.2026 tarihli sabit Türkiye saati örnekleridir; güncel ölçüm değildir.

Uptime, gösterilen 12 kayıttaki başarılı kontrollerin oranıdır; ortalama yanıt süresi aynı kayıtların aritmetik ortalamasıdır. Demo başarı ölçütü HTTP 200'dür. Grafik aynı geçmişi eskiden yeniye gösterir. DOWN örneğinde HTTP 503 kullanılmıştır.

Site ekleme formu tarayıcı doğrulamasıyla bilgileri yalnızca sayfada önizler. Veriler sunucuya gönderilmez, veritabanına veya tarayıcı depolamasına kaydedilmez, site listesine eklenmez. Girilen URL'ye istek gönderilmez ve kontrol aralığı bir görev başlatmaz. JavaScript kapalıysa önizleme düğmesi devre dışıdır.

PostgreSQL, Docker, AWS, worker veya gerçek HTTP kontrol sistemi eklenmemiştir. `domain`, `application` ve `infrastructure` katmanları değiştirilmemiştir.

Bootstrap 5.3.3 CSS ve Chart.js 4.4.8 sabit sürümleri CDN'den yüklenir; tam görsel görünüm ve grafik için internet erişimi gerekir. Chart.js yüklenemezse açıklama gösterilir ve geçmiş tablosu kullanılabilir. Özel CSS/JS yerel `static` dizinindedir.

## Dosyalar

- `app/main.py`: mevcut endpointler korunarak statik dosyalar ve sayfa router'ı bağlanır.
- `app/presentation/pages.py`: yalnızca HTML sayfa route'ları.
- `app/presentation/demo.py`: sunum katmanına özel örnek veri.
- `app/presentation/templates/`: ortak yerleşim, tablo bileşenleri ve dört ekran.
- `app/presentation/static/css/app.css`: açık renkli, responsive görünüm.
- `app/presentation/static/js/`: form önizlemesi ve yanıt süresi grafiği.
- `requirements.txt`: mevcut bağımlılıklara Jinja2 ve testler için httpx eklenmiştir; dosya UTF-8 biçimindedir.
- `tests/test_pages.py`: endpoint, şablon, grafik verisi ve demo kapsamı kontrolleri.

## Test

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Testler uygulamayı TestClient ile çalıştırır; dış sitelere istek veya veritabanı bağlantısı yapmaz. Tarayıcıda mobil görünümü, gezinme bağlantılarını, `/sites/3` DOWN örneğini ve `/sites/new` form önizlemesini de deneyebilirsiniz.
