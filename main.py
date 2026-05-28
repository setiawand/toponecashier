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
