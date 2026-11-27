# Web Performans İzleme Sistemi

FastAPI, Jinja2, Bootstrap 5 ve Chart.js ile hazırlanmış Türkçe web arayüzü.

## Mevcut durum

Veritabanı ve gerçek HTTP kontrolleri henüz bağlı değildir. Sahte kayıtlar kaldırılmıştır. `/dashboard` ve `/sites` sayfalarında **“Henüz kayıtlı web sitesi bulunmuyor.”** mesajı gösterilir. Toplam site sayısı 0, ölçüm bulunmayan durum kartları “—” gösterir.

`/sites/new` formunun tasarımı korunmuştur; **Siteyi Kaydet** düğmesi devre dışıdır. Bilgiler kaydedilmez ve başarı mesajı gösterilmez. `/sites/{site_id}` kayıt olmadığı için 404 döner; detay şablonu ileride gerçek veri, eksik ölçüm ve boş geçmişle kullanılmak üzere korunmuştur. Grafik yalnızca yanıt süresi ölçümü varsa oluşturulur.

`/` ve `/health` JSON endpointleri korunmuştur. PostgreSQL, worker, AWS veya yeni bir altyapı eklenmemiştir.

## Çalıştırma

Python 3.12 ile proje kökünde (mevcut `.venv` varsa ilk adımı atlayın):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Tarayıcıda http://127.0.0.1:8000/dashboard adresini açın. Site listesi `/sites`, ekleme formu `/sites/new`, API dokümantasyonu `/docs` adresindedir. Bootstrap ve Chart.js CDN kaynakları internet gerektirir.

Şablonlar `app/presentation/templates/`, CSS/JS `app/presentation/static/` altındadır. `pages.py` içindeki `get_sites()` şu an boş liste döndürür; sonraki backend entegrasyonunda uygulama katmanındaki sorguya bağlanmalıdır. Ölçülmemiş alanlar `None`, geçmiş boş liste olarak sağlanmalıdır; sayısal sıfır gerçek bir ölçüm olarak korunur.

## Test

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Testler boş durumları, kaldırılan etiketleri ve sol menü bloğunu, pasif kaydı, mevcut endpointleri ve detay şablonunun eksik/gerçek ölçüm davranışını doğrular. Test verileri yalnızca testlerde kullanılır; arayüze eklenmez.
