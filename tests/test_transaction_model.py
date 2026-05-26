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
