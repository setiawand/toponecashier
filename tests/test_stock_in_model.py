import pytest
from datetime import date
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
