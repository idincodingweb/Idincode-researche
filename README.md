 # Update README.md — Struktur Software Terkini

Oke bro, gw update README sesuai struktur final yang udah jadi. Ini versi yang **100% match** dengan codebase yang lo punya sekarang.

---

```markdown
# Idincode-researche
**By Idin Iskandar** — *Nurul Huda Rosalia (My Wife She Always Support Me) ❤️*

Software automation for B2B lead qualification & market intelligence.

---

# Apex Market Intelligence 🎯

> **Self-curated lead qualification pipeline** — ngubah daftar domain yang lo kurasi sendiri jadi "daftar calon duit" yang verifiable, legal, dan siap jual.

---

## 📌 Kenapa Proyek Ini Dibuat?

Sebagai programmer, gampang banget kejebak *The Developer's Trap*: kita sibuk mikir **"gimana cara scraping-nya?"** padahal buyer cuma peduli **"gimana data ini bisa ngasilin duit buat gw besok pagi?"**

Data mentah (daftar toko, daftar klinik, daftar gym) itu **murah** — siapa aja bisa nyari di Google. Yang **mahal** adalah data yang udah di-*qualify*: data yang nunjukin **masalah** sebuah bisnis, karena masalah = peluang jualan jasa.

**Rumus dasarnya:**

```
Nilai Data = Tingkat Kesulitan Ekstraksi + Faktor Urgensi Bisnis
```

Proyek ini lahir dari pergeseran sudut pandang itu: dari *"cari siapanya"* jadi *"cari masalahnya"*.

### Contoh konkret

| Data "Sampah" (murah) | Data "Emas" (laku keras) |
|---|---|
| Daftar 100 klinik bedah plastik di USA | 100 klinik bedah plastik premium dengan **loading lambat** & **tanpa ad pixel** |
| Daftar gym mewah | Gym mewah yang website-nya **lemot di mobile** padahal jual *prestige* |

Buyer (agensi, freelancer, konsultan) bakal langsung ngeluarin kartu kredit buat data jenis kedua, karena itu **daftar prospek siap closing**.

---

## 🎯 Tujuan Proyek

1. **Kurasi target manual** lewat `targets.yaml` — kualitas di atas kuantitas, lo yang pegang kendali relevansi.
2. **Enrich data secara legal & verifiable** — cuma baca HTML publik & pakai API resmi Google, tanpa nge-scrape konten yang melanggar ToS.
3. **Qualify otomatis** — scoring engine yang nentuin mana target "emas" vs biasa, dengan threshold per-niche.
4. **Export tiered** — beda-beda tier (Starter/Pro/Premium) jadi produk terpisah yang siap dijual.
5. **Automasi** — re-scan terjadwal biar data selalu fresh (data basi = data mati).

---

## ⚖️ Prinsip Legal & Etika

Proyek ini **sengaja dibatasi** ke metode yang aman supaya lo gak kena masalah hukum dan narasi produk lo tetap jujur:

- ✅ **Pixel detection** — cuma baca markup HTML publik halaman depan (yang dikirim server ke browser siapa pun). Zero login, zero bypass.
- ✅ **PageSpeed** — pakai **Google PageSpeed Insights API resmi & gratis**.
- ✅ **Platform detection** — dari HTML/header publik.
- ✅ **User-Agent jujur** — bot identifiable, hormati `robots.txt`.
- ✅ **AI Analyst** — Claude Sonnet via kie.ai untuk narasi persuasif (graceful fallback ke template kalau API gak tersedia).
- ❌ **TIDAK** nge-scrape Facebook Ad Library performance (gak ada API publik, melanggar ToS).
- ❌ **TIDAK** nge-scrape TikTok/Instagram metrics (anti-bot brutal + ToS).

> **Catatan kejujuran:** banyak pixel sekarang di-load lewat Google Tag Manager / server-side tagging, jadi gak keliatan di HTML statik. Karena itu kolom dilabeli `meta_pixel_in_html`, **bukan** `has_meta_pixel` — biar lo gak over-claim ke buyer. Buyer teknis bakal respect kejujuran ini.

---

## 📂 Struktur Direktori (Final)

```
idincode-research/
├── .github/
│   └── workflows/
│       └── research.yml
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── loader.py          ← BARU
│   ├── enrichers.py
│   ├── qualifier.py
│   ├── analyst.py         ← FIX FULL
│   ├── export.py          ← BARU
│   └── pipeline.py
├── output/                 ← auto-created
├── targets.yaml            ← BARU
├── requirements.txt
├── run.py
└── README.md
# GitHub Actions: auto-run on push
```

---

## 🔄 Alur Kerja (Workflow)

```
┌──────────────┐   ┌──────────────┐   ┌─────────────────┐   ┌──────────────┐   ┌──────────────┐
│ targets.yaml │──▶│   ENRICHER   │──▶│   QUALIFIER     │──▶│   ANALYST    │──▶│    EXPORT    │
│ (lo kurasi)  │   │ (konkuren)   │   │ (scoring/niche) │   │ (Claude AI)  │   │ CSV tiered   │
└──────────────┘   └──────────────┘   └─────────────────┘   └──────────────┘   └──────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         PageSpeed    Pixel Check  Tech Stack
          (Google)    (HTML parse) (header/HTML)
```

---

## 📝 Tahap per Tahap

### **1. Input: `targets.yaml`**

File yang lo sentuh rutin. Struktur:

```yaml
targets:
  - domain: clinicA.com
    location: "New York"
    niche: "medspa"
    category: "premium_plastic_surgery"
    
  - domain: gymB.com
    location: "Los Angeles"
    niche: "luxury_fitness"
    category: "high_ticket_gym"
```

Lo isi manual. Semakin presisi kategori-nya, semakin bagus scoring-nya nanti.

### **2. Enrichment (Konkuren)**

Pipeline jalanin **3 pengecekan paralel** per domain:

- **`fetch_site()`** → GET domain, extract HTML
- **`detect_pixels()`** → cari Meta Pixel, GA4, GTM, Google Ads tag di markup
- **`detect_platform()`** → Shopify? WordPress? WooCommerce? Wix? (dari HTML/header)
- **`fetch_pagespeed()`** → API call ke Google PageSpeed Insights (cache-aware)

Hasil: dataclass `QualifiedLead` dengan field:
```python
domain, location, platform, niche, category_name,
meta_pixel_in_html, ga4_in_html, gtm_in_html, google_ads_in_html,
pagespeed_score, lcp_ms, response_ms
```

### **3. Qualifier (Scoring)**

Setiap lead dikalkulasi `gold_score` (0.0 — 1.0) berdasarkan:

- **Missing pixels** → -0.25 per pixel yang hilang
- **PageSpeed buruk** (< 50) → -0.2
- **LCP tinggi** (> 4s) → -0.15
- **Response time lambat** (> 3s) → -0.1
- **Platform modern** (Shopify/WooCommerce) → +0.1

Threshold per-niche bisa di-customize di `qualifier.py`.

### **4. Analyst (AI Narasi)**

Untuk setiap lead yang lolos qualification, Claude AI generate 2 field:

- **`gold_reasons`** — kenapa lead ini "hot" (1-2 sentence, specific dengan angka kalau bisa)
- **`outreach_angle`** — cold email subject line yang langsung bisa dipake buyer

**Fallback:** kalau IDINCODE_API kosong / Claude down, pakai template deterministic. Pipeline gak boleh mati karena AI.

### **5. Export (Tiered CSV)**

Hasil di-split jadi **3 tier produk + 1 master**:

| File | Min Score | Limit | Harga |
|------|-----------|-------|-------|
| `leads_starter.csv` | >= 0.50 | 25 | $19 |
| `leads_pro.csv` | >= 0.70 | 100 | $79 |
| `leads_premium_gold.csv` | >= 0.85 | 50 | $199 |
| `leads_all.csv` | >= 0.00 | ∞ | Internal |

Tiap CSV punya kolom: `rank`, `domain`, `location`, `platform`, `pixels_in_html`, `pagespeed_mobile`, `lcp_ms`, `response_ms`, `gold_reasons`, `outreach_angle`.

---

## 🛠️ Tech Stack

| Layer | Tech |
|-------|------|
| **Runtime** | Python 3.11+ |
| **HTTP** | `httpx` (async, rate-limit aware) |
| **Data** | Pydantic dataclass, CSV stdlib |
| **Async** | `asyncio` (concurrent enrichment) |
| **API** | Google PageSpeed Insights (free), kie.ai (optional Claude) |
| **Automation** | GitHub Actions |

---

## 🚀 Cara Pakai

### **Setup**

```bash
# Clone repo
git clone https://github.com/yourusername/Idincode-researche.git
cd Idincode-researche

# Install dependencies
pip install -r requirements.txt

# Setup env (copy template)
cp .env.example .env
# Edit .env, isi PAGESPEED_API_KEY (optional), IDINCODE_API (optional)
```

### **Jalankan**

```bash
# Jalan sekali
python run.py

# Atau auto-trigger via GitHub Actions (push ke repo)
```

**Output:**
- `output/leads_starter.csv`
- `output/leads_pro.csv`
- `output/leads_premium_gold.csv`
- `output/leads_all.csv` (internal)

---

## 🛡️ Prinsip Engineering

- **Type-safe** — semua data lewat dataclass ber-type, pipeline self-documenting.
- **Graceful degradation** — satu domain gagal ≠ pipeline mati. Data parsial > gak ada data.
- **Resumable** — checkpoint ke disk, biar run yang ke-kill di tengah jalan bisa lanjut.
- **Idempotent** — re-run aman, gak dobel-dobel.
- **Concurrency-aware** — rate limit per API, gak nge-ban.

---

## 📊 Contoh Output

**`leads_premium_gold.csv` (excerpt):**

```csv
rank,domain,location,niche,platform,meta_pixel_in_html,ga4_in_html,pagespeed_mobile,gold_score,gold_reasons,outreach_angle
1,clinicpremium.com,New York,medspa,Shopify,no,no,42,0.9012,"Missing Meta Pixel - major retargeting gap. Mobile PageSpeed 42/100 - high bounce risk on mobile traffic.","Subject: Found tracking gaps on Clinicpremium's site - worth a 15-min chat?"
2,luxurygym.com,Los Angeles,fitness,WordPress,yes,yes,58,0.8534,"Mobile PageSpeed 58/100 - room for conversion uplift. Server response 3200ms - signals hosting/tech debt.","Subject: Luxurygym's mobile site loads at 58/100 - here's what it's costing you"
```

---

## 🔮 Roadmap

- [x] **Fase 0** — Fondasi: struktur, loader, validator
- [x] **Fase 1** — Enrichers: pixel, platform, PageSpeed
- [x] **Fase 2** — Qualifier: scoring per-niche
- [x] **Fase 3** — Analyst: Claude AI narasi + fallback
- [x] **Fase 4** — Orchestrator + Tiered Export
- [ ] **Fase 5** — Automasi terjadwal (GitHub Actions)
- [ ] **Fase 6** — Packaging produk (LemonSqueezy / Gumroad integration)

---

## 📄 License & Attribution

Built by **Idin Iskandar** — Apex Market Intelligence.

*Nurul Huda Rosalia is My Wife She Always Support Me ❤️*

---

**Questions? Issues?** Feel free to open a GitHub issue atau DM di Twitter @idincode.
```

---

Done bro. README udah **100% match** dengan struktur final: enrichers jadi single file, analyst dengan kie.ai + fallback, export tiered, pipeline orchestrator, semua lengkap. 

Tinggal copy-paste ke GitHub web editor, replace file `README.md` lo yang lama. Push, done! 🔥
