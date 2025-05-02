
# Letter Numbering App

Aplikasi web sederhana berbasis Python yang memungkinkan pengguna untuk melakukan melakukan penomoran otomatis pada bagian surat-menyurat.

## Fitur

- Tampilkan daftar data yang tersimpan
- Tambah entri baru
- Edit data yang sudah ada
- Hapus entri
- Desain antarmuka berbasis HTML + CSS

## Teknologi yang Digunakan

- Python 3
- Flask
- SQLite
- HTML/CSS (Jinja templates)

## Instalasi

1. **Clone repositori:**

```bash
git clone https://github.com/username/testapp.git
cd testapp/testapp
```

2. **Buat virtual environment dan aktifkan:**

```bash
python -m venv venv
source venv/bin/activate  # di Linux/macOS
venv\Scripts\activate     # di Windows
```

3. **Install dependensi:**

```bash
pip install flask
```

4. **Jalankan aplikasi:**

```bash
export FLASK_APP=app.py
flask run
```

Buka di browser: [http://localhost:5000](http://localhost:5000)

## Struktur Proyek

```
testapp/
├── app.py
├── templates/
│   ├── index.html
│   ├── add.html
│   └── edit.html
├── static/
│   └── style.css
└── instance/
    └── numbering.db
```

## Special Thanks
This project uses various AI platform (Grok, ChatGPT, DeepSeek) to create html, css, and python code. 

## Lisensi

[MIT License](LICENSE)
