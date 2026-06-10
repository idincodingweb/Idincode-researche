# Idincode-researche
# Nurul Huda Rosalia (My Wife He Always Support Me ❤️

Software automation

```markdown
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
4. **Export per-kategori** — tiap niche jadi produk terpisah yang siap dijual (mis. di LemonSqueezy).
5. **Automasi** — re-scan terjadwal biar data selalu fresh (data basi = data mati).

---

## ⚖️ Prinsip Legal & Etika

Proyek ini **sengaja dibatasi** ke metode yang aman supaya lo gak kena masalah hukum dan narasi produk lo tetap jujur:

- ✅ **Pixel detection** — cuma baca markup HTML publik halaman depan (yang dikirim server ke browser siapa pun). Zero login, zero bypass.
- ✅ **PageSpeed** — pakai **Google PageSpeed Insights API resmi & gratis**.
- ✅ **Platform detection** — dari HTML/header publik.
- ✅ **User-Agent jujur** — bot identifiable, hormati `robots.txt`.
- ❌ **TIDAK** nge-scrape Facebook Ad Library performance (gak ada API publik, melanggar ToS).
- ❌ **TIDAK** nge-scrape TikTok/Instagram metrics (anti-bot brutal + ToS).

> **Catatan kejujuran:** banyak pixel sekarang di-load lewat Google Tag Manager / server-side tagging, jadi gak keliatan di HTML statik. Karena itu kolom dilabeli `meta_pixel_in_html`, **bukan** `has_meta_pixel` — biar lo gak over-claim ke buyer. Buyer teknis bakal respect kejujuran ini.

---

## 📂 Struktur Direktori

```
apex-intel/
├── pyproject.toml            # dependency & metadata proyek
├── .env.example              # template env (PAGESPEED_API_KEY)
├── targets.yaml              # ← "OTAK" produk: daftar target yang lo kurasi sendiri
├── README.md                 # dokumen ini
│
├── src/
│   ├── config.py             # konfigurasi: konkurensi, timeout, user-agent
│   ├── models.py             # dataclass type-safe: StoreRecord, PixelStatus, PageSpeedResult
│   ├── targets_loader.py     # load + validasi targets.yaml
│   │
│   ├── enrichers/            # modul independen, tiap modul bisa di-test sendiri
│   │   ├── pixels.py         # deteksi Meta/GA4/TikTok/Google Ads pixel dari HTML
│   │   ├── pagespeed.py      # ambil metrik PageSpeed via API Google
│   │   └── techstack.py      # deteksi platform (Shopify/WooCommerce/Wix/dll)
│   │
│   ├── qualifier.py          # scoring "emas" per-niche
│   ├── pipeline.py           # orchestrator: konkuren + resumable
│   └── export.py             # output CSV/JSON per-kategori
│
├── output/                   # hasil enrichment, dipisah per kategori/niche
│   ├── medical_high_ticket.csv
│   └── luxury_fitness.csv
│
└── .github/
    └── workflows/
        └── research.yml      # automasi re-scan terjadwal
```

---

## 🔄 Alur Kerja (Workflow)

```
┌──────────────┐   ┌──────────────┐   ┌─────────────────┐   ┌──────────────┐
│ targets.yaml │──▶│   ENRICHER   │──▶│    QUALIFIER    │──▶│    EXPORT    │
│ (lo kurasi)  │   │ (konkuren)   │   │ (scoring/niche) │   │ CSV per-niche│
└──────────────┘   └──────────────┘   └─────────────────┘   └──────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         PageSpeed    Pixel Check  Tech Stack
          (Google)    (HTML parse) (header/HTML)
```

**Penjelasan tiap tahap:**

1. **Input (`targets.yaml`)** — lo isi manual daftar domain per kategori. Tiap kategori punya `niche` yang nentuin aturan scoring-nya. Ini satu-satunya file yang lo sentuh rutin; nambah kategori = nambah SKU produk.

2. **Enricher** — untuk tiap domain, pipeline jalanin tiga pengecekan paralel: cek tracking pixel dari HTML, deteksi platform e-commerce, dan ambil skor PageSpeed dari Google. Jalan konkuren biar ratusan domain kelar cepat, dengan rate-limit biar gak kena ban.

3. **Qualifier** — tiap hasil enrichment dihitung `gold_score`-nya berdasarkan sinyal masalah: loading lambat, perf score rendah, gak ada ad pixel, dll. Threshold-nya beda per-niche (LCP 5 detik di klinik mewah = dosa besar, lebih ditolerir di niche lain).

4. **Export** — hasil di-split jadi satu CSV per kategori, lengkap dengan kolom alasan (`gold_reasons`) biar buyer langsung paham kenapa tiap lead masuk daftar. Tiap file = satu produk jual.

---

## 🛡️ Prinsip Engineering

- **Type-safe** — semua data lewat dataclass ber-type, pipeline self-documenting.
- **Graceful degradation** — satu domain gagal ≠ pipeline mati. Data parsial > gak ada data.
- **Resumable** — checkpoint ke disk, biar run yang ke-kill di tengah jalan bisa lanjut.
- **Idempotent** — re-run aman, gak dobel-dobel.

---

## 🚀 Roadmap

- [ ] **Fase 0** — Fondasi: struktur proyek, schema `targets.yaml`, loader + validator
- [ ] **Fase 1** — Enrichers: pixel, platform, PageSpeed
- [ ] **Fase 2** — Qualifier: scoring per-niche
- [ ] **Fase 3** — Orchestrator + Export
- [ ] **Fase 4** — Automasi (GitHub Actions) + packaging produk

---

## 📦 Output Produk

Tiap kategori di-export sebagai CSV terpisah, siap di-upload sebagai produk independen:

- `Premium Plastic Surgery Leads — Performance Issues` 
- `Luxury Gym Leads — Mobile Speed Problems`
- *(dan seterusnya, sesuai kategori yang lo kurasi)*

---

*Built by **Idin Iskandar** — Apex Market Intelligence.* 🔥
*Nurull Huda Rosalia is My Wife He Always Support Me ❤️*
```
