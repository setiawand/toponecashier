from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QHeaderView, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QComboBox, QDoubleSpinBox, QSpinBox,
)
from PyQt6.QtGui import QColor
from models.product import ProductModel
from utils.formatter import format_rupiah


class ProductDialog(QDialog):
    def __init__(self, product: dict = None, parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle("Tambah Produk" if not product else "Edit Produk")
        self.setMinimumWidth(360)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan atau ketik barcode...")
        layout.addRow("Barcode:", self.barcode_input)

        self.name_input = QLineEdit()
        layout.addRow("Nama Produk:", self.name_input)

        self.price_buy_spin = QDoubleSpinBox()
        self.price_buy_spin.setRange(0, 99_999_999)
        self.price_buy_spin.setDecimals(0)
        self.price_buy_spin.setSingleStep(500)
        layout.addRow("Harga Beli (Rp):", self.price_buy_spin)

        self.price_sell_spin = QDoubleSpinBox()
        self.price_sell_spin.setRange(0, 99_999_999)
        self.price_sell_spin.setDecimals(0)
        self.price_sell_spin.setSingleStep(500)
        layout.addRow("Harga Jual (Rp):", self.price_sell_spin)

        self.stock_spin = QSpinBox()
        self.stock_spin.setRange(0, 999_999)
        layout.addRow("Stok Awal:", self.stock_spin)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["pcs", "kg", "gram", "liter", "dus", "karton", "lusin"])
        self.unit_combo.setEditable(True)
        layout.addRow("Satuan:", self.unit_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if self.product:
            self.barcode_input.setText(self.product["barcode"])
            self.name_input.setText(self.product["name"])
            self.price_buy_spin.setValue(self.product["price_buy"])
            self.price_sell_spin.setValue(self.product["price_sell"])
            self.stock_spin.setValue(self.product["stock"])
            self.stock_spin.setEnabled(False)  # stok diubah via Stok Masuk
            idx = self.unit_combo.findText(self.product["unit"])
            if idx >= 0:
                self.unit_combo.setCurrentIndex(idx)
            else:
                self.unit_combo.setCurrentText(self.product["unit"])

    def _on_accept(self):
        if not self.barcode_input.text().strip():
            QMessageBox.warning(self, "Validasi", "Barcode tidak boleh kosong.")
            return
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validasi", "Nama produk tidak boleh kosong.")
            return
        self.accept()

    def get_values(self) -> dict:
        return {
            "barcode": self.barcode_input.text().strip(),
            "name": self.name_input.text().strip(),
            "price_buy": self.price_buy_spin.value(),
            "price_sell": self.price_sell_spin.value(),
            "stock": self.stock_spin.value(),
            "unit": self.unit_combo.currentText(),
        }


class ProdukView(QWidget):
    COLS = ["ID", "Barcode", "Nama Produk", "Harga Beli", "Harga Jual", "Stok", "Satuan"]

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.model = ProductModel(conn)
        self._products: list[dict] = []
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari nama atau barcode...")
        self.search_input.textChanged.connect(self._on_search)

        btn_add = QPushButton("+ Tambah")
        btn_add.setObjectName("btnPrimary")
        btn_add.clicked.connect(self._on_add)

        btn_edit = QPushButton("✏ Edit")
        btn_edit.clicked.connect(self._on_edit)

        btn_del = QPushButton("🗑 Hapus")
        btn_del.setObjectName("btnDanger")
        btn_del.clicked.connect(self._on_delete)

        toolbar.addWidget(self.search_input)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_edit)
        toolbar.addWidget(btn_del)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def _load(self, query: str = ""):
        self._products = self.model.search(query) if query else self.model.get_all()
        self.table.setRowCount(len(self._products))
        LOW = 5
        for row, p in enumerate(self._products):
            vals = [str(p["id"]), p["barcode"], p["name"],
                    format_rupiah(p["price_buy"]), format_rupiah(p["price_sell"]),
                    str(p["stock"]), p["unit"]]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if p["stock"] <= LOW:
                    item.setForeground(QColor("#ef4444"))
                self.table.setItem(row, col, item)

    def _on_search(self, text: str):
        self._load(text)

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        return self._products[row] if 0 <= row < len(self._products) else None

    def _on_add(self):
        dlg = ProductDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            self.model.create(v["barcode"], v["name"], v["price_buy"],
                              v["price_sell"], v["stock"], v["unit"])
            self._load()

    def _on_edit(self):
        p = self._selected()
        if not p:
            QMessageBox.information(self, "Edit", "Pilih produk terlebih dahulu.")
            return
        dlg = ProductDialog(product=p, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            self.model.update(p["id"], v["barcode"], v["name"],
                              v["price_buy"], v["price_sell"], v["unit"])
            self._load()

    def _on_delete(self):
        p = self._selected()
        if not p:
            QMessageBox.information(self, "Hapus", "Pilih produk terlebih dahulu.")
            return
        reply = QMessageBox.question(
            self, "Hapus", f"Hapus '{p['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.model.delete(p["id"])
            self._load()
