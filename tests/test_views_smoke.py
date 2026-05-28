import sqlite3
import pytest
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
    assert win.windowTitle().startswith("TopOneCashier")
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
