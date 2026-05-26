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
