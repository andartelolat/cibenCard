# Business Card Generator - andartelolat

Generator kartu nama modern berbasis **Flask** + **Pillow (PIL)** dengan **live preview server-side**, **ekspor PNG/PDF**, **tema profesional**, **QR otomatis**, dan **App Navigator** (tombol floating + sidebar + dock) yang interaktif. UI dibuat ringan menggunakan **TailwindCSS (CDN)** dan **Alpine.js**.

> **Demo lokal:** jalan di `http://localhost:5013/`  
> **Platform:** Python 3.10+ (direkomendasikan)

---

## ✨ Fitur Utama

- 🎨 **Tema Profesional + Premium**  
  Tema bawaan: `pro-clean`, `pro-modern`, `pro-dark`, `pro-glass`, `pro-gradient`, `pro-kraft`, `pro-mono`, `pro-stripe`  
  Tema premium baru: **`pro-aurora`**, **`pro-carbon`**, **`pro-lines`**, **`pro-satin`**.

- 🖼️ **Live Preview**  
  Preview di-render server menggunakan engine yang sama dengan hasil akhir → hasil aman buat cetak.

- 🧾 **Ekspor PNG & PDF**  
  PNG cepat untuk share digital, PDF dengan DPI terkontrol (default 300) untuk cetak offset/printing.

- 🔎 **QR Otomatis**  
  Isi URL → otomatis generate QR dengan kontras aman di tema gelap (ada white frame).

- 🧩 **App Navigator** (Floating + Drawer + Dock)  
  Tombol **ikon-only 52×52 px** (ukuran tetap lintas device), bisa drag & pin, hotkey `Alt+K`, search, pinned apps, dan grouping.

- ☕ **Tombol Trakteer**  
  Tombol support langsung ke halaman Trakteer kamu.

- ⌨️ **Hotkeys**  
  - Generate cepat: **Ctrl/Cmd + Enter**  
  - Buka Navigator: **Alt + K**  
  - Tutup Navigator: **Esc**  
  - Pindah Drawer kiri/kanan: **[** atau **]**

---

## 📸 Tangkapan Layar

> (Letakkan screenshot kamu di folder `docs/` dan ganti link di bawah ini)
- UI utama: `docs/screen-main.png`
- Drawer navigator: `docs/screen-navigator.png`
- Contoh hasil kartu: `docs/sample-card.png`

```md
![UI Utama](docs/screen-main.png)
![Navigator](docs/screen-navigator.png)
![Sample Card](docs/sample-card.png)


🧱 Arsitektur Singkat

Backend: Flask

Rendering: Pillow (PIL) untuk background, panel, teks, logo, dan QR (via qrcode[pil])

UI: Tailwind (CDN), Alpine.js (CDN)

Output: PNG (preview & unduh), PDF (print-ready)

Cache sementara: Direktori temp OS (dibersihkan otomatis ≤ 12 jam)

🚀 Instalasi & Menjalankan
1) Clone & masuk folder
git clone https://github.com/<USERNAME>/<REPO_NAME>.git
cd <REPO_NAME>

2) Buat virtual env & install deps
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -U pip
pip install flask pillow "qrcode[pil]"

3) Jalankan app
python card_maker_pro_plus.py


Buka di browser: http://localhost:5013/

Catatan font: Aplikasi mencoba memuat font populer (Inter, Montserrat, DejaVuSans, Arial). Jika tidak ada, akan fallback ke default PIL. Untuk hasil cetak yang konsisten, sebaiknya taruh file .ttf di direktori kerja dan/atau install font di OS.

⚙️ Konfigurasi Penting

Trakteer Link
Cari string berikut di HTML dan ganti USERNAME:

<a href="https://trakteer.id/USERNAME/tip" ...>☕ Support</a>


Daftar Aplikasi di Navigator
Edit konstanta APP_LINKS di fungsi appNavigator() (bagian <script> di HTML).
Kamu bisa menambah pinned, groups, icon emoji, deskripsi, dan tag.

Port & Debug
Di bagian akhir file:

app.run(debug=True, host="0.0.0.0", port=5013)


Ubah port/debug sesuai kebutuhan.

Penyimpanan Sementara Hasil
File hasil akan disimpan di folder temp OS (mis. /tmp/card_maker_results) dan otomatis dibersihkan bila usia > 12 jam.

🧭 Endpoint

GET / — UI utama (form + preview)

POST / — Generate PNG + PDF (menghasilkan link unduh)

POST /api/preview — Render preview PNG (dipanggil oleh UI)

GET /result/<fname> — Menyajikan file hasil (PNG/PDF)

🛠️ Opsi Deploy
Docker (opsional)

Buat file Dockerfile sederhana:

FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flask pillow "qrcode[pil]"
EXPOSE 5013
CMD ["python", "card_maker_pro_plus.py"]


Bangun & jalankan:

docker build -t card-maker-pro-plus .
docker run --rm -p 5013:5013 card-maker-pro-plus

🧪 Checklist Kualitas

 FAB ukuran tetap (52×52 px) — tidak membesar saat switch mobile↔desktop

 Bounding drag disesuaikan (w/h = 56 px)

 -webkit-text-size-adjust:100% untuk cegah auto-resize teks di mobile

 White frame di QR untuk tema gelap (scan-friendly)

 Live preview render server-side

 Preset ukuran kartu (US/EU/bleed)

🐞 Troubleshooting

FAB tiba-tiba pindah/keluar layar:
Hapus localStorage key fab_pos lalu refresh halaman.

Font tidak cocok/terlalu “bergetar”:
Pastikan font .ttf tersedia. Kamu bisa taruh file Inter-Regular.ttf, Inter-SemiBold.ttf, dll. di root project.

QR sulit di-scan di tema gelap:
Pastikan URL benar (tanpa whitespace), dan gunakan aksen warna dengan kontras tinggi. QR sudah diberi white frame otomatis, tapi tekstur background terlalu ramai bisa mengganggu—pilih tema yang lebih bersih.

PDF terlalu berat:
Turunkan DPI (mis. 200) saat generate PDF.

🗺️ Roadmap

 Ekspor multi-kartu per sheet (A4, 8-up/10-up) + crop marks

 Impor kontak dari vCard/CSV

 Logo auto-invert untuk tema gelap

 Text style presets (tracking/leading)

 Undo/redo kecil pada form (draft save)

🤝 Kontribusi

PR & issue dipersilakan! Untuk kontribusi besar, buka issue dulu agar bisa diskusi scope-nya.

📜 Lisensi
andartelolat
MIT License. Lihat berkas LICENSE.
