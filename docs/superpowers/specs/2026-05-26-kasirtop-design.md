# KasirTop — Desain Aplikasi POS Warung Grosir

**Tanggal:** 2026-05-26  
**Status:** Disetujui  
**Scope:** Versi 1 — Single kasir, desktop Python, SQLite

---

## 1. Ringkasan

KasirTop adalah aplikasi Point of Sale (POS) desktop untuk warung grosir kecil-menengah. Aplikasi ini menangani penjualan harian, manajemen stok (termasuk penerimaan barang dari supplier), dan laporan bisnis. Dibangun dengan Python + PyQt6, database SQLite, dan mendukung barcode scanner USB serta thermal printer ESC/POS.

---

## 2. Keputusan Desain

| Aspek | Keputusan | Alasan |
|---|---|---|
| UI Framework | PyQt6 | Layout kasir kompleks, input barcode natural, mature & documented |
| Database | SQLite (built-in) | Lightweight, zero-config, file tunggal, cukup untuk < 500 produk |
| Pengguna | Single kasir, tanpa login | Versi 1, satu operator |
| Struk | Thermal printer ESC/POS | Standar kasir, via `python-escpos` |
| Laporan ekspor | CSV | Format universal, mudah dibuka di Excel |

---

## 3. Arsitektur

**Pola:** MVC sederhana — Model (database layer), View (PyQt windows), Controller (business logic di dalam view).

**Stack:**
- Python 3.10+
- PyQt6 — UI desktop
- SQLite via `sqlite3` (built-in)
- `python-escpos` — thermal printer ESC/POS

**Struktur folder:**
```
kasirtop/
├── main.py                    # Entry point, inisialisasi app & window
├── database/
│   ├── db.py                  # Koneksi SQLite, inisialisasi schema
│   └── schema.sql             # DDL semua tabel
├── models/
│   ├── product.py             # CRUD produk, update stok
│   ├── transaction.py         # Simpan transaksi, query laporan
│   └── stock_in.py            # Penerimaan barang masuk
├── views/
│   ├── main_window.py         # Window utama + sidebar navigasi
│   ├── kasir_view.py          # Layar kasir (Layout B: full-width)
│   ├── produk_view.py         # Manajemen produk
│   ├── stok_view.py           # Penerimaan stok masuk
│   └── laporan_view.py        # Laporan & ekspor CSV
├── utils/
│   ├── printer.py             # ESC/POS thermal printer handler
│   ├── barcode.py             # Barcode input event handler
│   └── formatter.py           # Format Rupiah, tanggal
└── assets/
    └── style.qss              # Qt stylesheet (tema aplikasi)
```

**Navigasi:** Satu `QMainWindow` dengan sidebar tab vertikal — Kasir | Produk | Stok Masuk | Laporan.

---

## 4. Database Schema

```sql
-- Katalog produk
CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode     TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    price_buy   REAL NOT NULL DEFAULT 0,
    price_sell  REAL NOT NULL DEFAULT 0,
    stock       INTEGER NOT NULL DEFAULT 0,
    unit        TEXT NOT NULL DEFAULT 'pcs',
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Header transaksi penjualan
CREATE TABLE transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    subtotal    REAL NOT NULL DEFAULT 0,
    discount    REAL NOT NULL DEFAULT 0,
    total       REAL NOT NULL DEFAULT 0,
    payment     REAL NOT NULL DEFAULT 0,
    change      REAL NOT NULL DEFAULT 0,
    notes       TEXT
);

-- Detail item per transaksi
CREATE TABLE transaction_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  INTEGER NOT NULL REFERENCES transactions(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    qty             INTEGER NOT NULL,
    price_sell      REAL NOT NULL,
    subtotal        REAL NOT NULL
);

-- Header penerimaan barang dari supplier
CREATE TABLE stock_in (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    supplier_name   TEXT,
    invoice_no      TEXT,
    notes           TEXT
);

-- Detail item per penerimaan barang
CREATE TABLE stock_in_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_in_id INTEGER NOT NULL REFERENCES stock_in(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    qty         INTEGER NOT NULL,
    price_buy   REAL NOT NULL DEFAULT 0
);
```

**Aturan stok otomatis:**
- Transaksi penjualan selesai → `products.stock` berkurang sejumlah qty terjual
- Penerimaan barang disimpan → `products.stock` bertambah sejumlah qty diterima
- `price_buy` di `stock_in_items` digunakan untuk kalkulasi laba/rugi di laporan

---

## 5. Fitur Per Layar

### 5.1 Layar Kasir (Layout B — Full-width)

- `QLineEdit` scan barcode selalu dalam fokus; scanner USB langsung mengirim input tanpa klik apapun
- Scan barcode yang sama berulang → qty item di keranjang otomatis +1
- `QTableWidget` keranjang: kolom No | Nama Produk | Qty | Harga Satuan | Subtotal | Hapus
- Klik baris → edit qty via dialog input
- **BAYAR [F1]** → dialog pembayaran: input nominal, tampil kembalian, konfirmasi → cetak struk thermal
- **BATAL [F2]** → konfirmasi lalu kosongkan keranjang
- Produk tidak ditemukan di barcode → notifikasi merah non-blocking (QLabel berwarna)
- Total dan jumlah item selalu tampil real-time di bawah tabel

### 5.2 Layar Produk

- `QTableWidget` daftar semua produk; kolom stok berwarna merah jika stok ≤ 5
- Tombol **Tambah**, **Edit**, **Hapus**
- Form produk: barcode (bisa scan), nama, harga beli, harga jual, stok awal, satuan
- Pencarian produk via `QLineEdit` filter real-time by nama atau barcode

### 5.3 Layar Stok Masuk

**Mode Input Cepat:**
- Scan barcode → input qty → stok langsung bertambah, tanpa data supplier

**Mode Penerimaan Supplier:**
- Isi header: nama supplier, nomor faktur (opsional), tanggal, catatan
- Scan/tambah item satu per satu: barcode → nama auto-fill → qty → harga beli
- Simpan semua sekaligus → stok semua item terupdate atomik

- Tab riwayat: daftar penerimaan barang dengan filter tanggal, bisa klik untuk lihat detail

### 5.4 Layar Laporan

| Tab | Konten |
|---|---|
| Harian | Total transaksi hari ini, total omzet, estimasi laba kotor |
| Periode | Pilih rentang tanggal, grafik bar omzet per hari (`QChart`), tabel ringkasan |
| Stok | Daftar semua produk + stok saat ini, highlight merah jika hampir habis (≤ 5) |
| Per Produk | Produk terlaris (by qty), total qty terjual, total laba per produk |

- Semua tab memiliki tombol **Ekspor CSV**

---

## 6. Integrasi Barcode Scanner

- Scanner USB/Bluetooth bekerja sebagai *keyboard emulator* — tidak perlu driver khusus
- `QLineEdit` dengan `setFocus()` dipanggil ulang setiap kali fokus berpindah
- Scanner mengirim karakter diikuti `\n` atau `\r` → sinyal `returnPressed` memicu pencarian produk
- Tidak ada library tambahan yang dibutuhkan untuk scanner

---

## 7. Integrasi Thermal Printer

- Library: `python-escpos`
- Mendukung koneksi: USB, Serial (COM), dan Network (IP)
- Konfigurasi printer disimpan di `config.json` (type, vendor_id/product_id atau port/ip)
- Format struk:
  ```
  ================================
         NAMA TOKO
       Jl. Alamat Toko
  ================================
  28/05/2026 14:32  No: #0042
  --------------------------------
  Indomie Goreng
    5 pcs x Rp3.000     Rp 15.000
  Aqua 600ml
    2 pcs x Rp4.000     Rp  8.000
  --------------------------------
  TOTAL              Rp  23.000
  BAYAR              Rp  25.000
  KEMBALI            Rp   2.000
  ================================
       Terima kasih!
  ================================
  ```
- Jika printer tidak tersambung → struk otomatis disimpan sebagai file `.txt` di folder `receipts/`

---

## 8. Konfigurasi Toko

File `config.json` di root project menyimpan:
```json
{
  "store_name": "Warung Grosir Sumber Rejeki",
  "store_address": "Jl. Contoh No. 1, Jakarta",
  "store_phone": "08123456789",
  "low_stock_threshold": 5,
  "printer": {
    "type": "usb",
    "vendor_id": "0x04b8",
    "product_id": "0x0202"
  }
}
```
Dapat diubah via layar Settings sederhana (opsional di v1, atau edit file langsung).

---

## 9. Dependensi Python

```
PyQt6>=6.6.0
python-escpos>=3.0
```

Instalasi: `pip install PyQt6 python-escpos`

---

## 10. Batasan Versi 1

- Single kasir, tanpa sistem login/multi-user
- Tidak ada fitur diskon kompleks (hanya diskon nominal flat, opsional)
- Tidak ada sinkronisasi cloud atau multi-device
- Tidak ada manajemen supplier (hanya nama supplier di form penerimaan)
- Laporan ekspor hanya CSV (bukan PDF)
