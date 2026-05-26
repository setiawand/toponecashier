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
