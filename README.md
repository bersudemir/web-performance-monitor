# Web Performans İzleme Sistemi

Python 3.12, FastAPI, PostgreSQL, APScheduler ve Nginx ile web sitesi performans izleme uygulaması. Dört Docker Compose servisi tek bir bridge ağında servis adlarıyla haberleşir. Yalnızca Nginx, yerel makineye port açar. PostgreSQL verileri adlandırılmış Docker volume'de kalır.

## Docker ile çalıştırma

Docker Desktop açıkken proje kökünde:

```powershell
Copy-Item .env.example .env  # Yalnızca ilk kurulumda; mevcut .env dosyasını koruyun.
# .env içindeki POSTGRES_PASSWORD değerini ilk kurulumda değiştirin.
docker compose up -d --build --wait --remove-orphans
docker compose ps
```

Arayüz: http://127.0.0.1:8080/dashboard. Port `NGINX_PORT` ile değiştirilebilir. `docker compose down` servisleri durdurur, verileri korur. **`docker compose down -v` kullanmayın; volume ve verileri siler.** İlk kurulumdan sonra `.env` parolasını değiştirmek mevcut PostgreSQL kullanıcısının parolasını otomatik değiştirmez.

Ubuntu 24.04 EC2'de `.env` içine `NGINX_BIND_ADDRESS=0.0.0.0` ve `NGINX_PORT=80` yazın; güvenlik grubunda yalnızca HTTP 80'i ve yönetim için gerekli SSH erişimini açın. PostgreSQL ve FastAPI host portu yayımlamaz.

## Servisler

- `nginx`: Tek giriş noktası; istekleri `web:8000` adresine iletir.
- `web`: FastAPI uygulaması. `db` sağlıklı olduğunda Alembic migration'ını tamamlar, sonra HTTP sunucusunu açar.
- `worker`: `web` sağlıklı olduktan sonra aynı Python imajıyla ayrı süreç olarak başlar; her kayıtlı siteyi kendi aralığında HTTPX ile ölçer.
- `db`: PostgreSQL 17. `web-performance-monitor_postgres_data` volume'ünü kullanır; host portu açmaz.

Servisler `app_net` ağında `db`, `web` gibi adlarla iletişim kurar. `POSTGRES_HOST=db` ve port `5432` konteyner içindeki bağlantı içindir. Parola `.env` üzerinden Compose'a verilir; dosya Git ve Docker build bağlamından dışlanır. Mevcut `postgres_data` volume adı korunmuştur.

Worker, yeni/güncellenen/silinen siteleri 5 saniyede bir algılar. HTTP 2xx/3xx UP, 4xx/5xx ve ağ hataları DOWN olarak saklanır. Özel ve yerel adresler DNS ve yönlendirme aşamalarında engellenir. Dashboard ve detay sayfası gerçek sonuçları gösterir; ölçüm yoksa veri uydurmaz.

## Doğrulama

```powershell
docker compose ps
docker compose exec web python -m alembic current
docker compose exec web python -m unittest discover -s tests -v
docker compose logs --tail 30 worker
docker compose stats --no-stream
```

`/health` yalnızca uygulama yanıtını sınar. Bootstrap ve Chart.js CDN kaynakları tarayıcıda internet gerektirir.
