# Workspace Agent Rules - Bot Auto Open & Auto Close ShopeeFood

## Project Overview
Proyek ini adalah bot otomatisasi **Auto Open & Auto Close** untuk outlet **ShopeeFood (ShopeePartner)** berdasarkan **Vercel Toggle** sebagai *Source of Truth*, **Status Penangguhan**, **Status Subscription**, dan **Jam Operasional**.

---

## Technical & Architectural Guidelines

### 1. System Priority Enforcement (Urutan Prioritas Keputusan)
Setiap eksekusi bot **WAJIB** mengevaluasi status outlet secara hierarkis mengikuti urutan prioritas berikut:
1. **Status Penangguhan** (Penangguhan = Ya $\rightarrow$ Paksa OFF)
2. **Status Subscription** (Subscription Expired $\rightarrow$ Nonaktifkan Auto Open)
3. **Vercel Toggle** (Source of Truth utama: ON / OFF)
4. **Jam Operasional** (Di luar jam operasional $\rightarrow$ Vercel Toggle & ShopeePartner Toggle = OFF)
5. **ShopeePartner Toggle** (Status aktual outlet di Shopee Partner)

### 2. Code Quality & Conventions
- **Language**: Python 3.10+
- **Code Style**: PEP 8 compliance, type hints (`typing`), modular functions.
- **Selenium/Browser Session**:
  - Gunakan browser session terisolasi (`chromeprofile` di root proyek).
  - Gunakan headless mode untuk server/production run jika tidak ada GUI display.
  - Tangani crash browser/session timeout secara robust dengan auto-reconnect/retry mechanism.
- **Data Source Integrity**:
  - Pisahkan layer Data Provider (Google Sheets / Vercel API / Database) dari layer Core Automation Bot.
  - Jangan melakukan hardcoding credential atau URL spreadsheet langsung di source code core logic; selalu manfaatkan `.env` dan `config/`.

### 3. Logging & Monitoring Standards
- Setiap aksi bot (buka store, tutup store, skip/no action, retry, error) harus dicatat dalam log terstruktur.
- Field log minimum yang wajib ada:
  `[Timestamp] [Store ID / Outlet Name] [Penangguhan] [Subscription] [Vercel Toggle] [Shopee Status Sebelum] [Tindakan Bot] [Shopee Status Sesudah] [Status/Result]`
- Tangani penanggulangan kegagalan (retry max 3 kali sebelum mengirimkan notifikasi alert error).

---

## Communication & Planning
- Selalu patuhi petunjuk dan struktur yang disetujui dalam `implementation_plan.md` saat melakukan pengerjaan fitur besar.
- Sertakan link markdown github (`[filename](file:///path/to/file)`) untuk setiap referensi file atau baris kode.
