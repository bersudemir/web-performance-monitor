# Web Performans İzleme Sistemi

Bu proje, web sitelerinin **erişilebilirliğini ve HTTP yanıt süresini** belirlenen aralıklarla izler. Siteler web arayüzünden yönetilir; bağımsız worker gerçek HTTP isteklerinin sonuçlarını PostgreSQL'e kaydeder. Dashboard son durumları, site detayı ise geçmişi ve hesaplanan ölçümleri gösterir. Bulut Bilişimde Sanallaştırma Teknolojileri dersi kapsamında uygulama, veritabanı ve ters vekil sunucu AWS EC2 üzerindeki Ubuntu 24.04 sanal makinede Docker Compose ile ayrı konteynerler olarak çalıştırılır.

Bu araç tarayıcıda sayfa yükleme hızını, JavaScript çalışmasını veya Core Web Vitals değerlerini ölçmez. Yanıt süresi, worker'ın HTTP isteğinin yanıt başlıklarını almasına kadar geçen süredir; DNS, bağlantı ve varsa yönlendirmeler bu süreye dahildir.

## Özellikler

- Site ekleme, listeleme, düzenleme ve silme; kontrol aralığını formda 1, 5, 10, 15, 30 veya 60 dakika olarak seçme.
- Her kayıtlı siteyi kendi aralığında otomatik kontrol etme; yeni, güncellenen ve silinen siteleri worker yeniden başlatılmadan algılama.
- Kontrol zamanı, UP/DOWN, HTTP kodu, milisaniye cinsinden yanıt süresi ve varsa hata mesajını saklama.
- Dashboard'da son kontrol durumları; site detayında kontrol geçmişi, Chart.js yanıt süresi grafiği, başarılı kontrol oranı, ortalama, minimum, maksimum ve p95.
- Ölçüm bulunmayan alanları boş gösterme; sahte performans verisi üretmeme.

Şemada aktif/pasif alanı yoktur: kayıtlı tüm siteler izlenir. Kullanıcı girişi ve bildirim sistemi bu sürümde bulunmaz.

## Kullanılan teknolojiler

| Teknoloji | Görevi |
| --- | --- |
| Python 3.12, FastAPI | Web uygulaması ve HTML sayfa yolları |
| HTTPX | Worker'ın gerçek HTTP/HTTPS istekleri |
| APScheduler | Siteye özel periyodik kontrol işleri |
| PostgreSQL 17 | Siteler ve kontrol sonuçları için kalıcı veritabanı |
| SQLAlchemy, Alembic | ORM modelleri, oturum yönetimi ve şema migration'ı |
| Jinja2, Bootstrap, Chart.js | Sunucu tarafı şablonlar, arayüz ve geçmiş grafiği |
| Nginx | Kullanıcı isteklerini FastAPI'ye ileten ters vekil |
| Docker, Docker Compose | Dört servisin imaj, konteyner, ağ ve volume yönetimi |
| AWS EC2, Ubuntu 24.04 | Sistemin çalıştırıldığı bulut sanal makinesi |

## Mimari ve sanallaştırma

AWS EC2, Ubuntu 24.04 çalıştıran bir bulut sanal makinesidir. Docker uygulama bileşenlerini ayrı konteynerlere ayırır; `web` ile `worker` aynı Python imajını farklı komutlarla kullanır. Compose'un `app_net` bridge ağı, servislerin birbirine `web` ve `db` adlarıyla erişmesini sağlar. PostgreSQL'in verisi `web-performance-monitor_postgres_data` adlı Docker volume'de tutulur ve konteyner yeniden oluşturulsa da kalır. Böylece EC2 sunucu sanallaştırmasını, konteynerler uygulama izolasyonunu, bridge ağı ağ izolasyonunu ve named volume kalıcı depolama soyutlamasını sağlar.

```mermaid
flowchart LR
    User["Kullanıcı"] -->|"HTTP :80"| SG["AWS Security Group"]
    subgraph EC2["AWS EC2 · Ubuntu 24.04 VM"]
        subgraph Net["Docker bridge ağı · app_net"]
            Nginx["nginx · :80"] -->|"web:8000"| Web["web · FastAPI"]
            Worker["worker · APScheduler / HTTPX"]
            DB["db · PostgreSQL :5432"]
            Web -->|"db:5432"| DB
            Worker -->|"db:5432"| DB
        end
        DB --> Volume[(postgres_data)]
    end
    SG --> Nginx
    Worker -->|"HTTP/HTTPS"| Sites["İzlenen internet siteleri"]
```

Yalnızca Nginx host portu yayımlar: yerelde `127.0.0.1:8080`, EC2 için `.env` ayarıyla `0.0.0.0:80`. PostgreSQL `5432` ve FastAPI `8000` Docker ağı içinde kullanılır, doğrudan host portu açmaz. EC2 Security Group gelen trafiği yönetir; **TCP 80'i uygulamaya erişmesine izin verilen IP aralığına, TCP 22'yi yalnızca yönetim IP'nize** açın. Güvenlik grubu kuralları bu depoda tanımlı değildir; gerçek EC2 ayarlarını ayrıca kontrol edin. Bu sürümde web arayüzü için HTTPS ve kullanıcı kimlik doğrulaması yoktur.

## İzleme iş akışı

```mermaid
flowchart TD
    A["Kullanıcı site ve aralık ekler"] --> B["FastAPI siteyi PostgreSQL'e kaydeder"]
    B --> C["Worker site listesindeki değişikliği algılar"]
    C --> D["Seçilen aralıkta HTTPX GET isteği"]
    D --> E{"Yanıt veya bağlantı hatası"}
    E -->|"HTTP yanıtı"| F["Durum kodu ve süreyi değerlendir"]
    E -->|"Hata"| G["DOWN ve hata metnini oluştur"]
    F --> H["Sonucu check_results tablosuna kaydet"]
    G --> H
    H --> I["Dashboard ve site detayında göster"]
```

Worker'ın işleyişi, kodun izlediği sırayla:

```text
zamanlayıcıyı başlat
her 5 saniyede:
    kayıtlı siteleri ve saniye cinsinden aralıklarını veritabanından oku
    eklenen veya aralığı değişen sitelerin işlerini ayarla; silinenlerin işlerini kaldır
her site işi için (aynı siteye eşzamanlı iş açma):
    site satırını kilitle; site silinmişse çık
    kontrol zamanını kaydet
    HTTP/HTTPS adresini ve yönlendirmeleri denetleyerek HTTPX GET gönder
    2xx/3xx → UP; 4xx/5xx veya bağlantı/timeout hatası → DOWN
    kod, süre ve varsa hatayı check_results tablosuna yaz
    tek site işinde beklenmeyen hata olursa logla; worker döngüsünü sürdür
```

Worker site listesini **5 saniyede bir** yeniler. APScheduler her site işi için `max_instances=1` kullanır; PostgreSQL satır kilidi de aynı site kontrollerini sıralar. Her HTTP isteği için HTTPX timeout'u **10 saniyedir**; yönlendirme sayısı en fazla **5** olur. Timeout toplam job süresi için kesin bir üst sınır değildir.

## Veritabanı

Alembic `0001` migration'ı iki tabloyu oluşturur; uygulama açılışında tablo veya sahte veri üretilmez. Site silinince ona bağlı sonuçlar da silinir.

```mermaid
erDiagram
    sites ||--o{ check_results : has
    sites {
        int id PK
        string name
        string url
        int check_interval_seconds
        datetime created_at
    }
    check_results {
        int id PK
        int site_id FK
        datetime checked_at
        boolean is_up
        int status_code
        int response_ms
        string error
    }
```

`check_interval_seconds` pozitif saniye değeridir. `status_code`, `response_ms` ve `error` nullable alanlardır. Bağlantı hatasında HTTP kodu ve yanıt süresi boş kalabilir; **0 ms** geçerli bir ölçümdür. Zaman alanları saat dilimi içerir. `check_results.site_id` foreign key ile `sites.id` alanına bağlıdır.

## Ölçüm metrikleri

HTTP **2xx ve 3xx** UP, **4xx ve 5xx** DOWN sayılır. `Location` başlıklı yönlendirmeler izlenir ve her hedef güvenlik denetiminden geçer; son yanıt değerlendirilir. Timeout, DNS ve bağlantı hataları da DOWN olarak saklanır; HTTP yanıtı alınmadıysa durum kodu ve yanıt süresi boş olabilir. SSL/TLS veya ağ hatası, sitenin herkes için kapalı olduğunu kanıtlamaz: ölçüm EC2 worker'ının bulunduğu ağdan yapılır.

**Başarılı kontrol oranı** = UP sonuç sayısı / tüm kontrol sayısı × 100. Ortalama, minimum, maksimum ve **p95** yalnızca yanıt süresi ölçülmüş kayıtlardan hesaplanır; p95 sıralı değerlerde `ceil(0,95 × adet)` konumundaki değerdir. Hata metni başarısız kontrolün detayında HTML kaçışıyla gösterilir. Grafik de yalnızca kaydedilmiş yanıt süresi değerlerini kullanır.

## Kurulum ve çalıştırma

Gereksinimler: Docker ve Docker Compose; yerelde Docker Desktop, sunucuda Ubuntu 24.04 üzerinde kurulu Docker. `.env` dosyası örnek dosyadan oluşturulur. İlk kurulumda güçlü bir `POSTGRES_PASSWORD` belirleyin; gerçek parolayı veya SSH anahtarını depoya eklemeyin. Mevcut veritabanı volume'ünde parolayı yalnızca `.env` içinde değiştirmek PostgreSQL kullanıcısının parolasını değiştirmez.

**Windows PowerShell — yerel geliştirme**

```powershell
git clone https://github.com/bersudemir/web-performance-monitor.git
cd web-performance-monitor
Copy-Item .env.example .env  # yalnızca ilk kurulumda
# .env içinde POSTGRES_PASSWORD değerini belirleyin.
# NGINX_BIND_ADDRESS=127.0.0.1 ve NGINX_PORT=8080 bırakın.
docker compose up -d --build --wait
docker compose ps
Invoke-WebRequest http://127.0.0.1:8080/health
```

Dashboard: `http://127.0.0.1:8080/dashboard`. `/health` FastAPI yanıtını sınar; veritabanının durumunu doğrudan ölçmez.

**Ubuntu 24.04 — AWS EC2**

```bash
git clone https://github.com/bersudemir/web-performance-monitor.git
cd web-performance-monitor
cp .env.example .env  # yalnızca ilk kurulumda
nano .env             # gerçek parolayı, NGINX_BIND_ADDRESS=0.0.0.0 ve NGINX_PORT=80 ayarlayın
sudo docker compose up -d --build --wait
sudo docker compose ps
curl http://127.0.0.1/health
```

EC2 Security Group'ta TCP 80 için kullanıcıların izin verilen kaynak IP aralığını, SSH 22 için yönetim IP'nizi tanımlayın. PostgreSQL 5432 ve FastAPI 8000 için dış erişim kuralı eklemeyin. Sunucunun genel IP'si veya DNS adıyla `http://<EC2-adresi>/dashboard` açılır. EC2 üzerinde bu komutların sonucu ve güvenlik grubu kuralları bu depodan doğrulanamaz.

Güncelleme ve veri kaybı olmadan durdurma için Windows PowerShell'de:

```bash
git pull --ff-only origin main
docker compose up -d --build --wait
docker compose logs --tail 50 web worker
docker compose down
```

Ubuntu EC2 terminalinde:

```bash
git pull --ff-only origin main
sudo docker compose up -d --build --wait
sudo docker compose logs --tail 50 web worker
sudo docker compose down
```

`docker compose down` konteynerleri kaldırır, named volume'ü korur. **`docker compose down -v` volume'ü ve veritabanı verilerini siler; kullanmayın.**

## Performans deneyleri

1, 5 ve 10 site senaryoları aynı kontrol aralığı ve aynı gözlem süresiyle karşılaştırılmalıdır. Her senaryoda `docker compose stats --no-stream` (Ubuntu'da `sudo docker compose stats --no-stream`) çıktısından CPU, RAM ve NET I/O değerleri birkaç kez alınır. **NET I/O konteyner başladığından beri biriken ağ trafiğidir; tek başına son örnekleme aralığının trafiği değildir.** Her senaryo için gözlem başlangıcı ve bitişindeki NET I/O değerlerini kaydedin; aynı süre boyunca oluşan artışı (bitiş − başlangıç) karşılaştırın. Tekrarları aynı aralık, süre ve benzer ağ koşullarında yapıp CPU/RAM örneklerini ve NET I/O artışlarını birlikte değerlendirin. Bu deneyler henüz yapılmamıştır; aşağıdaki tablo sonuç şablonudur.

| Site sayısı | Kontrol aralığı | Tekrar sayısı | CPU | RAM | NET I/O | Not |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | — | — | — | — | — | Ölçülmedi |
| 5 | — | — | — | — | — | Ölçülmedi |
| 10 | — | — | — | — | — | Ölçülmedi |

## Test ve sorun giderme

Ubuntu üzerinde yerel/ayrı test veritabanıyla Docker komutları (gerçek AWS veritabanında çalıştırmayın):

```bash
sudo docker compose ps
sudo docker compose exec web python -m alembic current
sudo docker compose exec web python -m alembic check
sudo docker compose exec web python -m unittest discover -s tests -v
sudo docker compose logs --tail 100 worker
sudo docker compose logs --tail 100 web db nginx
sudo docker compose stats --no-stream
```

Testler URL/DNS güvenliği, worker zamanlaması, veritabanına sonuç yazma, site CRUD işlemleri, arayüzde ölçümsüz/başarısız durumlar ve HTML kaçışını kapsar. Testler çalışan PostgreSQL gerektirir ve **geçici site/kontrol kayıtları yazar**; normal bitişte bunları temizlese de gerçek AWS veritabanı yerine yerel veya ayrı bir test veritabanında çalıştırılmalıdır. Windows'ta aynı Docker komutlarını `sudo` olmadan kullanın.

- **Konteyner sağlıksızsa:** `docker compose ps` ve ilgili servis loglarını inceleyin. `db` healthcheck'i `pg_isready`, `web` healthcheck'i `/health` kullanır. Worker logu zamanlayıcı ve HTTP hata kayıtlarını gösterir.
- **SSL/TLS veya bağlantı hatasında:** Worker'ın bulunduğu ağdan hedef siteye erişimi, DNS çözümünü ve sertifika durumunu inceleyin. Hata metni site detayında görülebilir.
- **Veritabanı bağlantısında:** Compose içinden `db:5432` kullanıldığını, `.env` kullanıcı/parola/veritabanı değerlerini ve volume'ün ilk oluşturulduğu zamanki parolayı kontrol edin. Host üzerinde 5432 yayımlanmaz.
- **Port 80 açılamıyorsa:** EC2 Security Group ve hostta 80 portunu kullanan başka bir servis olup olmadığını kontrol edin; yerel geliştirmede varsayılan port 8080'dir.

## Proje yapısı

```text
.
├── app/
│   ├── main.py                  # FastAPI uygulaması
│   ├── worker.py                # Bağımsız APScheduler süreci
│   ├── application/sites.py     # Site işlemleri ve ekran verisi
│   ├── infrastructure/
│   │   ├── config.py            # .env ve bağlantı ayarları
│   │   ├── database.py          # SQLAlchemy engine/oturum
│   │   ├── models.py            # Site ve CheckResult ORM modelleri
│   │   └── http_check.py        # HTTPX ölçümü ve adres denetimi
│   └── presentation/
│       ├── pages.py             # HTML yolları ve form işlemleri
│       ├── templates/           # Dashboard, site listesi/formu/detayı
│       └── static/              # Mevcut CSS ve grafik JavaScript'i
├── migrations/                  # Alembic ortamı ve 0001 migration'ı
├── nginx/default.conf          # Nginx → web ters vekil ayarı
├── tests/                      # Veritabanı, worker ve sayfa testleri
├── Dockerfile                  # Python 3.12 uygulama imajı
├── compose.yaml                # nginx, web, worker, db; ağ ve volume
├── .dockerignore               # İmaj bağlamından çıkarılan dosyalar
├── .env.example                # Ortam değişkeni şablonu
├── alembic.ini                 # Migration yapılandırması
└── requirements.txt            # Python bağımlılıkları
```

## Güvenlik ve sınırlamalar

Form yalnızca HTTP/HTTPS adreslerini kabul eder; worker DNS çözümlemesindeki tüm IP'leri ve her yönlendirme hedefini denetler, genel erişime açık olmayan adresleri engeller. HTTPX ortam proxy'lerini kullanmaz. Bu denetimler DNS ve yönlendirme kaynaklı SSRF riskini azaltır; uygulama yine de internete açık, kimlik doğrulamasız bir yönetim arayüzüdür. Web için HTTPS/TLS sonlandırması bu sürümde yoktur. EC2'de HTTP erişimini ihtiyaç duyulan kaynak IP'lerle sınırlayın. `.env`, `.pem`, `.key` ve sanal ortam Git ile Docker imajı dışında tutulur. Bootstrap ve Chart.js CDN kaynakları tarayıcıda internet gerektirir.
