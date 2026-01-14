# AutoScoring
<h3 align="center">Sistem Penilaian Otomatis Laporan Praktikum Mahasiswa</h3>

<p align="center">
  <strong>Lab FKI Universitas Muhammadiyah Surakarta</strong><br>
  Program Studi Informatika
</p>
---

## 📸 Demo Aplikasi

<p align="center">
  <img src="figures/dashboard.png" alt="AutoScoring Dashboard" width="800">
</p>

<p align="center"><em>Dashboard Penilaian AutoScoring - Upload laporan, atur parameter, dan mulai penilaian otomatis</em></p>

### Alur Kerja Sistem

<p align="center">
  <img src="figures/workflow.png" alt="AutoScoring Workflow" width="600">
</p>

<p align="center"><em>Diagram alur kerja sistem AutoScoring - dari upload hingga export hasil</em></p>

---

## 📖 Tentang AutoScoring

AutoScoring adalah aplikasi web berbasis Flask yang membantu dosen dan asisten laboratorium untuk menilai laporan praktikum atau tugas mahasiswa secara otomatis menggunakan Large Language Model (LLM) Google Gemini 2.5 Flash.

### Mengapa AutoScoring?

| Masalah Tradisional | Solusi AutoScoring |
|---------------------|-------------------|
| ⏱️ Penilaian manual memakan waktu 2-3 menit per laporan | ⚡ Penilaian otomatis dalam hitungan detik |
| 😓 Inkonsistensi akibat kelelahan penilai | 🎯 Konsistensi penilaian dengan standar yang sama |
| 📅 Keterlambatan umpan balik ke mahasiswa | 📊 Hasil instan dalam format CSV |
| 💰 Biaya langganan platform grading mahal | 🆓 Self-hosted, gratis, data tetap di institusi |

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| 📄 **Upload PDF Massal** | Unggah hingga 50 file PDF laporan mahasiswa sekaligus |
| 🔑 **Kunci Jawaban Opsional** | Gunakan PDF referensi sebagai acuan penilaian |
| 🤖 **Penilaian AI** | Google Gemini 2.5 Flash untuk analisis dan penilaian |
| 📊 **Export CSV** | Hasil penilaian dalam format CSV (No, NIM, Nama, Skor, Evaluasi) |
| 🔄 **Round-Robin API** | Rotasi 15 API key untuk menghindari rate limit |
| 🖥️ **GPU Support** | Akselerasi GPU untuk parsing PDF dengan Docling + EasyOCR |
| 🔒 **Sistem Login** | Autentikasi pengguna dengan role admin dan aslab |
| ⚙️ **Admin Panel** | Manajemen pengguna dan sistem via Flask-Admin |
| 🧹 **Auto Cleanup** | Pembersihan otomatis file temporary setiap hari |
| 📱 **Responsive UI** | Antarmuka modern yang responsif di semua perangkat |

---

## 🛠️ Teknologi

| Komponen | Teknologi |
|----------|-----------|
| Backend | Flask 3.0+, SQLAlchemy, Flask-Login, Flask-Admin |
| PDF Parser | Docling (IBM), EasyOCR |
| AI/LLM | Google Gemini 2.5 Flash |
| Database | SQLite3 |
| Frontend | Bootstrap 5, Dropzone.js |
| Deployment | Docker (GPU/CPU), Gunicorn |

---

## 📋 Persyaratan Sistem

### Minimum
- Python 3.10+
- 4GB RAM
- 10GB Disk Space

### Rekomendasi (dengan GPU)
- Python 3.11
- 8GB+ RAM
- NVIDIA GPU dengan CUDA 12.1+
- NVIDIA Container Toolkit (untuk Docker)

---

## 🚀 Instalasi

### Metode 1: Instalasi Lokal

1. **Clone repository**
   ```bash
   git clone https://github.com/your-repo/autoscoring.git
   cd autoscoring
   ```

2. **Buat virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Konfigurasi environment**
   ```bash
   cp .env.example .env
   # Edit .env dan isi API key Gemini
   ```

5. **Jalankan aplikasi**
   ```bash
   python run.py
   ```

6. **Akses aplikasi**
   
   Buka browser dan akses: http://localhost:5000

### Metode 2: Docker (GPU)

1. **Pastikan NVIDIA Container Toolkit terinstall**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

2. **Konfigurasi environment**
   ```bash
   cp .env.example .env
   # Edit .env dan isi API key Gemini
   ```

3. **Build dan jalankan**
   ```bash
   docker-compose up -d
   ```

### Metode 3: Docker (CPU Only)

```bash
cp .env.example .env
# Edit .env dan isi API key Gemini

docker-compose -f docker-compose.cpu.yml up -d
```

---

## ⚙️ Konfigurasi

### API Key Gemini

1. Buka [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Buat API key baru
3. Masukkan ke file `.env`:
   ```
   GEMINI_API_KEY_1=your-api-key-here
   GEMINI_API_KEY_2=your-second-api-key
   # ... hingga 15 key untuk round-robin
   ```

### Konfigurasi Lengkap (.env)

| Variable | Default | Deskripsi |
|----------|---------|-----------|
| `SECRET_KEY` | - | Secret key Flask (wajib diganti) |
| `MAX_PDF_COUNT` | 50 | Maksimal file PDF per job |
| `MAX_WORKERS` | 4 | Jumlah worker parallel |
| `ENABLE_OCR` | true | Aktifkan OCR untuk PDF scan |
| `ENABLE_CLEANUP` | true | Pembersihan otomatis file |
| `DEFAULT_SCORE_MIN` | 40 | Nilai minimum default |
| `DEFAULT_SCORE_MAX` | 100 | Nilai maksimum default |

---

## 👤 Akun Default

| Username | Password | Role |
|----------|----------|------|
| admin | informatika | Admin |
| aslab | informatika1 | Asisten Lab |

> ⚠️ **Penting:** Segera ganti password default setelah instalasi!

---

## 📖 Panduan Penggunaan

### 1. Login
- Buka aplikasi di browser
- Masukkan username dan password
- Klik "Masuk"

### 2. Upload Laporan
- Di dashboard, klik area upload atau drag-drop file PDF
- Pilih semua file PDF laporan mahasiswa (maks. 50 file)
- (Opsional) Upload kunci jawaban sebagai referensi

### 3. Konfigurasi Penilaian
- Atur rentang nilai (min-max)
- Pilih apakah ingin menyertakan evaluasi tertulis

### 4. Mulai Penilaian
- Klik tombol "Mulai Penilaian"
- Tunggu proses selesai (progress bar akan menunjukkan status)

### 5. Download Hasil
- Setelah selesai, klik "Unduh Hasil (CSV)"
- File CSV berisi: No, NIM, Nama, Nilai, Evaluasi

---

## 📁 Struktur Proyek

```
autoscoring/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration
│   ├── extensions.py        # Flask extensions
│   ├── models.py            # Database models
│   ├── routes/
│   │   ├── auth.py          # Authentication routes
│   │   ├── dashboard.py     # Main dashboard
│   │   └── admin_views.py   # Flask-Admin views
│   ├── services/
│   │   ├── docling_service.py   # PDF parsing
│   │   ├── gemini_service.py    # LLM scoring
│   │   ├── scoring_service.py   # Orchestration
│   │   └── cleanup_service.py   # File cleanup
│   ├── templates/           # HTML templates
│   └── static/              # CSS, JS, images
├── uploads/                 # Temporary uploads
├── results/                 # CSV results
├── logs/                    # Application logs
├── run.py                   # Entry point
├── Dockerfile               # GPU Docker image
├── Dockerfile.cpu           # CPU Docker image
├── docker-compose.yml       # GPU compose
├── docker-compose.cpu.yml   # CPU compose
├── requirements.txt         # Python dependencies
└── .env.example            # Environment template
```

---

## 🔧 Admin Panel

Akses admin panel di: `http://localhost:5000/admin`

Fitur admin:
- Manajemen pengguna (CRUD)
- Lihat riwayat pekerjaan
- Lihat hasil penilaian
- Log sistem
- Informasi sistem (GPU/CPU mode)

---

## 📊 Format Output CSV

| Kolom | Deskripsi |
|-------|-----------|
| No | Nomor urut |
| NIM | Nomor Induk Mahasiswa |
| student_name | Nama mahasiswa |
| Score | Nilai (sesuai rentang yang diatur) |
| Evaluation | Evaluasi singkat (maks. 100 kata) |

---

## 🐛 Troubleshooting

### PDF tidak terbaca
- Pastikan file PDF valid dan tidak corrupt
- Aktifkan OCR di `.env` untuk PDF hasil scan
- Periksa log di folder `logs/`

### Rate Limit Error
- Tambahkan lebih banyak API key Gemini
- Kurangi jumlah worker (`MAX_WORKERS`)
- Tunggu beberapa menit dan coba lagi

### GPU tidak terdeteksi
- Pastikan NVIDIA driver terinstall
- Verifikasi dengan `nvidia-smi`
- Pastikan CUDA version kompatibel

### Memory Error
- Kurangi jumlah worker
- Proses file dalam batch lebih kecil
- Restart aplikasi untuk membersihkan memory

---

## 📝 Limitasi

- Maksimal 50 file PDF per job (dapat dikonfigurasi)
- PDF harus dalam format teks (bukan hanya gambar, kecuali OCR aktif)
- Membutuhkan koneksi internet untuk Gemini API
- Evaluasi dalam Bahasa Indonesia

---

## 🔐 Keamanan

- Password di-hash menggunakan Werkzeug
- CSRF protection aktif
- Validasi file upload ketat
- Prompt injection mitigation pada LLM
- File temporary dibersihkan otomatis

---

## 📄 Lisensi

Aplikasi ini dikembangkan untuk keperluan internal Lab FKI Universitas Muhammadiyah Surakarta.

---

## 🤝 Kontribusi

Untuk melaporkan bug atau mengusulkan fitur, silakan hubungi tim Lab FKI UMS.

---

## 📞 Kontak

**Lab FKI Universitas Muhammadiyah Surakarta**  
Program Studi Informatika  
Jl. A. Yani, Pabelan, Kartasura, Sukoharjo 57162

---

*Dibuat dengan ❤️ untuk kemajuan pendidikan*

---

<p align="center">
  <strong>AutoScoring v1.0</strong><br>
  © 2025 Lab FKI Universitas Muhammadiyah Surakarta
</p>
