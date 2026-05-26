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
