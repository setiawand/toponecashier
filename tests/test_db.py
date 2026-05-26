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
