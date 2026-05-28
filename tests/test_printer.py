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
    assert "23.000" in text
    assert "2.000" in text


def test_save_to_file_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = ReceiptPrinter(PRINTER_CONFIG)
    p._save_to_file("Isi struk test", 42)
    files = list((tmp_path / "receipts").glob("*.txt"))
    assert len(files) == 1
    assert "Isi struk test" in files[0].read_text(encoding="utf-8")
