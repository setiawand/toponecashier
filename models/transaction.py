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
