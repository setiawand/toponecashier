# KasirTop

Aplikasi kasir desktop untuk toko/warung kecil. Dibangun dengan Python + PyQt6, database SQLite lokal, dan dukungan cetak struk thermal printer.

## Fitur

- **Kasir** — scan barcode, tambah item, hitung kembalian, cetak struk
- **Manajemen Produk** — tambah/edit/hapus produk, harga beli & jual, satuan
- **Stok Masuk** — catat penerimaan barang dari supplier
- **Laporan** — ringkasan penjualan harian/bulanan dengan grafik

## Quick Start

**Prasyarat:** Python 3.11+ dan [uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
# 1. Clone dan masuk ke folder
git clone <repo-url>
cd toponecashier

# 2. Install dependensi & jalankan
uv run python main.py
```

uv otomatis membuat virtual environment dan menginstall dependensi dari `pyproject.toml`.

Database SQLite dibuat otomatis di `database/kasir.db` saat pertama kali dijalankan.

## Konfigurasi

Edit `config.json` di root folder (dibuat otomatis jika belum ada):

```json
{
  "store_name": "Warung Grosir",
  "store_address": "Jl. Contoh No. 1",
  "store_phone": "08xxxxxxxxxx",
  "low_stock_threshold": 5,
  "printer": {
    "type": "usb",
    "vendor_id": "0x0416",
    "product_id": "0x5011"
  }
}
```

`low_stock_threshold` — produk dengan stok di bawah angka ini akan ditandai sebagai stok menipis.

Untuk `vendor_id` dan `product_id` printer, cek dengan `lsusb` (Linux/Mac) atau Device Manager (Windows).

## Struktur Proyek

```
toponecashier/
├── main.py              # Entry point
├── config.json          # Konfigurasi toko
├── database/
│   ├── db.py            # Koneksi & inisialisasi DB
│   └── schema.sql       # Skema tabel SQLite
├── models/
│   ├── product.py       # CRUD produk & stok
│   ├── transaction.py   # Simpan & query penjualan
│   └── stock_in.py      # Penerimaan barang
├── views/
│   ├── main_window.py   # Window utama & navigasi
│   ├── kasir_view.py    # Layar kasir
│   ├── produk_view.py   # Manajemen produk
│   ├── stok_view.py     # Stok masuk
│   └── laporan_view.py  # Laporan & grafik
├── utils/
│   ├── formatter.py     # Format rupiah & datetime
│   └── printer.py       # Integrasi thermal printer
└── assets/
    └── style.qss        # Stylesheet PyQt6
```

## Development

```bash
# Jalankan semua tes
uv run pytest

# Jalankan dengan verbose
uv run pytest -v
```

## Dependensi Utama

| Package | Kegunaan |
|---------|----------|
| PyQt6 | GUI desktop |
| python-escpos | Cetak struk thermal printer |
| matplotlib | Grafik laporan |
| pytest / pytest-qt | Testing |
