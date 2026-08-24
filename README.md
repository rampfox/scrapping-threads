# 🕸️ Threads Scraper Bot

Bot scraping otomatis untuk Threads (Meta) dengan fitur anti-deteksi tingkat lanjut dan web GUI yang informatif.

## ✨ Fitur

- **🔍 Search by Keyword** — Scraping berdasarkan kata kunci di Threads (membutuhkan login)
- **📊 Timeline GUI** — Tampilan real-time post yang terurut dari terbaru
- **🛡️ Anti-Detection Stack:**
  - Playwright + stealth scripts (remove webdriver flag, canvas noise, dll)
  - Rotasi User-Agent yang realistis dengan fingerprint konsisten
  - Rate limiting dengan jitter Gaussian (1.8s - 4.5s random)
  - Exponential backoff saat error 429/503
  - Simulasi perilaku manusia (scroll, mouse movement)
- **🔄 Proxy Rotation** — Support HTTP/HTTPS/SOCKS5, health checking, session affinity
- **🤖 CAPTCHA Handler** — Deteksi otomatis + integrasi 2Captcha/Anti-Captcha (opsional)
- **⏱️ Polling Scheduler** — Interval 30 detik s/d 10 menit
- **🔐 Session Management** — Login Threads, cookie terenkripsi, persisten di DB
- **💾 SQLite Database** — Ringan, embedded, tidak perlu setup tambahan
- **🌐 Multi-bahasa** — Bahasa Indonesia & English (toggle di sidebar)
- **📤 Export Data** — JSON & CSV

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose

### 1. Clone & Setup
```bash
cd scrapping-threads
cp .env.example .env
```

### 2. Edit `.env` (opsional untuk konfigurasi awal)
```env
# Isi username & password Threads untuk fitur search
THREADS_USERNAME=your_username
THREADS_PASSWORD=your_password

# Interval scraping (detik) - default 120 (2 menit)
POLLING_INTERVAL=120
```

### 3. Jalankan
```bash
docker-compose up --build
```

### 4. Buka Browser
```
http://localhost:8000
```

## 📖 Panduan Penggunaan

### Langkah 1: Login Threads
Buka **Pengaturan** → **Akun Threads** → masukkan username & password → klik **Login**

> ⚠️ Gunakan akun khusus scraping, bukan akun personal. Ada risiko akun terkena restrict jika terdeteksi.

### Langkah 2: Tambah Kata Kunci
Buka **Kata Kunci** → masukkan kata kunci yang ingin dipantau → klik **Tambah**

### Langkah 3: Mulai Scraping
Klik tombol ▶️ di sidebar untuk memulai scraper.

Bot akan otomatis scraping setiap 2 menit (default) dan menampilkan hasilnya di **Timeline**.

### Langkah 4: Lihat Timeline
Buka **Timeline** untuk melihat semua post yang sudah di-scrape, filter by keyword, atau search.

## ⚙️ Konfigurasi

| Variable | Default | Deskripsi |
|----------|---------|-----------|
| `POLLING_INTERVAL` | 120 | Interval scraping dalam detik (30-600) |
| `MAX_CONCURRENT` | 2 | Maksimum sesi scraping paralel |
| `MAX_KEYWORDS` | 20 | Maksimum kata kunci aktif |
| `PROXY_ENABLED` | false | Aktifkan rotasi proxy |
| `PROXY_LIST` | - | Daftar proxy (comma-separated) |
| `CAPTCHA_SERVICE` | - | `2captcha` atau `anticaptcha` |
| `CAPTCHA_API_KEY` | - | API key untuk CAPTCHA solver |

## 🔌 API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/posts` | Daftar post (timeline) |
| GET | `/api/posts/stats` | Statistik |
| GET | `/api/keywords` | Daftar kata kunci |
| POST | `/api/keywords` | Tambah kata kunci |
| POST | `/api/keywords/{id}/scrape-now` | Scrape manual |
| GET | `/api/settings` | Pengaturan |
| PUT | `/api/settings` | Update pengaturan |
| POST | `/api/auth/login` | Login Threads |
| GET | `/api/scraper/status` | Status scraper |
| POST | `/api/scraper/start` | Mulai scraper |
| POST | `/api/scraper/stop` | Hentikan scraper |
| GET | `/api/scraper/logs` | Log scraper |
| POST | `/api/settings/export` | Export data (JSON/CSV) |

## 🏗️ Arsitektur

```
scrapping-threads/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Konfigurasi
│   ├── database.py          # SQLAlchemy + SQLite
│   ├── models.py            # DB Models
│   ├── scraper/
│   │   ├── engine.py        # Orchestrator utama
│   │   ├── threads_parser.py # Parser data Threads
│   │   ├── search.py        # Search implementation
│   │   ├── stealth.py       # Anti-detection scripts
│   │   ├── fingerprint.py   # UA & header rotation
│   │   ├── proxy_manager.py # Proxy pool
│   │   ├── rate_limiter.py  # Rate limiting
│   │   ├── captcha_handler.py # CAPTCHA solver
│   │   └── session_manager.py # Session & cookies
│   ├── scheduler/
│   │   └── polling.py       # APScheduler
│   └── api/
│       ├── routes_posts.py
│       ├── routes_keywords.py
│       ├── routes_settings.py
│       ├── routes_auth.py
│       └── routes_scraper.py
└── frontend/
    ├── index.html           # SPA HTML
    ├── css/style.css        # Design system
    └── js/
        ├── app.js           # Router & controller
        ├── api.js           # API client
        ├── timeline.js      # Timeline component
        ├── keywords.js      # Keywords component
        ├── settings.js      # Settings component
        ├── auth.js          # Auth component
        ├── i18n.js          # Translations
        └── utils.js         # Utilities
```

## ⚠️ Disclaimer

Tool ini dibuat untuk keperluan riset dan pemantauan. Penggunaan bot scraping dapat melanggar Terms of Service Threads/Meta. Gunakan secara bertanggung jawab dan dengan memperhatikan rate limit.

## 📝 License

MIT
