from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QLabel, QPushButton, QHeaderView, QDialog, QMessageBox,
    QDialogButtonBox, QFormLayout, QDoubleSpinBox, QInputDialog,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from models.product import ProductModel
from models.transaction import TransactionModel
from utils.printer import ReceiptPrinter
from utils.formatter import format_rupiah


class PaymentDialog(QDialog):
    def __init__(self, total: float, parent=None):
        super().__init__(parent)
        self.total = total
        self.setWindowTitle("Pembayaran")
        self.setMinimumWidth(320)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        total_label = QLabel(format_rupiah(self.total))
        total_label.setObjectName("cartTotalLabel")
        layout.addRow("Total:", total_label)

        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, self.total)
        self.discount_spin.setDecimals(0)
        self.discount_spin.setSingleStep(1000)
        self.discount_spin.valueChanged.connect(self._update)
        layout.addRow("Diskon (Rp):", self.discount_spin)

        self.payment_spin = QDoubleSpinBox()
        self.payment_spin.setRange(0, 99_999_999)
        self.payment_spin.setDecimals(0)
        self.payment_spin.setSingleStep(1000)
        self.payment_spin.setValue(self.total)
        self.payment_spin.valueChanged.connect(self._update)
        layout.addRow("Bayar (Rp):", self.payment_spin)

        self.change_label = QLabel("Rp 0")
        self.change_label.setObjectName("statValue")
        layout.addRow("Kembalian:", self.change_label)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addRow(self._buttons)
        self._update()

    def _update(self):
        disc = self.discount_spin.value()
        pay = self.payment_spin.value()
        final_total = self.total - disc
        change = pay - final_total
        self.change_label.setText(format_rupiah(max(0, change)))
        ok = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok:
            ok.setEnabled(pay >= final_total and final_total > 0)

    def _on_accept(self):
        disc = self.discount_spin.value()
        pay = self.payment_spin.value()
        if pay < (self.total - disc):
            QMessageBox.warning(self, "Kurang", "Nominal bayar kurang dari total.")
            return
        self.accept()

    def get_values(self) -> tuple[float, float, float]:
        disc = self.discount_spin.value()
        pay = self.payment_spin.value()
        return pay, disc, pay - (self.total - disc)


class KasirView(QWidget):
    COLS = ["No", "Produk", "Qty", "Harga Satuan", "Subtotal", ""]

    def __init__(self, conn, config: dict):
        super().__init__()
        self.conn = conn
        self.config = config
        self.product_model = ProductModel(conn)
        self.transaction_model = TransactionModel(conn)
        self.printer = ReceiptPrinter(config.get("printer", {}))
        self.cart: list[dict] = []
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Barcode input
        scan_row = QHBoxLayout()
        scan_row.addWidget(QLabel("📷 Scan / Barcode:"))
        self.scan_input = QLineEdit()
        self.scan_input.setObjectName("scanInput")
        self.scan_input.setPlaceholderText("Scan barcode atau ketik lalu Enter...")
        self.scan_input.returnPressed.connect(self._on_scan)
        scan_row.addWidget(self.scan_input)
        layout.addLayout(scan_row)

        # Notification label
        self.notif_label = QLabel("")
        self.notif_label.setObjectName("notifLabel")
        layout.addWidget(self.notif_label)

        # Cart table
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(5, 44)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        # Total row
        total_row = QHBoxLayout()
        self.count_label = QLabel("0 item")
        self.total_label = QLabel("TOTAL: Rp 0")
        self.total_label.setObjectName("cartTotalLabel")
        total_row.addWidget(self.count_label)
        total_row.addStretch()
        total_row.addWidget(self.total_label)
        layout.addLayout(total_row)

        # Action buttons
        btn_row = QHBoxLayout()
        self.btn_bayar = QPushButton("💵  BAYAR  [F1]")
        self.btn_bayar.setObjectName("btnBayar")
        self.btn_bayar.clicked.connect(self._on_bayar)

        self.btn_batal = QPushButton("✕  BATAL  [F2]")
        self.btn_batal.setObjectName("btnBatal")
        self.btn_batal.clicked.connect(self._on_batal)

        btn_row.addWidget(self.btn_bayar, 3)
        btn_row.addWidget(self.btn_batal, 1)
        layout.addLayout(btn_row)

        self._refocus()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F1"), self, self._on_bayar)
        QShortcut(QKeySequence("F2"), self, self._on_batal)

    def _refocus(self):
        self.scan_input.setFocus()

    def _on_scan(self):
        barcode = self.scan_input.text().strip()
        self.scan_input.clear()
        if not barcode:
            return
        product = self.product_model.get_by_barcode(barcode)
        if not product:
            self._notify(f"⚠ Produk '{barcode}' tidak ditemukan.", error=True)
            return
        self._add_to_cart(product)
        self._notify(f"✓ {product['name']} ditambahkan.", error=False)

    def _add_to_cart(self, product: dict):
        for item in self.cart:
            if item["product_id"] == product["id"]:
                item["qty"] += 1
                item["subtotal"] = item["qty"] * item["price_sell"]
                self._refresh()
                return
        self.cart.append({
            "product_id": product["id"],
            "name": product["name"],
            "qty": 1,
            "price_sell": product["price_sell"],
            "subtotal": product["price_sell"],
            "unit": product["unit"],
        })
        self._refresh()

    def _refresh(self):
        self.table.setRowCount(len(self.cart))
        for row, item in enumerate(self.cart):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(item["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(item["qty"])))
            self.table.setItem(row, 3, QTableWidgetItem(format_rupiah(item["price_sell"])))
            self.table.setItem(row, 4, QTableWidgetItem(format_rupiah(item["subtotal"])))
            del_btn = QPushButton("🗑")
            del_btn.clicked.connect(lambda _, r=row: self._remove(r))
            self.table.setCellWidget(row, 5, del_btn)

        total = sum(i["subtotal"] for i in self.cart)
        count = sum(i["qty"] for i in self.cart)
        self.total_label.setText(f"TOTAL: {format_rupiah(total)}")
        self.count_label.setText(f"{count} item")

    def _remove(self, row: int):
        if 0 <= row < len(self.cart):
            self.cart.pop(row)
            self._refresh()

    def _on_double_click(self, row: int, col: int):
        if col == 2 and row < len(self.cart):
            item = self.cart[row]
            qty, ok = QInputDialog.getInt(
                self, "Ubah Qty", f"Qty untuk {item['name']}:", item["qty"], 0, 9999
            )
            if ok:
                if qty == 0:
                    self._remove(row)
                else:
                    item["qty"] = qty
                    item["subtotal"] = qty * item["price_sell"]
                    self._refresh()

    def _on_bayar(self):
        if not self.cart:
            self._notify("Keranjang kosong.", error=True)
            return
        total = sum(i["subtotal"] for i in self.cart)
        dlg = PaymentDialog(total, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            payment, discount, change = dlg.get_values()
            tid = self.transaction_model.save(
                self.cart, payment=payment, discount=discount
            )
            tx = self.transaction_model.get_by_id(tid)
            self.printer.print_receipt(tx, self.cart, self.config)
            self.cart.clear()
            self._refresh()
            self._notify(
                f"✓ Transaksi #{tid:04d} selesai. Kembalian: {format_rupiah(change)}",
                error=False,
                duration=5000,
            )
        self._refocus()

    def _on_batal(self):
        if not self.cart:
            return
        reply = QMessageBox.question(
            self, "Batal", "Kosongkan keranjang?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cart.clear()
            self._refresh()
            self._notify("Keranjang dikosongkan.")
        self._refocus()

    def _notify(self, msg: str, error: bool = False, duration: int = 3000):
        self.notif_label.setText(msg)
        self.notif_label.setProperty("error", str(error).lower())
        self.notif_label.style().unpolish(self.notif_label)
        self.notif_label.style().polish(self.notif_label)
        QTimer.singleShot(duration, lambda: self.notif_label.setText(""))
