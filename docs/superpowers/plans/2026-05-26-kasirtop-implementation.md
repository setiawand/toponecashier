# KasirTop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bangun aplikasi POS desktop warung grosir (KasirTop) dengan kasir, manajemen produk, stok masuk, laporan, barcode scanner, dan thermal printer.

**Architecture:** MVC sederhana — models (SQLite via sqlite3), views (PyQt6), utils (printer + formatter). Single SQLite file `kasirtop.db`. Navigasi via sidebar tab di main window.

**Tech Stack:** Python 3.10+, PyQt6, SQLite (built-in), python-escpos, matplotlib, pytest, pytest-qt

---

## File Map

| File | Tanggung Jawab |
|---|---|
| `requirements.txt` | Runtime deps (PyQt6, python-escpos, matplotlib) |
| `requirements-dev.txt` | Dev deps (pytest, pytest-qt) |
| `config.json` | Konfigurasi toko default |
| `database/schema.sql` | DDL 5 tabel SQLite |
| `database/db.py` | `get_connection()`, `init_db()` |
| `models/product.py` | `ProductModel` — CRUD + stok naik/turun |
| `models/transaction.py` | `TransactionModel` — save + laporan queries |
| `models/stock_in.py` | `StockInModel` — input cepat + penerimaan supplier |
| `utils/formatter.py` | `format_rupiah()`, `format_datetime()`, `format_date()` |
| `utils/printer.py` | `ReceiptPrinter` — ESC/POS + fallback ke file |
| `assets/style.qss` | Qt dark theme stylesheet |
| `views/main_window.py` | `MainWindow` — QMainWindow + sidebar navigasi |
| `views/kasir_view.py` | `KasirView` — barcode scan, cart, payment dialog |
| `views/produk_view.py` | `ProdukView` — CRUD produk + filter |
| `views/stok_view.py` | `StokView` — input cepat + penerimaan supplier + riwayat |
| `views/laporan_view.py` | `LaporanView` — 4 tab laporan + ekspor CSV |
| `main.py` | Entry point — inisialisasi app, db, window |
| `tests/conftest.py` | Shared pytest fixtures (db in-memory) |
| `tests/test_db.py` | Test init_db |
| `tests/test_formatter.py` | Test format_rupiah, format_datetime |
| `tests/test_product_model.py` | Test CRUD produk + stok |
| `tests/test_transaction_model.py` | Test save transaksi + laporan queries |
| `tests/test_stock_in_model.py` | Test quick_add + save_supplier_receipt |
| `tests/test_printer.py` | Test _format_receipt_text + _save_to_file |
| `tests/test_views_smoke.py` | Smoke test PyQt6 views (pytest-qt) |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `config.json`
- Create: `database/__init__.py`, `models/__init__.py`, `utils/__init__.py`, `views/__init__.py`, `tests/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: Buat requirements.txt**

```
PyQt6>=6.6.0
python-escpos>=3.0
matplotlib>=3.8.0
```

- [ ] **Step 2: Buat requirements-dev.txt**

```
pytest>=7.4.0
pytest-qt>=4.2.0
```

- [ ] **Step 3: Buat config.json**

```json
{
  "store_name": "Warung Grosir Sumber Rejeki",
  "store_address": "Jl. Contoh No. 1, Jakarta",
  "store_phone": "08123456789",
  "low_stock_threshold": 5,
  "printer": {
    "type": "usb",
    "vendor_id": "0x0416",
    "product_id": "0x5011"
  }
}
```

- [ ] **Step 4: Buat semua folder + `__init__.py` kosong**

```bash
mkdir -p database models utils views tests assets receipts
touch database/__init__.py models/__init__.py utils/__init__.py views/__init__.py tests/__init__.py
```

- [ ] **Step 5: Tambah ke .gitignore**

```
__pycache__/
*.pyc
*.db
.venv/
receipts/
.superpowers/
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Expected: semua package terinstall tanpa error.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt requirements-dev.txt config.json database/__init__.py models/__init__.py utils/__init__.py views/__init__.py tests/__init__.py assets/ receipts/.gitkeep .gitignore
git commit -m "chore: project setup — deps, folders, config"
```

---

## Task 2: Database Layer

**Files:**
- Create: `database/schema.sql`
- Create: `database/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_db.py`:
```python
import sqlite3
import pytest
from database.db import init_db


def test_init_db_creates_all_tables():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "products" in tables
    assert "transactions" in tables
    assert "transaction_items" in tables
    assert "stock_in" in tables
    assert "stock_in_items" in tables
    conn.close()


def test_init_db_is_idempotent():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    init_db(conn)  # kedua kali tidak boleh raise
    conn.close()
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
pytest tests/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'database.db'`

- [ ] **Step 3: Buat database/schema.sql**

```sql
CREATE TABLE IF NOT EXISTS products (
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

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    subtotal    REAL NOT NULL DEFAULT 0,
    discount    REAL NOT NULL DEFAULT 0,
    total       REAL NOT NULL DEFAULT 0,
    payment     REAL NOT NULL DEFAULT 0,
    change      REAL NOT NULL DEFAULT 0,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS transaction_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  INTEGER NOT NULL REFERENCES transactions(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    qty             INTEGER NOT NULL,
    price_sell      REAL NOT NULL,
    subtotal        REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_in (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    supplier_name   TEXT,
    invoice_no      TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS stock_in_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_in_id INTEGER NOT NULL REFERENCES stock_in(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    qty         INTEGER NOT NULL,
    price_buy   REAL NOT NULL DEFAULT 0
);
```

- [ ] **Step 4: Buat database/db.py**

```python
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "kasirtop.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: str = None) -> sqlite3.Connection:
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
```

- [ ] **Step 5: Jalankan test — pastikan PASS**

```bash
pytest tests/test_db.py -v
```

Expected:
```
PASSED tests/test_db.py::test_init_db_creates_all_tables
PASSED tests/test_db.py::test_init_db_is_idempotent
```

- [ ] **Step 6: Commit**

```bash
git add database/schema.sql database/db.py tests/test_db.py
git commit -m "feat: database schema and connection layer"
```

---

## Task 3: Formatter Utils

**Files:**
- Create: `utils/formatter.py`
- Create: `tests/test_formatter.py`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_formatter.py`:
```python
from utils.formatter import format_rupiah, format_datetime, format_date


def test_format_rupiah_thousands():
    assert format_rupiah(15000) == "Rp 15.000"


def test_format_rupiah_millions():
    assert format_rupiah(1500000) == "Rp 1.500.000"


def test_format_rupiah_zero():
    assert format_rupiah(0) == "Rp 0"


def test_format_rupiah_with_float():
    assert format_rupiah(15000.0) == "Rp 15.000"


def test_format_datetime():
    assert format_datetime("2026-05-26 14:32:00") == "26/05/2026 14:32"


def test_format_date():
    assert format_date("2026-05-26 14:32:00") == "26/05/2026"
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
pytest tests/test_formatter.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.formatter'`

- [ ] **Step 3: Implementasi utils/formatter.py**

```python
from datetime import datetime


def format_rupiah(amount: float) -> str:
    """Format angka sebagai Rupiah: Rp 15.000"""
    return "Rp {:,.0f}".format(amount).replace(",", ".")


def format_datetime(dt_str: str) -> str:
    """'YYYY-MM-DD HH:MM:SS' → 'DD/MM/YYYY HH:MM'"""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%d/%m/%Y %H:%M")


def format_date(dt_str: str) -> str:
    """'YYYY-MM-DD HH:MM:SS' → 'DD/MM/YYYY'"""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%d/%m/%Y")
```

- [ ] **Step 4: Jalankan test — pastikan PASS**

```bash
pytest tests/test_formatter.py -v
```

Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add utils/formatter.py tests/test_formatter.py
git commit -m "feat: formatter utils — format_rupiah, format_datetime"
```

---

## Task 4: Product Model

**Files:**
- Create: `models/product.py`
- Create: `tests/conftest.py`
- Create: `tests/test_product_model.py`

- [ ] **Step 1: Buat tests/conftest.py dengan shared fixture**

```python
import sqlite3
import pytest
from database.db import init_db


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    yield conn
    conn.close()
```

- [ ] **Step 2: Tulis test yang gagal**

`tests/test_product_model.py`:
```python
import pytest
from models.product import ProductModel


@pytest.fixture
def model(db):
    return ProductModel(db)


def test_create_returns_id(model):
    pid = model.create("1234567890", "Indomie Goreng", 2500, 3000, 100, "pcs")
    assert pid > 0


def test_get_by_barcode_found(model):
    model.create("1234567890", "Indomie Goreng", 2500, 3000, 100, "pcs")
    p = model.get_by_barcode("1234567890")
    assert p is not None
    assert p["name"] == "Indomie Goreng"
    assert p["stock"] == 100


def test_get_by_barcode_not_found(model):
    assert model.get_by_barcode("9999999999") is None


def test_get_all(model):
    model.create("111", "Produk A", 1000, 1500, 50, "pcs")
    model.create("222", "Produk B", 2000, 2500, 30, "pcs")
    assert len(model.get_all()) == 2


def test_get_all_sorted_by_name(model):
    model.create("222", "Zebra", 1000, 1500, 10, "pcs")
    model.create("111", "Apple", 1000, 1500, 10, "pcs")
    products = model.get_all()
    assert products[0]["name"] == "Apple"


def test_search_by_name(model):
    model.create("111", "Indomie Goreng", 2500, 3000, 100, "pcs")
    model.create("222", "Aqua Botol", 3000, 4000, 50, "pcs")
    results = model.search("indo")
    assert len(results) == 1
    assert results[0]["name"] == "Indomie Goreng"


def test_search_by_barcode(model):
    model.create("8990123456789", "Teh Botol", 2000, 2500, 60, "pcs")
    results = model.search("8990123")
    assert len(results) == 1


def test_update_product(model):
    pid = model.create("111", "Old Name", 1000, 1500, 10, "pcs")
    model.update(pid, "111", "New Name", 1200, 1700, "pcs")
    p = model.get_by_id(pid)
    assert p["name"] == "New Name"
    assert p["price_sell"] == 1700


def test_delete_product(model):
    pid = model.create("111", "To Delete", 1000, 1500, 10, "pcs")
    model.delete(pid)
    assert model.get_by_id(pid) is None


def test_decrease_stock(model):
    pid = model.create("111", "Produk", 1000, 1500, 100, "pcs")
    model.decrease_stock(pid, 10)
    assert model.get_by_id(pid)["stock"] == 90


def test_increase_stock(model):
    pid = model.create("111", "Produk", 1000, 1500, 10, "pcs")
    model.increase_stock(pid, 50)
    assert model.get_by_id(pid)["stock"] == 60
```

- [ ] **Step 3: Jalankan test — pastikan FAIL**

```bash
pytest tests/test_product_model.py -v
```

Expected: `ModuleNotFoundError: No module named 'models.product'`

- [ ] **Step 4: Implementasi models/product.py**

```python
import sqlite3
from datetime import datetime


class ProductModel:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_all(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM products ORDER BY name")
        return [dict(row) for row in cur.fetchall()]

    def get_by_barcode(self, barcode: str) -> dict | None:
        cur = self.conn.execute(
            "SELECT * FROM products WHERE barcode = ?", (barcode,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_by_id(self, product_id: int) -> dict | None:
        cur = self.conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def search(self, query: str) -> list[dict]:
        pattern = f"%{query}%"
        cur = self.conn.execute(
            "SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ? ORDER BY name",
            (pattern, pattern),
        )
        return [dict(row) for row in cur.fetchall()]

    def create(self, barcode: str, name: str, price_buy: float,
               price_sell: float, stock: int, unit: str) -> int:
        cur = self.conn.execute(
            """INSERT INTO products (barcode, name, price_buy, price_sell, stock, unit)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (barcode, name, price_buy, price_sell, stock, unit),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, product_id: int, barcode: str, name: str,
               price_buy: float, price_sell: float, unit: str) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            """UPDATE products
               SET barcode=?, name=?, price_buy=?, price_sell=?, unit=?, updated_at=?
               WHERE id=?""",
            (barcode, name, price_buy, price_sell, unit, now, product_id),
        )
        self.conn.commit()
        return True

    def delete(self, product_id: int) -> bool:
        self.conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        self.conn.commit()
        return True

    def decrease_stock(self, product_id: int, qty: int) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            "UPDATE products SET stock = stock - ?, updated_at=? WHERE id=?",
            (qty, now, product_id),
        )
        self.conn.commit()
        return True

    def increase_stock(self, product_id: int, qty: int) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            "UPDATE products SET stock = stock + ?, updated_at=? WHERE id=?",
            (qty, now, product_id),
        )
        self.conn.commit()
        return True
```

- [ ] **Step 5: Jalankan test — pastikan PASS**

```bash
pytest tests/test_product_model.py -v
```

Expected: 11 PASSED

- [ ] **Step 6: Commit**

```bash
git add models/product.py tests/conftest.py tests/test_product_model.py
git commit -m "feat: ProductModel — CRUD produk dan manajemen stok"
```

---

## Task 5: Transaction Model

**Files:**
- Create: `models/transaction.py`
- Create: `tests/test_transaction_model.py`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_transaction_model.py`:
```python
import pytest
from datetime import date
from models.product import ProductModel
from models.transaction import TransactionModel


@pytest.fixture
def product_model(db):
    return ProductModel(db)


@pytest.fixture
def model(db):
    return TransactionModel(db)


@pytest.fixture
def sample_pid(db, product_model):
    return product_model.create("111", "Indomie Goreng", 2500, 3000, 100, "pcs")


def _make_items(product_id, qty=5):
    return [{"product_id": product_id, "qty": qty,
             "price_sell": 3000, "subtotal": qty * 3000}]


def test_save_returns_id(model, sample_pid):
    tid = model.save(_make_items(sample_pid), payment=20000)
    assert tid > 0


def test_save_decreases_stock(model, product_model, sample_pid):
    model.save(_make_items(sample_pid, qty=5), payment=20000)
    assert product_model.get_by_id(sample_pid)["stock"] == 95


def test_save_calculates_total_and_change(model, db, sample_pid):
    tid = model.save(_make_items(sample_pid, qty=2), payment=10000, discount=0)
    row = db.execute("SELECT * FROM transactions WHERE id=?", (tid,)).fetchone()
    assert row["subtotal"] == 6000
    assert row["total"] == 6000
    assert row["change"] == 4000


def test_save_with_discount(model, db, sample_pid):
    tid = model.save(_make_items(sample_pid, qty=2), payment=10000, discount=1000)
    row = db.execute("SELECT * FROM transactions WHERE id=?", (tid,)).fetchone()
    assert row["total"] == 5000
    assert row["change"] == 5000


def test_get_today_summary_empty(model):
    summary = model.get_today_summary()
    assert summary["count"] == 0
    assert summary["total"] == 0
    assert summary["profit"] == 0


def test_get_today_summary(model, sample_pid):
    model.save(_make_items(sample_pid, qty=2), payment=10000)
    summary = model.get_today_summary()
    assert summary["count"] == 1
    assert summary["total"] == 6000
    assert summary["profit"] == 1000  # (3000-2500)*2


def test_get_daily_totals(model, sample_pid):
    model.save(_make_items(sample_pid, qty=1), payment=5000)
    today = date.today().isoformat()
    daily = model.get_daily_totals(today, today)
    assert len(daily) == 1
    assert daily[0]["total"] == 3000


def test_get_product_sales(model, sample_pid):
    model.save(_make_items(sample_pid, qty=3), payment=15000)
    today = date.today().isoformat()
    sales = model.get_product_sales(today, today)
    assert len(sales) == 1
    assert sales[0]["qty"] == 3
    assert sales[0]["profit"] == 1500  # (3000-2500)*3


def test_get_by_id_includes_items(model, sample_pid):
    tid = model.save(_make_items(sample_pid, qty=2), payment=10000)
    tx = model.get_by_id(tid)
    assert tx is not None
    assert len(tx["items"]) == 1
    assert tx["items"][0]["qty"] == 2
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
pytest tests/test_transaction_model.py -v
```

Expected: `ModuleNotFoundError: No module named 'models.transaction'`

- [ ] **Step 3: Implementasi models/transaction.py**

```python
import sqlite3
from datetime import date
from models.product import ProductModel


class TransactionModel:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._product_model = ProductModel(conn)

    def save(self, items: list[dict], payment: float,
             discount: float = 0, notes: str = "") -> int:
        """
        items: [{"product_id": int, "qty": int, "price_sell": float, "subtotal": float}]
        Returns new transaction id.
        """
        subtotal = sum(item["subtotal"] for item in items)
        total = subtotal - discount
        change = payment - total

        cur = self.conn.execute(
            """INSERT INTO transactions (subtotal, discount, total, payment, change, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (subtotal, discount, total, payment, change, notes),
        )
        transaction_id = cur.lastrowid

        for item in items:
            self.conn.execute(
                """INSERT INTO transaction_items
                   (transaction_id, product_id, qty, price_sell, subtotal)
                   VALUES (?, ?, ?, ?, ?)""",
                (transaction_id, item["product_id"], item["qty"],
                 item["price_sell"], item["subtotal"]),
            )
            self._product_model.decrease_stock(item["product_id"], item["qty"])

        self.conn.commit()
        return transaction_id

    def get_by_id(self, transaction_id: int) -> dict | None:
        cur = self.conn.execute(
            "SELECT * FROM transactions WHERE id=?", (transaction_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        items_cur = self.conn.execute(
            """SELECT ti.*, p.name, p.unit
               FROM transaction_items ti
               JOIN products p ON ti.product_id = p.id
               WHERE ti.transaction_id = ?""",
            (transaction_id,),
        )
        result["items"] = [dict(r) for r in items_cur.fetchall()]
        return result

    def get_today_summary(self) -> dict:
        today = date.today().isoformat()
        return self.get_period_summary(today, today)

    def get_period_summary(self, date_from: str, date_to: str) -> dict:
        cur = self.conn.execute(
            """SELECT COUNT(*) as count,
                      COALESCE(SUM(subtotal), 0) as subtotal,
                      COALESCE(SUM(discount), 0) as discount,
                      COALESCE(SUM(total), 0) as total
               FROM transactions
               WHERE date(date) BETWEEN ? AND ?""",
            (date_from, date_to),
        )
        row = dict(cur.fetchone())
        row["profit"] = self._calc_profit(date_from, date_to)
        return row

    def get_daily_totals(self, date_from: str, date_to: str) -> list[dict]:
        cur = self.conn.execute(
            """SELECT date(date) as day,
                      COUNT(*) as count,
                      COALESCE(SUM(total), 0) as total
               FROM transactions
               WHERE date(date) BETWEEN ? AND ?
               GROUP BY date(date)
               ORDER BY day""",
            (date_from, date_to),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_product_sales(self, date_from: str, date_to: str) -> list[dict]:
        cur = self.conn.execute(
            """SELECT ti.product_id,
                      p.name,
                      p.unit,
                      SUM(ti.qty) as qty,
                      SUM(ti.subtotal) as total,
                      SUM(ti.qty * (ti.price_sell - p.price_buy)) as profit
               FROM transaction_items ti
               JOIN transactions t ON ti.transaction_id = t.id
               JOIN products p ON ti.product_id = p.id
               WHERE date(t.date) BETWEEN ? AND ?
               GROUP BY ti.product_id
               ORDER BY qty DESC""",
            (date_from, date_to),
        )
        return [dict(row) for row in cur.fetchall()]

    def _calc_profit(self, date_from: str, date_to: str) -> float:
        cur = self.conn.execute(
            """SELECT COALESCE(SUM(ti.qty * (ti.price_sell - p.price_buy)), 0) as profit
               FROM transaction_items ti
               JOIN transactions t ON ti.transaction_id = t.id
               JOIN products p ON ti.product_id = p.id
               WHERE date(t.date) BETWEEN ? AND ?""",
            (date_from, date_to),
        )
        return cur.fetchone()["profit"]
```

- [ ] **Step 4: Jalankan test — pastikan PASS**

```bash
pytest tests/test_transaction_model.py -v
```

Expected: 10 PASSED

- [ ] **Step 5: Commit**

```bash
git add models/transaction.py tests/test_transaction_model.py
git commit -m "feat: TransactionModel — save penjualan dan queries laporan"
```

---

## Task 6: StockIn Model

**Files:**
- Create: `models/stock_in.py`
- Create: `tests/test_stock_in_model.py`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_stock_in_model.py`:
```python
import pytest
from models.product import ProductModel
from models.stock_in import StockInModel


@pytest.fixture
def product_model(db):
    return ProductModel(db)


@pytest.fixture
def model(db):
    return StockInModel(db)


@pytest.fixture
def sample_pid(db, product_model):
    return product_model.create("111", "Indomie Goreng", 2500, 3000, 10, "pcs")


def test_quick_add_increases_stock(model, product_model, sample_pid):
    model.quick_add(sample_pid, 50)
    assert product_model.get_by_id(sample_pid)["stock"] == 60


def test_save_supplier_receipt_returns_id(model, sample_pid):
    items = [{"product_id": sample_pid, "qty": 20, "price_buy": 2500}]
    sid = model.save_supplier_receipt("Supplier A", "INV-001", "Catatan", items)
    assert sid > 0


def test_save_supplier_receipt_increases_stock(model, product_model, sample_pid):
    items = [{"product_id": sample_pid, "qty": 20, "price_buy": 2500}]
    model.save_supplier_receipt("Supplier A", "INV-001", "", items)
    assert product_model.get_by_id(sample_pid)["stock"] == 30


def test_get_history_returns_records(model, sample_pid):
    items = [{"product_id": sample_pid, "qty": 10, "price_buy": 2500}]
    model.save_supplier_receipt("Supplier A", "INV-001", "", items)
    history = model.get_history()
    assert len(history) >= 1


def test_get_history_with_date_filter(model, sample_pid):
    items = [{"product_id": sample_pid, "qty": 5, "price_buy": 2500}]
    model.save_supplier_receipt("Supplier B", "INV-002", "", items)
    from datetime import date
    today = date.today().isoformat()
    history = model.get_history(today, today)
    assert len(history) >= 1


def test_get_detail_includes_items(model, sample_pid):
    items = [{"product_id": sample_pid, "qty": 10, "price_buy": 2500}]
    sid = model.save_supplier_receipt("Supplier A", "INV-001", "Test", items)
    detail = model.get_detail(sid)
    assert detail["supplier_name"] == "Supplier A"
    assert len(detail["items"]) == 1
    assert detail["items"][0]["qty"] == 10
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
pytest tests/test_stock_in_model.py -v
```

Expected: `ModuleNotFoundError: No module named 'models.stock_in'`

- [ ] **Step 3: Implementasi models/stock_in.py**

```python
import sqlite3
from models.product import ProductModel


class StockInModel:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._product_model = ProductModel(conn)

    def quick_add(self, product_id: int, qty: int) -> bool:
        """Input cepat tanpa data supplier."""
        sid = self._create_header(None, None, "Input Cepat")
        self.conn.execute(
            "INSERT INTO stock_in_items (stock_in_id, product_id, qty, price_buy) VALUES (?,?,?,0)",
            (sid, product_id, qty),
        )
        self._product_model.increase_stock(product_id, qty)
        self.conn.commit()
        return True

    def save_supplier_receipt(self, supplier_name: str, invoice_no: str,
                               notes: str, items: list[dict]) -> int:
        """
        items: [{"product_id": int, "qty": int, "price_buy": float}]
        Returns stock_in id.
        """
        sid = self._create_header(supplier_name, invoice_no, notes)
        for item in items:
            self.conn.execute(
                """INSERT INTO stock_in_items (stock_in_id, product_id, qty, price_buy)
                   VALUES (?, ?, ?, ?)""",
                (sid, item["product_id"], item["qty"], item["price_buy"]),
            )
            self._product_model.increase_stock(item["product_id"], item["qty"])
        self.conn.commit()
        return sid

    def _create_header(self, supplier_name, invoice_no, notes) -> int:
        cur = self.conn.execute(
            "INSERT INTO stock_in (supplier_name, invoice_no, notes) VALUES (?,?,?)",
            (supplier_name, invoice_no, notes),
        )
        return cur.lastrowid

    def get_history(self, date_from: str = None, date_to: str = None) -> list[dict]:
        if date_from and date_to:
            cur = self.conn.execute(
                """SELECT si.*, COUNT(sii.id) as item_count
                   FROM stock_in si
                   LEFT JOIN stock_in_items sii ON si.id = sii.stock_in_id
                   WHERE date(si.date) BETWEEN ? AND ?
                   GROUP BY si.id ORDER BY si.date DESC""",
                (date_from, date_to),
            )
        else:
            cur = self.conn.execute(
                """SELECT si.*, COUNT(sii.id) as item_count
                   FROM stock_in si
                   LEFT JOIN stock_in_items sii ON si.id = sii.stock_in_id
                   GROUP BY si.id ORDER BY si.date DESC LIMIT 100"""
            )
        return [dict(row) for row in cur.fetchall()]

    def get_detail(self, stock_in_id: int) -> dict | None:
        cur = self.conn.execute("SELECT * FROM stock_in WHERE id=?", (stock_in_id,))
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        items_cur = self.conn.execute(
            """SELECT sii.*, p.name, p.unit
               FROM stock_in_items sii
               JOIN products p ON sii.product_id = p.id
               WHERE sii.stock_in_id = ?""",
            (stock_in_id,),
        )
        result["items"] = [dict(r) for r in items_cur.fetchall()]
        return result
```

- [ ] **Step 4: Jalankan test — pastikan PASS**

```bash
pytest tests/test_stock_in_model.py -v
```

Expected: 7 PASSED

- [ ] **Step 5: Jalankan semua test sekaligus**

```bash
pytest tests/ -v --ignore=tests/test_views_smoke.py
```

Expected: semua PASSED

- [ ] **Step 6: Commit**

```bash
git add models/stock_in.py tests/test_stock_in_model.py
git commit -m "feat: StockInModel — quick_add dan penerimaan supplier"
```

---

## Task 7: Printer Utils

**Files:**
- Create: `utils/printer.py`
- Create: `tests/test_printer.py`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_printer.py`:
```python
import pytest
from utils.printer import ReceiptPrinter

PRINTER_CONFIG = {"type": "usb", "vendor_id": "0x0416", "product_id": "0x5011"}
STORE = {
    "store_name": "Warung Test",
    "store_address": "Jl. Test No. 1",
    "store_phone": "08123456789",
}
TRANSACTION = {
    "id": 42,
    "date": "2026-05-26 14:32:00",
    "total": 23000,
    "payment": 25000,
    "change": 2000,
    "discount": 0,
}
ITEMS = [
    {"name": "Indomie Goreng", "qty": 5, "price_sell": 3000,
     "subtotal": 15000, "unit": "pcs"},
    {"name": "Aqua 600ml", "qty": 2, "price_sell": 4000,
     "subtotal": 8000, "unit": "pcs"},
]


def test_format_receipt_contains_store_name():
    p = ReceiptPrinter(PRINTER_CONFIG)
    text = p._format_receipt_text(TRANSACTION, ITEMS, STORE)
    assert "Warung Test" in text


def test_format_receipt_contains_transaction_no():
    p = ReceiptPrinter(PRINTER_CONFIG)
    text = p._format_receipt_text(TRANSACTION, ITEMS, STORE)
    assert "#0042" in text


def test_format_receipt_contains_items():
    p = ReceiptPrinter(PRINTER_CONFIG)
    text = p._format_receipt_text(TRANSACTION, ITEMS, STORE)
    assert "Indomie Goreng" in text
    assert "Aqua 600ml" in text


def test_format_receipt_contains_totals():
    p = ReceiptPrinter(PRINTER_CONFIG)
    text = p._format_receipt_text(TRANSACTION, ITEMS, STORE)
    assert "23.000" in text   # total
    assert "2.000" in text    # kembalian


def test_save_to_file_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = ReceiptPrinter(PRINTER_CONFIG)
    p._save_to_file("Isi struk test", 42)
    files = list((tmp_path / "receipts").glob("*.txt"))
    assert len(files) == 1
    assert "Isi struk test" in files[0].read_text(encoding="utf-8")
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
pytest tests/test_printer.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.printer'`

- [ ] **Step 3: Implementasi utils/printer.py**

```python
from pathlib import Path
from datetime import datetime
from utils.formatter import format_rupiah, format_datetime


class ReceiptPrinter:
    LINE_WIDTH = 32

    def __init__(self, printer_config: dict):
        self.config = printer_config
        self.printer = None
        self._connect()

    def _connect(self) -> bool:
        try:
            ptype = self.config.get("type", "")
            if ptype == "usb":
                from escpos.printer import Usb
                vid = int(self.config["vendor_id"], 16)
                pid = int(self.config["product_id"], 16)
                self.printer = Usb(vid, pid)
            elif ptype == "serial":
                from escpos.printer import Serial
                self.printer = Serial(self.config["port"])
            elif ptype == "network":
                from escpos.printer import Network
                self.printer = Network(self.config["ip"])
            return True
        except Exception:
            self.printer = None
            return False

    def print_receipt(self, transaction: dict, items: list[dict],
                      store: dict) -> bool:
        """Returns True jika berhasil cetak, False jika disimpan ke file."""
        text = self._format_receipt_text(transaction, items, store)
        if self.printer:
            try:
                self.printer.text(text)
                self.printer.cut()
                return True
            except Exception:
                pass
        self._save_to_file(text, transaction["id"])
        return False

    def _format_receipt_text(self, transaction: dict, items: list[dict],
                              store: dict) -> str:
        w = self.LINE_WIDTH
        sep = "=" * w
        thin = "-" * w

        lines = [
            sep,
            store.get("store_name", "TOKO").center(w),
            store.get("store_address", "").center(w),
            store.get("store_phone", "").center(w),
            sep,
            f"{format_datetime(transaction['date'])}  No: #{transaction['id']:04d}",
            thin,
        ]

        for item in items:
            lines.append(item["name"])
            qty_line = (f"  {item['qty']} {item['unit']} x "
                        f"{format_rupiah(item['price_sell'])}")
            sub_str = format_rupiah(item["subtotal"])
            pad = w - len(qty_line) - len(sub_str)
            lines.append(qty_line + " " * max(1, pad) + sub_str)

        lines.append(thin)

        if transaction.get("discount", 0) > 0:
            d = format_rupiah(transaction["discount"])
            lines.append(f"{'DISKON':<{w - len(d)}}{d}")

        total_str = format_rupiah(transaction["total"])
        lines.append(f"{'TOTAL':<{w - len(total_str)}}{total_str}")

        bayar_str = format_rupiah(transaction["payment"])
        lines.append(f"{'BAYAR':<{w - len(bayar_str)}}{bayar_str}")

        kembali_str = format_rupiah(transaction["change"])
        lines.append(f"{'KEMBALI':<{w - len(kembali_str)}}{kembali_str}")

        lines += [sep, "Terima kasih!".center(w), sep, "\n\n\n"]
        return "\n".join(lines)

    def _save_to_file(self, text: str, transaction_id: int) -> None:
        receipts_dir = Path("receipts")
        receipts_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = receipts_dir / f"struk_{transaction_id:04d}_{ts}.txt"
        path.write_text(text, encoding="utf-8")
```

- [ ] **Step 4: Jalankan test — pastikan PASS**

```bash
pytest tests/test_printer.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add utils/printer.py tests/test_printer.py
git commit -m "feat: ReceiptPrinter — format struk ESC/POS dan fallback file"
```

---

## Task 8: Qt Stylesheet

**Files:**
- Create: `assets/style.qss`

- [ ] **Step 1: Buat assets/style.qss**

```css
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "SF Pro Display", Arial, sans-serif;
    font-size: 13px;
}

QWidget#sidebar {
    background-color: #181825;
    border-right: 1px solid #313244;
}

QLabel#logoLabel {
    color: #cba6f7;
    font-size: 18px;
    font-weight: bold;
    padding: 8px;
}

QPushButton#navButton {
    background-color: transparent;
    color: #a6adc8;
    border: none;
    border-radius: 6px;
    padding: 10px 12px;
    text-align: left;
}

QPushButton#navButton:hover { background-color: #313244; color: #cdd6f4; }
QPushButton#navButton:checked { background-color: #45475a; color: #cba6f7; font-weight: bold; }

QTableWidget {
    background-color: #181825;
    border: 1px solid #313244;
    gridline-color: #313244;
    selection-background-color: #45475a;
    border-radius: 4px;
}

QTableWidget::item { padding: 6px 8px; }

QHeaderView::section {
    background-color: #313244;
    color: #a6adc8;
    padding: 6px 8px;
    border: none;
    font-weight: bold;
}

QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px 10px;
    color: #cdd6f4;
}

QLineEdit:focus { border-color: #cba6f7; }

QLineEdit#scanInput {
    font-size: 15px;
    padding: 8px 12px;
    border-color: #a6e3a1;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
}

QPushButton:hover { background-color: #45475a; }

QPushButton#btnBayar {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-size: 15px;
    font-weight: bold;
    border-radius: 6px;
    padding: 12px;
}

QPushButton#btnBayar:hover { background-color: #94d3a2; }

QPushButton#btnBatal {
    background-color: #f38ba8;
    color: #1e1e2e;
    font-weight: bold;
    border-radius: 6px;
    padding: 12px;
}

QPushButton#btnBatal:hover { background-color: #e37a98; }
QPushButton#btnPrimary { background-color: #89b4fa; color: #1e1e2e; font-weight: bold; }
QPushButton#btnPrimary:hover { background-color: #74a0e8; }
QPushButton#btnDanger { background-color: #f38ba8; color: #1e1e2e; }

QLabel#cartTotalLabel { font-size: 16px; font-weight: bold; color: #f9e2af; }
QLabel#notifLabel[error="true"] { color: #f38ba8; }
QLabel#notifLabel[error="false"] { color: #a6e3a1; }
QLabel#statValue { font-size: 15px; font-weight: bold; color: #a6e3a1; }

QTabWidget::pane { border: 1px solid #313244; border-radius: 4px; }
QTabBar::tab { background-color: #181825; color: #a6adc8; padding: 8px 16px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #cba6f7; border-bottom: 2px solid #cba6f7; }

QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    color: #cdd6f4;
}

QGroupBox {
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 8px;
    color: #a6adc8;
}

QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }

QScrollBar:vertical {
    background: #181825;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical { background: #45475a; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
```

- [ ] **Step 2: Commit**

```bash
git add assets/style.qss
git commit -m "feat: Qt dark theme stylesheet (Catppuccin Mocha)"
```

---

## Task 9: Main Window

**Files:**
- Create: `views/main_window.py`

- [ ] **Step 1: Buat views/main_window.py**

```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel,
)
from PyQt6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self, conn, config: dict):
        super().__init__()
        self.conn = conn
        self.config = config
        self.setWindowTitle(f"KasirTop — {config.get('store_name', 'Toko')}")
        self.setMinimumSize(1100, 650)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(170)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 16, 8, 8)
        sidebar_layout.setSpacing(4)

        logo = QLabel("KasirTop")
        logo.setObjectName("logoLabel")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(12)

        self.stack = QStackedWidget()
        self.nav_buttons: list[QPushButton] = []

        pages = [
            ("🛒  Kasir",      self._make_kasir),
            ("📦  Produk",     self._make_produk),
            ("📥  Stok Masuk", self._make_stok),
            ("📊  Laporan",    self._make_laporan),
        ]

        for i, (label, factory) in enumerate(pages):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("navButton")
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            self.stack.addWidget(factory())

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack)
        self._switch(0)

    def _switch(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _make_kasir(self):
        from views.kasir_view import KasirView
        return KasirView(self.conn, self.config)

    def _make_produk(self):
        from views.produk_view import ProdukView
        return ProdukView(self.conn)

    def _make_stok(self):
        from views.stok_view import StokView
        return StokView(self.conn)

    def _make_laporan(self):
        from views.laporan_view import LaporanView
        return LaporanView(self.conn)
```

- [ ] **Step 2: Commit**

```bash
git add views/main_window.py
git commit -m "feat: MainWindow — sidebar navigasi dan stack layout"
```

---

## Task 10: Kasir View

**Files:**
- Create: `views/kasir_view.py`

- [ ] **Step 1: Buat views/kasir_view.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QLabel, QPushButton, QHeaderView, QDialog, QMessageBox,
    QDialogButtonBox, QFormLayout, QDoubleSpinBox, QInputDialog,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from models.product import ProductModel
from models.transaction import TransactionModel
from utils.printer import ReceiptPrinter
from utils.formatter import format_rupiah


class PaymentDialog(QDialog):
    def __init__(self, total: float, parent=None):
        super().__init__(parent)
        self.total = total
        self.setWindowTitle("Pembayaran")
        self.setMinimumWidth(320)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        total_label = QLabel(format_rupiah(self.total))
        total_label.setObjectName("cartTotalLabel")
        layout.addRow("Total:", total_label)

        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, self.total)
        self.discount_spin.setDecimals(0)
        self.discount_spin.setSingleStep(1000)
        self.discount_spin.valueChanged.connect(self._update)
        layout.addRow("Diskon (Rp):", self.discount_spin)

        self.payment_spin = QDoubleSpinBox()
        self.payment_spin.setRange(0, 99_999_999)
        self.payment_spin.setDecimals(0)
        self.payment_spin.setSingleStep(1000)
        self.payment_spin.setValue(self.total)
        self.payment_spin.valueChanged.connect(self._update)
        layout.addRow("Bayar (Rp):", self.payment_spin)

        self.change_label = QLabel("Rp 0")
        self.change_label.setObjectName("statValue")
        layout.addRow("Kembalian:", self.change_label)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addRow(self._buttons)
        self._update()

    def _update(self):
        disc = self.discount_spin.value()
        pay = self.payment_spin.value()
        final_total = self.total - disc
        change = pay - final_total
        self.change_label.setText(format_rupiah(max(0, change)))
        ok = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok:
            ok.setEnabled(pay >= final_total > 0)

    def _on_accept(self):
        disc = self.discount_spin.value()
        pay = self.payment_spin.value()
        if pay < (self.total - disc):
            QMessageBox.warning(self, "Kurang", "Nominal bayar kurang dari total.")
            return
        self.accept()

    def get_values(self) -> tuple[float, float, float]:
        disc = self.discount_spin.value()
        pay = self.payment_spin.value()
        return pay, disc, pay - (self.total - disc)


class KasirView(QWidget):
    COLS = ["No", "Produk", "Qty", "Harga Satuan", "Subtotal", ""]

    def __init__(self, conn, config: dict):
        super().__init__()
        self.conn = conn
        self.config = config
        self.product_model = ProductModel(conn)
        self.transaction_model = TransactionModel(conn)
        self.printer = ReceiptPrinter(config.get("printer", {}))
        self.cart: list[dict] = []
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Barcode input
        scan_row = QHBoxLayout()
        scan_row.addWidget(QLabel("📷 Scan / Barcode:"))
        self.scan_input = QLineEdit()
        self.scan_input.setObjectName("scanInput")
        self.scan_input.setPlaceholderText("Scan barcode atau ketik lalu Enter...")
        self.scan_input.returnPressed.connect(self._on_scan)
        scan_row.addWidget(self.scan_input)
        layout.addLayout(scan_row)

        # Notification
        self.notif_label = QLabel("")
        self.notif_label.setObjectName("notifLabel")
        layout.addWidget(self.notif_label)

        # Cart table
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(5, 40)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        # Total row
        total_row = QHBoxLayout()
        self.count_label = QLabel("0 item")
        self.total_label = QLabel("TOTAL: Rp 0")
        self.total_label.setObjectName("cartTotalLabel")
        total_row.addWidget(self.count_label)
        total_row.addStretch()
        total_row.addWidget(self.total_label)
        layout.addLayout(total_row)

        # Action buttons
        btn_row = QHBoxLayout()
        self.btn_bayar = QPushButton("💵  BAYAR  [F1]")
        self.btn_bayar.setObjectName("btnBayar")
        self.btn_bayar.clicked.connect(self._on_bayar)

        self.btn_batal = QPushButton("✕  BATAL  [F2]")
        self.btn_batal.setObjectName("btnBatal")
        self.btn_batal.clicked.connect(self._on_batal)

        btn_row.addWidget(self.btn_bayar, 3)
        btn_row.addWidget(self.btn_batal, 1)
        layout.addLayout(btn_row)

        self._refocus()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F1"), self, self._on_bayar)
        QShortcut(QKeySequence("F2"), self, self._on_batal)

    def _refocus(self):
        self.scan_input.setFocus()

    def _on_scan(self):
        barcode = self.scan_input.text().strip()
        self.scan_input.clear()
        if not barcode:
            return
        product = self.product_model.get_by_barcode(barcode)
        if not product:
            self._notify(f"⚠ Produk '{barcode}' tidak ditemukan.", error=True)
            return
        self._add_to_cart(product)
        self._notify(f"✓ {product['name']} ditambahkan.", error=False)

    def _add_to_cart(self, product: dict):
        for item in self.cart:
            if item["product_id"] == product["id"]:
                item["qty"] += 1
                item["subtotal"] = item["qty"] * item["price_sell"]
                self._refresh()
                return
        self.cart.append({
            "product_id": product["id"],
            "name": product["name"],
            "qty": 1,
            "price_sell": product["price_sell"],
            "subtotal": product["price_sell"],
            "unit": product["unit"],
        })
        self._refresh()

    def _refresh(self):
        self.table.setRowCount(len(self.cart))
        for row, item in enumerate(self.cart):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(item["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(item["qty"])))
            self.table.setItem(row, 3, QTableWidgetItem(format_rupiah(item["price_sell"])))
            self.table.setItem(row, 4, QTableWidgetItem(format_rupiah(item["subtotal"])))
            del_btn = QPushButton("🗑")
            del_btn.clicked.connect(lambda _, r=row: self._remove(r))
            self.table.setCellWidget(row, 5, del_btn)

        total = sum(i["subtotal"] for i in self.cart)
        count = sum(i["qty"] for i in self.cart)
        self.total_label.setText(f"TOTAL: {format_rupiah(total)}")
        self.count_label.setText(f"{count} item")

    def _remove(self, row: int):
        if 0 <= row < len(self.cart):
            self.cart.pop(row)
            self._refresh()

    def _on_double_click(self, row: int, col: int):
        if col == 2 and row < len(self.cart):
            item = self.cart[row]
            qty, ok = QInputDialog.getInt(
                self, "Ubah Qty", f"Qty untuk {item['name']}:", item["qty"], 0, 9999
            )
            if ok:
                if qty == 0:
                    self._remove(row)
                else:
                    item["qty"] = qty
                    item["subtotal"] = qty * item["price_sell"]
                    self._refresh()

    def _on_bayar(self):
        if not self.cart:
            self._notify("Keranjang kosong.", error=True)
            return
        total = sum(i["subtotal"] for i in self.cart)
        dlg = PaymentDialog(total, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            payment, discount, change = dlg.get_values()
            tid = self.transaction_model.save(
                self.cart, payment=payment, discount=discount
            )
            tx = self.transaction_model.get_by_id(tid)
            self.printer.print_receipt(tx, self.cart, self.config)
            self.cart.clear()
            self._refresh()
            self._notify(
                f"✓ Transaksi #{tid:04d} selesai. Kembalian: {format_rupiah(change)}",
                error=False,
                duration=5000,
            )
        self._refocus()

    def _on_batal(self):
        if not self.cart:
            return
        reply = QMessageBox.question(
            self, "Batal", "Kosongkan keranjang?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cart.clear()
            self._refresh()
            self._notify("Keranjang dikosongkan.")
        self._refocus()

    def _notify(self, msg: str, error: bool = False, duration: int = 3000):
        self.notif_label.setText(msg)
        self.notif_label.setProperty("error", str(error).lower())
        self.notif_label.style().unpolish(self.notif_label)
        self.notif_label.style().polish(self.notif_label)
        QTimer.singleShot(duration, lambda: self.notif_label.setText(""))
```

- [ ] **Step 2: Commit**

```bash
git add views/kasir_view.py
git commit -m "feat: KasirView — barcode scan, keranjang, dan dialog bayar"
```

---

## Task 11: Produk View

**Files:**
- Create: `views/produk_view.py`

- [ ] **Step 1: Buat views/produk_view.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QHeaderView, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QComboBox, QDoubleSpinBox, QSpinBox,
)
from PyQt6.QtGui import QColor
from models.product import ProductModel
from utils.formatter import format_rupiah


class ProductDialog(QDialog):
    def __init__(self, product: dict = None, parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle("Tambah Produk" if not product else "Edit Produk")
        self.setMinimumWidth(360)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan atau ketik barcode...")
        layout.addRow("Barcode:", self.barcode_input)

        self.name_input = QLineEdit()
        layout.addRow("Nama Produk:", self.name_input)

        self.price_buy_spin = QDoubleSpinBox()
        self.price_buy_spin.setRange(0, 99_999_999)
        self.price_buy_spin.setDecimals(0)
        self.price_buy_spin.setSingleStep(500)
        layout.addRow("Harga Beli (Rp):", self.price_buy_spin)

        self.price_sell_spin = QDoubleSpinBox()
        self.price_sell_spin.setRange(0, 99_999_999)
        self.price_sell_spin.setDecimals(0)
        self.price_sell_spin.setSingleStep(500)
        layout.addRow("Harga Jual (Rp):", self.price_sell_spin)

        self.stock_spin = QSpinBox()
        self.stock_spin.setRange(0, 999_999)
        layout.addRow("Stok Awal:", self.stock_spin)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["pcs", "kg", "gram", "liter", "dus", "karton", "lusin"])
        self.unit_combo.setEditable(True)
        layout.addRow("Satuan:", self.unit_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if self.product:
            self.barcode_input.setText(self.product["barcode"])
            self.name_input.setText(self.product["name"])
            self.price_buy_spin.setValue(self.product["price_buy"])
            self.price_sell_spin.setValue(self.product["price_sell"])
            self.stock_spin.setValue(self.product["stock"])
            self.stock_spin.setEnabled(False)  # stok diubah via Stok Masuk
            idx = self.unit_combo.findText(self.product["unit"])
            if idx >= 0:
                self.unit_combo.setCurrentIndex(idx)
            else:
                self.unit_combo.setCurrentText(self.product["unit"])

    def _on_accept(self):
        if not self.barcode_input.text().strip():
            QMessageBox.warning(self, "Validasi", "Barcode tidak boleh kosong.")
            return
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validasi", "Nama produk tidak boleh kosong.")
            return
        self.accept()

    def get_values(self) -> dict:
        return {
            "barcode": self.barcode_input.text().strip(),
            "name": self.name_input.text().strip(),
            "price_buy": self.price_buy_spin.value(),
            "price_sell": self.price_sell_spin.value(),
            "stock": self.stock_spin.value(),
            "unit": self.unit_combo.currentText(),
        }


class ProdukView(QWidget):
    COLS = ["ID", "Barcode", "Nama Produk", "Harga Beli", "Harga Jual", "Stok", "Satuan"]

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.model = ProductModel(conn)
        self._products: list[dict] = []
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari nama atau barcode...")
        self.search_input.textChanged.connect(self._on_search)

        btn_add = QPushButton("+ Tambah")
        btn_add.setObjectName("btnPrimary")
        btn_add.clicked.connect(self._on_add)

        btn_edit = QPushButton("✏ Edit")
        btn_edit.clicked.connect(self._on_edit)

        btn_del = QPushButton("🗑 Hapus")
        btn_del.setObjectName("btnDanger")
        btn_del.clicked.connect(self._on_delete)

        toolbar.addWidget(self.search_input)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_edit)
        toolbar.addWidget(btn_del)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def _load(self, query: str = ""):
        self._products = self.model.search(query) if query else self.model.get_all()
        self.table.setRowCount(len(self._products))
        LOW = 5
        for row, p in enumerate(self._products):
            vals = [str(p["id"]), p["barcode"], p["name"],
                    format_rupiah(p["price_buy"]), format_rupiah(p["price_sell"]),
                    str(p["stock"]), p["unit"]]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if p["stock"] <= LOW:
                    item.setForeground(QColor("#ef4444"))
                self.table.setItem(row, col, item)

    def _on_search(self, text: str):
        self._load(text)

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        return self._products[row] if 0 <= row < len(self._products) else None

    def _on_add(self):
        dlg = ProductDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            self.model.create(v["barcode"], v["name"], v["price_buy"],
                              v["price_sell"], v["stock"], v["unit"])
            self._load()

    def _on_edit(self):
        p = self._selected()
        if not p:
            QMessageBox.information(self, "Edit", "Pilih produk terlebih dahulu.")
            return
        dlg = ProductDialog(product=p, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            self.model.update(p["id"], v["barcode"], v["name"],
                              v["price_buy"], v["price_sell"], v["unit"])
            self._load()

    def _on_delete(self):
        p = self._selected()
        if not p:
            QMessageBox.information(self, "Hapus", "Pilih produk terlebih dahulu.")
            return
        reply = QMessageBox.question(
            self, "Hapus", f"Hapus '{p['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.model.delete(p["id"])
            self._load()
```

- [ ] **Step 2: Commit**

```bash
git add views/produk_view.py
git commit -m "feat: ProdukView — CRUD produk dengan filter real-time"
```

---

## Task 12: Stok Masuk View

**Files:**
- Create: `views/stok_view.py`

- [ ] **Step 1: Buat views/stok_view.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QHeaderView, QTabWidget, QLabel, QFormLayout,
    QSpinBox, QDoubleSpinBox, QMessageBox, QDateEdit, QGroupBox,
)
from PyQt6.QtCore import QDate
from models.product import ProductModel
from models.stock_in import StockInModel
from utils.formatter import format_rupiah, format_datetime


class StokView(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.product_model = ProductModel(conn)
        self.stock_in_model = StockInModel(conn)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        tabs = QTabWidget()
        tabs.addTab(self._quick_tab(), "⚡ Input Cepat")
        tabs.addTab(self._supplier_tab(), "🏭 Dari Supplier")
        tabs.addTab(self._history_tab(), "📋 Riwayat")
        layout.addWidget(tabs)

    # ── Input Cepat ───────────────────────────────────────
    def _quick_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()

        self.q_barcode = QLineEdit()
        self.q_barcode.setPlaceholderText("Scan barcode produk...")
        self.q_barcode.returnPressed.connect(self._q_lookup)
        form.addRow("Barcode:", self.q_barcode)

        self.q_name_label = QLabel("—")
        form.addRow("Produk:", self.q_name_label)

        self.q_qty = QSpinBox()
        self.q_qty.setRange(1, 99999)
        form.addRow("Jumlah Masuk:", self.q_qty)

        layout.addLayout(form)

        self.q_notif = QLabel("")
        layout.addWidget(self.q_notif)

        btn = QPushButton("✓ Tambah Stok")
        btn.setObjectName("btnPrimary")
        btn.clicked.connect(self._q_save)
        layout.addWidget(btn)
        layout.addStretch()

        self._q_product = None
        return widget

    def _q_lookup(self):
        barcode = self.q_barcode.text().strip()
        p = self.product_model.get_by_barcode(barcode)
        if p:
            self._q_product = p
            self.q_name_label.setText(f"{p['name']} (Stok: {p['stock']} {p['unit']})")
            self.q_notif.setText("")
        else:
            self._q_product = None
            self.q_name_label.setText("—")
            self.q_notif.setText(f"⚠ Produk '{barcode}' tidak ditemukan.")

    def _q_save(self):
        if not self._q_product:
            QMessageBox.warning(self, "Input Cepat", "Scan barcode produk terlebih dahulu.")
            return
        qty = self.q_qty.value()
        self.stock_in_model.quick_add(self._q_product["id"], qty)
        self.q_notif.setText(f"✓ Stok {self._q_product['name']} +{qty}.")
        self.q_barcode.clear()
        self.q_name_label.setText("—")
        self._q_product = None

    # ── Dari Supplier ─────────────────────────────────────
    def _supplier_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        header_box = QGroupBox("Data Supplier")
        hf = QFormLayout(header_box)

        self.s_name = QLineEdit()
        self.s_name.setPlaceholderText("Nama distributor / supplier")
        hf.addRow("Supplier:", self.s_name)

        self.s_invoice = QLineEdit()
        self.s_invoice.setPlaceholderText("Nomor faktur (opsional)")
        hf.addRow("No. Faktur:", self.s_invoice)

        self.s_notes = QLineEdit()
        hf.addRow("Catatan:", self.s_notes)

        layout.addWidget(header_box)

        item_row = QHBoxLayout()
        self.s_barcode = QLineEdit()
        self.s_barcode.setPlaceholderText("Scan barcode item...")
        self.s_barcode.returnPressed.connect(self._s_lookup)

        self.s_qty = QSpinBox()
        self.s_qty.setRange(1, 99999)

        self.s_price_buy = QDoubleSpinBox()
        self.s_price_buy.setRange(0, 99_999_999)
        self.s_price_buy.setDecimals(0)
        self.s_price_buy.setSingleStep(500)

        btn_add = QPushButton("+ Tambah Item")
        btn_add.clicked.connect(self._s_add)

        item_row.addWidget(QLabel("Barcode:"))
        item_row.addWidget(self.s_barcode)
        item_row.addWidget(QLabel("Qty:"))
        item_row.addWidget(self.s_qty)
        item_row.addWidget(QLabel("Harga Beli:"))
        item_row.addWidget(self.s_price_buy)
        item_row.addWidget(btn_add)
        layout.addLayout(item_row)

        self.s_items: list[dict] = []
        self.s_table = QTableWidget(0, 4)
        self.s_table.setHorizontalHeaderLabels(["Produk", "Qty", "Harga Beli", ""])
        self.s_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.s_table)

        btn_save = QPushButton("💾 Simpan Penerimaan Barang")
        btn_save.setObjectName("btnPrimary")
        btn_save.clicked.connect(self._s_save)
        layout.addWidget(btn_save)

        self._s_product = None
        return widget

    def _s_lookup(self):
        barcode = self.s_barcode.text().strip()
        p = self.product_model.get_by_barcode(barcode)
        if p:
            self._s_product = p
            self.s_price_buy.setValue(p["price_buy"])
        else:
            self._s_product = None
            QMessageBox.warning(self, "Produk", f"Barcode '{barcode}' tidak ditemukan.")
            self.s_barcode.clear()

    def _s_add(self):
        if not self._s_product:
            QMessageBox.warning(self, "Item", "Scan barcode terlebih dahulu.")
            return
        self.s_items.append({
            "product_id": self._s_product["id"],
            "name": self._s_product["name"],
            "qty": self.s_qty.value(),
            "price_buy": self.s_price_buy.value(),
        })
        self._s_refresh()
        self.s_barcode.clear()
        self._s_product = None

    def _s_refresh(self):
        self.s_table.setRowCount(len(self.s_items))
        for row, item in enumerate(self.s_items):
            self.s_table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.s_table.setItem(row, 1, QTableWidgetItem(str(item["qty"])))
            self.s_table.setItem(row, 2, QTableWidgetItem(format_rupiah(item["price_buy"])))
            del_btn = QPushButton("🗑")
            del_btn.clicked.connect(lambda _, r=row: self._s_remove(r))
            self.s_table.setCellWidget(row, 3, del_btn)

    def _s_remove(self, row: int):
        if 0 <= row < len(self.s_items):
            self.s_items.pop(row)
            self._s_refresh()

    def _s_save(self):
        if not self.s_items:
            QMessageBox.warning(self, "Simpan", "Tambahkan minimal satu item.")
            return
        self.stock_in_model.save_supplier_receipt(
            self.s_name.text().strip(),
            self.s_invoice.text().strip(),
            self.s_notes.text().strip(),
            self.s_items,
        )
        QMessageBox.information(
            self, "Berhasil", f"{len(self.s_items)} item stok diperbarui."
        )
        for w in (self.s_name, self.s_invoice, self.s_notes):
            w.clear()
        self.s_items.clear()
        self._s_refresh()

    # ── Riwayat ───────────────────────────────────────────
    def _history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Dari:"))
        self.h_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.h_from.setCalendarPopup(True)
        filter_row.addWidget(self.h_from)
        filter_row.addWidget(QLabel("Sampai:"))
        self.h_to = QDateEdit(QDate.currentDate())
        self.h_to.setCalendarPopup(True)
        filter_row.addWidget(self.h_to)
        btn = QPushButton("🔍 Filter")
        btn.clicked.connect(self._load_history)
        filter_row.addWidget(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.h_table = QTableWidget(0, 5)
        self.h_table.setHorizontalHeaderLabels(
            ["Tanggal", "Supplier", "No. Faktur", "Jml Item", "Catatan"]
        )
        self.h_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.h_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.h_table)

        self._load_history()
        return widget

    def _load_history(self):
        date_from = self.h_from.date().toString("yyyy-MM-dd")
        date_to = self.h_to.date().toString("yyyy-MM-dd")
        history = self.stock_in_model.get_history(date_from, date_to)
        self.h_table.setRowCount(len(history))
        for row, h in enumerate(history):
            self.h_table.setItem(row, 0, QTableWidgetItem(format_datetime(h["date"])))
            self.h_table.setItem(row, 1, QTableWidgetItem(h["supplier_name"] or "—"))
            self.h_table.setItem(row, 2, QTableWidgetItem(h["invoice_no"] or "—"))
            self.h_table.setItem(row, 3, QTableWidgetItem(str(h["item_count"])))
            self.h_table.setItem(row, 4, QTableWidgetItem(h["notes"] or ""))
```

- [ ] **Step 2: Commit**

```bash
git add views/stok_view.py
git commit -m "feat: StokView — input cepat, penerimaan supplier, dan riwayat"
```

---

## Task 13: Laporan View

**Files:**
- Create: `views/laporan_view.py`

- [ ] **Step 1: Buat views/laporan_view.py**

```python
import csv
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QTabWidget, QDateEdit, QHeaderView,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from models.transaction import TransactionModel
from models.product import ProductModel
from utils.formatter import format_rupiah


class LaporanView(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.tx_model = TransactionModel(conn)
        self.product_model = ProductModel(conn)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._harian_tab(), "📅 Harian")
        self.tabs.addTab(self._periode_tab(), "📆 Periode")
        self.tabs.addTab(self._stok_tab(), "📦 Stok")
        self.tabs.addTab(self._per_produk_tab(), "🏆 Per Produk")
        self.tabs.currentChanged.connect(self._on_tab)
        layout.addWidget(self.tabs)

    def _on_tab(self, idx: int):
        if idx == 0:
            self._load_harian()
        elif idx == 2:
            self._load_stok()

    # ── Harian ───────────────────────────────────────────
    def _harian_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)

        self._h_labels: dict[str, QLabel] = {}
        for key, label in [
            ("count",    "Jumlah Transaksi"),
            ("total",    "Total Omzet"),
            ("profit",   "Estimasi Laba Kotor"),
            ("discount", "Total Diskon"),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            row.addStretch()
            val = QLabel("—")
            val.setObjectName("statValue")
            row.addWidget(val)
            layout.addLayout(row)
            self._h_labels[key] = val

        layout.addStretch()
        btn = QPushButton("📥 Ekspor CSV")
        btn.clicked.connect(self._export_harian)
        layout.addWidget(btn)

        self._load_harian()
        return widget

    def _load_harian(self):
        s = self.tx_model.get_today_summary()
        self._h_labels["count"].setText(str(s["count"]))
        self._h_labels["total"].setText(format_rupiah(s["total"]))
        self._h_labels["profit"].setText(format_rupiah(s["profit"]))
        self._h_labels["discount"].setText(format_rupiah(s["discount"]))

    def _export_harian(self):
        today = date.today().isoformat()
        s = self.tx_model.get_today_summary()
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan CSV", f"laporan_harian_{today}.csv", "CSV (*.csv)"
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([
                    ["Tanggal", "Transaksi", "Omzet", "Laba", "Diskon"],
                    [today, s["count"], s["total"], s["profit"], s["discount"]],
                ])
            QMessageBox.information(self, "Ekspor", f"Tersimpan:\n{path}")

    # ── Periode ───────────────────────────────────────────
    def _periode_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        fr = QHBoxLayout()
        fr.addWidget(QLabel("Dari:"))
        self.p_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.p_from.setCalendarPopup(True)
        fr.addWidget(self.p_from)
        fr.addWidget(QLabel("Sampai:"))
        self.p_to = QDateEdit(QDate.currentDate())
        self.p_to.setCalendarPopup(True)
        fr.addWidget(self.p_to)
        btn = QPushButton("🔍 Tampilkan")
        btn.clicked.connect(self._load_periode)
        fr.addWidget(btn)
        fr.addStretch()
        layout.addLayout(fr)

        self._fig = Figure(figsize=(6, 2.5), facecolor="#1e1e2e")
        self._canvas = FigureCanvasQTAgg(self._fig)
        layout.addWidget(self._canvas)

        self._p_table = QTableWidget(0, 3)
        self._p_table.setHorizontalHeaderLabels(["Tanggal", "Transaksi", "Omzet"])
        self._p_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._p_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._p_table)

        btn_exp = QPushButton("📥 Ekspor CSV")
        btn_exp.clicked.connect(self._export_periode)
        layout.addWidget(btn_exp)

        self._p_data: list[dict] = []
        return widget

    def _load_periode(self):
        df = self.p_from.date().toString("yyyy-MM-dd")
        dt = self.p_to.date().toString("yyyy-MM-dd")
        self._p_data = self.tx_model.get_daily_totals(df, dt)

        self._fig.clear()
        ax = self._fig.add_subplot(111)
        ax.set_facecolor("#16213e")
        self._fig.patch.set_facecolor("#1e1e2e")
        if self._p_data:
            ax.bar([d["day"] for d in self._p_data],
                   [d["total"] for d in self._p_data], color="#4ade80")
            ax.tick_params(colors="white", labelsize=7)
            ax.xaxis.set_tick_params(rotation=45)
            for sp in ax.spines.values():
                sp.set_edgecolor("#334155")
        else:
            ax.text(0.5, 0.5, "Tidak ada data", ha="center", va="center",
                    color="white", transform=ax.transAxes)
        self._canvas.draw()

        self._p_table.setRowCount(len(self._p_data))
        for row, d in enumerate(self._p_data):
            self._p_table.setItem(row, 0, QTableWidgetItem(d["day"]))
            self._p_table.setItem(row, 1, QTableWidgetItem(str(d["count"])))
            self._p_table.setItem(row, 2, QTableWidgetItem(format_rupiah(d["total"])))

    def _export_periode(self):
        if not self._p_data:
            QMessageBox.information(self, "Ekspor", "Klik 'Tampilkan' terlebih dahulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan CSV", "laporan_periode.csv", "CSV (*.csv)"
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Tanggal", "Transaksi", "Omzet"])
                for d in self._p_data:
                    w.writerow([d["day"], d["count"], d["total"]])
            QMessageBox.information(self, "Ekspor", f"Tersimpan:\n{path}")

    # ── Stok ─────────────────────────────────────────────
    def _stok_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._s_table = QTableWidget(0, 5)
        self._s_table.setHorizontalHeaderLabels(
            ["Barcode", "Nama Produk", "Stok", "Satuan", "Status"]
        )
        self._s_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._s_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._s_table)

        btn = QPushButton("📥 Ekspor CSV")
        btn.clicked.connect(self._export_stok)
        layout.addWidget(btn)

        self._s_data: list[dict] = []
        self._load_stok()
        return widget

    def _load_stok(self):
        self._s_data = self.product_model.get_all()
        self._s_table.setRowCount(len(self._s_data))
        LOW = 5
        for row, p in enumerate(self._s_data):
            status = "⚠ Hampir habis" if p["stock"] <= LOW else "OK"
            for col, val in enumerate(
                [p["barcode"], p["name"], str(p["stock"]), p["unit"], status]
            ):
                item = QTableWidgetItem(val)
                if p["stock"] <= LOW:
                    item.setForeground(QColor("#ef4444"))
                self._s_table.setItem(row, col, item)

    def _export_stok(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan CSV", "laporan_stok.csv", "CSV (*.csv)"
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Barcode", "Nama", "Stok", "Satuan", "Status"])
                for p in self._s_data:
                    w.writerow([p["barcode"], p["name"], p["stock"], p["unit"],
                                 "Hampir habis" if p["stock"] <= 5 else "OK"])
            QMessageBox.information(self, "Ekspor", f"Tersimpan:\n{path}")

    # ── Per Produk ────────────────────────────────────────
    def _per_produk_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        fr = QHBoxLayout()
        fr.addWidget(QLabel("Dari:"))
        self.pp_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.pp_from.setCalendarPopup(True)
        fr.addWidget(self.pp_from)
        fr.addWidget(QLabel("Sampai:"))
        self.pp_to = QDateEdit(QDate.currentDate())
        self.pp_to.setCalendarPopup(True)
        fr.addWidget(self.pp_to)
        btn = QPushButton("🔍 Tampilkan")
        btn.clicked.connect(self._load_per_produk)
        fr.addWidget(btn)
        fr.addStretch()
        layout.addLayout(fr)

        self._pp_table = QTableWidget(0, 5)
        self._pp_table.setHorizontalHeaderLabels(
            ["Nama Produk", "Satuan", "Qty Terjual", "Total Omzet", "Laba"]
        )
        self._pp_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._pp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._pp_table)

        btn_exp = QPushButton("📥 Ekspor CSV")
        btn_exp.clicked.connect(self._export_per_produk)
        layout.addWidget(btn_exp)

        self._pp_data: list[dict] = []
        return widget

    def _load_per_produk(self):
        df = self.pp_from.date().toString("yyyy-MM-dd")
        dt = self.pp_to.date().toString("yyyy-MM-dd")
        self._pp_data = self.tx_model.get_product_sales(df, dt)
        self._pp_table.setRowCount(len(self._pp_data))
        for row, s in enumerate(self._pp_data):
            for col, val in enumerate([
                s["name"], s["unit"], str(s["qty"]),
                format_rupiah(s["total"]), format_rupiah(s["profit"]),
            ]):
                self._pp_table.setItem(row, col, QTableWidgetItem(val))

    def _export_per_produk(self):
        if not self._pp_data:
            QMessageBox.information(self, "Ekspor", "Klik 'Tampilkan' terlebih dahulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan CSV", "laporan_per_produk.csv", "CSV (*.csv)"
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Nama Produk", "Satuan", "Qty Terjual", "Omzet", "Laba"])
                for s in self._pp_data:
                    w.writerow([s["name"], s["unit"], s["qty"],
                                 s["total"], s["profit"]])
            QMessageBox.information(self, "Ekspor", f"Tersimpan:\n{path}")
```

- [ ] **Step 2: Commit**

```bash
git add views/laporan_view.py
git commit -m "feat: LaporanView — 4 tab laporan dan ekspor CSV"
```

---

## Task 14: Entry Point + Smoke Tests

**Files:**
- Create: `main.py`
- Create: `tests/test_views_smoke.py`

- [ ] **Step 1: Buat main.py**

```python
import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from database.db import get_connection, init_db
from views.main_window import MainWindow

DEFAULT_CONFIG = {
    "store_name": "Warung Grosir",
    "store_address": "",
    "store_phone": "",
    "low_stock_threshold": 5,
    "printer": {"type": "usb", "vendor_id": "0x0416", "product_id": "0x5011"},
}


def load_config() -> dict:
    path = Path("config.json")
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    qss = Path("assets/style.qss")
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))

    config = load_config()
    conn = get_connection()
    init_db(conn)

    window = MainWindow(conn, config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Tulis smoke test views**

`tests/test_views_smoke.py`:
```python
import sqlite3
import pytest
from PyQt6.QtWidgets import QApplication
from database.db import init_db
from views.main_window import MainWindow
from views.kasir_view import KasirView
from views.produk_view import ProdukView


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def config():
    return {
        "store_name": "Test Toko",
        "store_address": "Jl. Test",
        "store_phone": "0811",
        "low_stock_threshold": 5,
        "printer": {"type": "usb", "vendor_id": "0x0416", "product_id": "0x5011"},
    }


def test_main_window_creates(qtbot, db, config):
    win = MainWindow(db, config)
    qtbot.addWidget(win)
    assert win.windowTitle().startswith("KasirTop")
    assert win.stack.count() == 4


def test_kasir_view_has_scan_input(qtbot, db, config):
    view = KasirView(db, config)
    qtbot.addWidget(view)
    assert view.scan_input is not None
    assert view.table is not None


def test_kasir_scan_unknown_barcode_shows_notif(qtbot, db, config):
    view = KasirView(db, config)
    qtbot.addWidget(view)
    view.scan_input.setText("BARCODE_TIDAK_ADA")
    view.scan_input.returnPressed.emit()
    assert "tidak ditemukan" in view.notif_label.text()


def test_produk_view_creates(qtbot, db):
    view = ProdukView(db)
    qtbot.addWidget(view)
    assert view.table is not None
    assert view.table.rowCount() == 0
```

- [ ] **Step 3: Jalankan semua test**

```bash
pytest tests/ -v
```

Expected: semua PASSED (smoke test mungkin butuh display/virtual framebuffer di CI)

- [ ] **Step 4: Verifikasi aplikasi bisa dijalankan**

```bash
python main.py
```

Expected: jendela aplikasi terbuka dengan sidebar 4 menu (Kasir, Produk, Stok Masuk, Laporan).

- [ ] **Step 5: Commit final**

```bash
git add main.py tests/test_views_smoke.py
git commit -m "feat: main.py entry point dan smoke tests — KasirTop v1 selesai"
```

---

## Spec Coverage Checklist

| Fitur dari Spec | Diimplementasi di |
|---|---|
| Kasir full-width, barcode scan, qty +1 | Task 10 `KasirView._on_scan` |
| Dialog bayar + diskon flat + kembalian | Task 10 `PaymentDialog` |
| Shortcut F1 BAYAR, F2 BATAL | Task 10 `_setup_shortcuts` |
| Notifikasi produk tidak ditemukan | Task 10 `_notify(error=True)` |
| CRUD produk + stok merah ≤5 | Task 11 `ProdukView` |
| Filter produk real-time | Task 11 `_on_search` |
| Stok masuk input cepat | Task 12 `_quick_tab` |
| Stok masuk dari supplier | Task 12 `_supplier_tab` |
| Riwayat penerimaan barang | Task 12 `_history_tab` |
| Laporan harian | Task 13 `_harian_tab` |
| Laporan periode + grafik bar | Task 13 `_periode_tab` |
| Laporan stok + highlight merah | Task 13 `_stok_tab` |
| Laporan per produk (terlaris) | Task 13 `_per_produk_tab` |
| Ekspor CSV semua laporan | Task 13 `_export_*` |
| Thermal printer ESC/POS | Task 7 `ReceiptPrinter` |
| Fallback struk ke file .txt | Task 7 `_save_to_file` |
| Format Rupiah Indonesia | Task 3 `format_rupiah` |
| config.json konfigurasi toko | Task 1 + Task 14 |
| SQLite schema 5 tabel | Task 2 |
| Stok otomatis turun saat transaksi | Task 5 `TransactionModel.save` |
| Stok otomatis naik saat penerimaan | Task 6 `StockInModel` |
| Dark theme stylesheet | Task 8 |
