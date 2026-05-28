from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QHeaderView, QTabWidget, QLabel, QFormLayout,
    QSpinBox, QDoubleSpinBox, QMessageBox, QDateEdit, QGroupBox,
)
from PyQt6.QtCore import QDate
from models.product import ProductModel
from models.stock_in import StockInModel
from utils.formatter import format_rupiah, format_datetime


class StokView(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.product_model = ProductModel(conn)
        self.stock_in_model = StockInModel(conn)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        tabs = QTabWidget()
        tabs.addTab(self._quick_tab(), "⚡ Input Cepat")
        tabs.addTab(self._supplier_tab(), "🏭 Dari Supplier")
        tabs.addTab(self._history_tab(), "📋 Riwayat")
        layout.addWidget(tabs)

    # ── Input Cepat ───────────────────────────────────────
    def _quick_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()

        self.q_barcode = QLineEdit()
        self.q_barcode.setPlaceholderText("Scan barcode produk...")
        self.q_barcode.returnPressed.connect(self._q_lookup)
        form.addRow("Barcode:", self.q_barcode)

        self.q_name_label = QLabel("—")
        form.addRow("Produk:", self.q_name_label)

        self.q_qty = QSpinBox()
        self.q_qty.setRange(1, 99999)
        form.addRow("Jumlah Masuk:", self.q_qty)

        layout.addLayout(form)

        self.q_notif = QLabel("")
        layout.addWidget(self.q_notif)

        btn = QPushButton("✓ Tambah Stok")
        btn.setObjectName("btnPrimary")
        btn.clicked.connect(self._q_save)
        layout.addWidget(btn)
        layout.addStretch()

        self._q_product = None
        return widget

    def _q_lookup(self):
        barcode = self.q_barcode.text().strip()
        p = self.product_model.get_by_barcode(barcode)
        if p:
            self._q_product = p
            self.q_name_label.setText(f"{p['name']} (Stok: {p['stock']} {p['unit']})")
            self.q_notif.setText("")
        else:
            self._q_product = None
            self.q_name_label.setText("—")
            self.q_notif.setText(f"⚠ Produk '{barcode}' tidak ditemukan.")

    def _q_save(self):
        if not self._q_product:
            QMessageBox.warning(self, "Input Cepat", "Scan barcode produk terlebih dahulu.")
            return
        qty = self.q_qty.value()
        self.stock_in_model.quick_add(self._q_product["id"], qty)
        self.q_notif.setText(f"✓ Stok {self._q_product['name']} +{qty}.")
        self.q_barcode.clear()
        self.q_name_label.setText("—")
        self._q_product = None

    # ── Dari Supplier ─────────────────────────────────────
    def _supplier_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        header_box = QGroupBox("Data Supplier")
        hf = QFormLayout(header_box)

        self.s_name = QLineEdit()
        self.s_name.setPlaceholderText("Nama distributor / supplier")
        hf.addRow("Supplier:", self.s_name)

        self.s_invoice = QLineEdit()
        self.s_invoice.setPlaceholderText("Nomor faktur (opsional)")
        hf.addRow("No. Faktur:", self.s_invoice)

        self.s_notes = QLineEdit()
        hf.addRow("Catatan:", self.s_notes)

        layout.addWidget(header_box)

        item_row = QHBoxLayout()
        self.s_barcode = QLineEdit()
        self.s_barcode.setPlaceholderText("Scan barcode item...")
        self.s_barcode.returnPressed.connect(self._s_lookup)

        self.s_qty = QSpinBox()
        self.s_qty.setRange(1, 99999)

        self.s_price_buy = QDoubleSpinBox()
        self.s_price_buy.setRange(0, 99_999_999)
        self.s_price_buy.setDecimals(0)
        self.s_price_buy.setSingleStep(500)

        btn_add = QPushButton("+ Tambah Item")
        btn_add.clicked.connect(self._s_add)

        item_row.addWidget(QLabel("Barcode:"))
        item_row.addWidget(self.s_barcode)
        item_row.addWidget(QLabel("Qty:"))
        item_row.addWidget(self.s_qty)
        item_row.addWidget(QLabel("Harga Beli:"))
        item_row.addWidget(self.s_price_buy)
        item_row.addWidget(btn_add)
        layout.addLayout(item_row)

        self.s_items: list[dict] = []
        self.s_table = QTableWidget(0, 4)
        self.s_table.setHorizontalHeaderLabels(["Produk", "Qty", "Harga Beli", ""])
        self.s_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.s_table)

        btn_save = QPushButton("💾 Simpan Penerimaan Barang")
        btn_save.setObjectName("btnPrimary")
        btn_save.clicked.connect(self._s_save)
        layout.addWidget(btn_save)

        self._s_product = None
        return widget

    def _s_lookup(self):
        barcode = self.s_barcode.text().strip()
        p = self.product_model.get_by_barcode(barcode)
        if p:
            self._s_product = p
            self.s_price_buy.setValue(p["price_buy"])
        else:
            self._s_product = None
            QMessageBox.warning(self, "Produk", f"Barcode '{barcode}' tidak ditemukan.")
            self.s_barcode.clear()

    def _s_add(self):
        if not self._s_product:
            QMessageBox.warning(self, "Item", "Scan barcode terlebih dahulu.")
            return
        self.s_items.append({
            "product_id": self._s_product["id"],
            "name": self._s_product["name"],
            "qty": self.s_qty.value(),
            "price_buy": self.s_price_buy.value(),
        })
        self._s_refresh()
        self.s_barcode.clear()
        self._s_product = None

    def _s_refresh(self):
        self.s_table.setRowCount(len(self.s_items))
        for row, item in enumerate(self.s_items):
            self.s_table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.s_table.setItem(row, 1, QTableWidgetItem(str(item["qty"])))
            self.s_table.setItem(row, 2, QTableWidgetItem(format_rupiah(item["price_buy"])))
            del_btn = QPushButton("🗑")
            del_btn.clicked.connect(lambda _, r=row: self._s_remove(r))
            self.s_table.setCellWidget(row, 3, del_btn)

    def _s_remove(self, row: int):
        if 0 <= row < len(self.s_items):
            self.s_items.pop(row)
            self._s_refresh()

    def _s_save(self):
        if not self.s_items:
            QMessageBox.warning(self, "Simpan", "Tambahkan minimal satu item.")
            return
        self.stock_in_model.save_supplier_receipt(
            self.s_name.text().strip(),
            self.s_invoice.text().strip(),
            self.s_notes.text().strip(),
            self.s_items,
        )
        QMessageBox.information(
            self, "Berhasil", f"{len(self.s_items)} item stok diperbarui."
        )
        for w in (self.s_name, self.s_invoice, self.s_notes):
            w.clear()
        self.s_items.clear()
        self._s_refresh()

    # ── Riwayat ───────────────────────────────────────────
    def _history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Dari:"))
        self.h_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.h_from.setCalendarPopup(True)
        filter_row.addWidget(self.h_from)
        filter_row.addWidget(QLabel("Sampai:"))
        self.h_to = QDateEdit(QDate.currentDate())
        self.h_to.setCalendarPopup(True)
        filter_row.addWidget(self.h_to)
        btn = QPushButton("🔍 Filter")
        btn.clicked.connect(self._load_history)
        filter_row.addWidget(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.h_table = QTableWidget(0, 5)
        self.h_table.setHorizontalHeaderLabels(
            ["Tanggal", "Supplier", "No. Faktur", "Jml Item", "Catatan"]
        )
        self.h_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.h_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.h_table)

        self._load_history()
        return widget

    def _load_history(self):
        date_from = self.h_from.date().toString("yyyy-MM-dd")
        date_to = self.h_to.date().toString("yyyy-MM-dd")
        history = self.stock_in_model.get_history(date_from, date_to)
        self.h_table.setRowCount(len(history))
        for row, h in enumerate(history):
            self.h_table.setItem(row, 0, QTableWidgetItem(format_datetime(h["date"])))
            self.h_table.setItem(row, 1, QTableWidgetItem(h["supplier_name"] or "—"))
            self.h_table.setItem(row, 2, QTableWidgetItem(h["invoice_no"] or "—"))
            self.h_table.setItem(row, 3, QTableWidgetItem(str(h["item_count"])))
            self.h_table.setItem(row, 4, QTableWidgetItem(h["notes"] or ""))
