import csv
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QTabWidget, QDateEdit, QHeaderView,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from models.transaction import TransactionModel
from models.product import ProductModel
from utils.formatter import format_rupiah


class LaporanView(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.tx_model = TransactionModel(conn)
        self.product_model = ProductModel(conn)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._harian_tab(), "📅 Harian")
        self.tabs.addTab(self._periode_tab(), "📆 Periode")
        self.tabs.addTab(self._stok_tab(), "📦 Stok")
        self.tabs.addTab(self._per_produk_tab(), "🏆 Per Produk")
        self.tabs.currentChanged.connect(self._on_tab)
        layout.addWidget(self.tabs)

    def _on_tab(self, idx: int):
        if idx == 0:
            self._load_harian()
        elif idx == 2:
            self._load_stok()

    # ── Harian ───────────────────────────────────────────
    def _harian_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)

        self._h_labels: dict[str, QLabel] = {}
        for key, label in [
            ("count",    "Jumlah Transaksi"),
            ("total",    "Total Omzet"),
            ("profit",   "Estimasi Laba Kotor"),
            ("discount", "Total Diskon"),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            row.addStretch()
            val = QLabel("—")
            val.setObjectName("statValue")
            row.addWidget(val)
            layout.addLayout(row)
            self._h_labels[key] = val

        layout.addStretch()
        btn = QPushButton("📥 Ekspor CSV")
        btn.clicked.connect(self._export_harian)
        layout.addWidget(btn)

        self._load_harian()
        return widget

    def _load_harian(self):
        s = self.tx_model.get_today_summary()
        self._h_labels["count"].setText(str(s["count"]))
        self._h_labels["total"].setText(format_rupiah(s["total"]))
        self._h_labels["profit"].setText(format_rupiah(s["profit"]))
        self._h_labels["discount"].setText(format_rupiah(s["discount"]))

    def _export_harian(self):
        today = date.today().isoformat()
        s = self.tx_model.get_today_summary()
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan CSV", f"laporan_harian_{today}.csv", "CSV (*.csv)"
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([
                    ["Tanggal", "Transaksi", "Omzet", "Laba", "Diskon"],
                    [today, s["count"], s["total"], s["profit"], s["discount"]],
                ])
            QMessageBox.information(self, "Ekspor", f"Tersimpan:\n{path}")

    # ── Periode ───────────────────────────────────────────
    def _periode_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        fr = QHBoxLayout()
        fr.addWidget(QLabel("Dari:"))
        self.p_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.p_from.setCalendarPopup(True)
        fr.addWidget(self.p_from)
        fr.addWidget(QLabel("Sampai:"))
        self.p_to = QDateEdit(QDate.currentDate())
        self.p_to.setCalendarPopup(True)
        fr.addWidget(self.p_to)
        btn = QPushButton("🔍 Tampilkan")
        btn.clicked.connect(self._load_periode)
        fr.addWidget(btn)
        fr.addStretch()
        layout.addLayout(fr)

        self._fig = Figure(figsize=(6, 2.5), facecolor="#1e1e2e")
        self._canvas = FigureCanvasQTAgg(self._fig)
        layout.addWidget(self._canvas)

        self._p_table = QTableWidget(0, 3)
        self._p_table.setHorizontalHeaderLabels(["Tanggal", "Transaksi", "Omzet"])
        self._p_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._p_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._p_table)

        btn_exp = QPushButton("📥 Ekspor CSV")
        btn_exp.clicked.connect(self._export_periode)
        layout.addWidget(btn_exp)

        self._p_data: list[dict] = []
        return widget

    def _load_periode(self):
        df = self.p_from.date().toString("yyyy-MM-dd")
        dt = self.p_to.date().toString("yyyy-MM-dd")
        self._p_data = self.tx_model.get_daily_totals(df, dt)

        self._fig.clear()
        ax = self._fig.add_subplot(111)
        ax.set_facecolor("#16213e")
        self._fig.patch.set_facecolor("#1e1e2e")
        if self._p_data:
            ax.bar([d["day"] for d in self._p_data],
                   [d["total"] for d in self._p_data], color="#4ade80")
            ax.tick_params(colors="white", labelsize=7)
            ax.xaxis.set_tick_params(rotation=45)
            for sp in ax.spines.values():
                sp.set_edgecolor("#334155")
        else:
            ax.text(0.5, 0.5, "Tidak ada data", ha="center", va="center",
                    color="white", transform=ax.transAxes)
        self._canvas.draw()

        self._p_table.setRowCount(len(self._p_data))
        for row, d in enumerate(self._p_data):
            self._p_table.setItem(row, 0, QTableWidgetItem(d["day"]))
            self._p_table.setItem(row, 1, QTableWidgetItem(str(d["count"])))
            self._p_table.setItem(row, 2, QTableWidgetItem(format_rupiah(d["total"])))

    def _export_periode(self):
        if not self._p_data:
            QMessageBox.information(self, "Ekspor", "Klik 'Tampilkan' terlebih dahulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan CSV", "laporan_periode.csv", "CSV (*.csv)"
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Tanggal", "Transaksi", "Omzet"])
                for d in self._p_data:
                    w.writerow([d["day"], d["count"], d["total"]])
            QMessageBox.information(self, "Ekspor", f"Tersimpan:\n{path}")

    # ── Stok ─────────────────────────────────────────────
    def _stok_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._s_table = QTableWidget(0, 5)
        self._s_table.setHorizontalHeaderLabels(
            ["Barcode", "Nama Produk", "Stok", "Satuan", "Status"]
        )
        self._s_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._s_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._s_table)

        btn = QPushButton("📥 Ekspor CSV")
        btn.clicked.connect(self._export_stok)
        layout.addWidget(btn)

        self._s_data: list[dict] = []
        self._load_stok()
        return widget

    def _load_stok(self):
        self._s_data = self.product_model.get_all()
        self._s_table.setRowCount(len(self._s_data))
        LOW = 5
        for row, p in enumerate(self._s_data):
            status = "⚠ Hampir habis" if p["stock"] <= LOW else "OK"
            for col, val in enumerate(
                [p["barcode"], p["name"], str(p["stock"]), p["unit"], status]
            ):
                item = QTableWidgetItem(val)
                if p["stock"] <= LOW:
                    item.setForeground(QColor("#ef4444"))
                self._s_table.setItem(row, col, item)

    def _export_stok(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan CSV", "laporan_stok.csv", "CSV (*.csv)"
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Barcode", "Nama", "Stok", "Satuan", "Status"])
                for p in self._s_data:
                    w.writerow([p["barcode"], p["name"], p["stock"], p["unit"],
                                 "Hampir habis" if p["stock"] <= 5 else "OK"])
            QMessageBox.information(self, "Ekspor", f"Tersimpan:\n{path}")

    # ── Per Produk ────────────────────────────────────────
    def _per_produk_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        fr = QHBoxLayout()
        fr.addWidget(QLabel("Dari:"))
        self.pp_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.pp_from.setCalendarPopup(True)
        fr.addWidget(self.pp_from)
        fr.addWidget(QLabel("Sampai:"))
        self.pp_to = QDateEdit(QDate.currentDate())
        self.pp_to.setCalendarPopup(True)
        fr.addWidget(self.pp_to)
        btn = QPushButton("🔍 Tampilkan")
        btn.clicked.connect(self._load_per_produk)
        fr.addWidget(btn)
        fr.addStretch()
        layout.addLayout(fr)

        self._pp_table = QTableWidget(0, 5)
        self._pp_table.setHorizontalHeaderLabels(
            ["Nama Produk", "Satuan", "Qty Terjual", "Total Omzet", "Laba"]
        )
        self._pp_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._pp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._pp_table)

        btn_exp = QPushButton("📥 Ekspor CSV")
        btn_exp.clicked.connect(self._export_per_produk)
        layout.addWidget(btn_exp)

        self._pp_data: list[dict] = []
        return widget

    def _load_per_produk(self):
        df = self.pp_from.date().toString("yyyy-MM-dd")
        dt = self.pp_to.date().toString("yyyy-MM-dd")
        self._pp_data = self.tx_model.get_product_sales(df, dt)
        self._pp_table.setRowCount(len(self._pp_data))
        for row, s in enumerate(self._pp_data):
            for col, val in enumerate([
                s["name"], s["unit"], str(s["qty"]),
                format_rupiah(s["total"]), format_rupiah(s["profit"]),
            ]):
                self._pp_table.setItem(row, col, QTableWidgetItem(val))

    def _export_per_produk(self):
        if not self._pp_data:
            QMessageBox.information(self, "Ekspor", "Klik 'Tampilkan' terlebih dahulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan CSV", "laporan_per_produk.csv", "CSV (*.csv)"
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Nama Produk", "Satuan", "Qty Terjual", "Omzet", "Laba"])
                for s in self._pp_data:
                    w.writerow([s["name"], s["unit"], s["qty"],
                                 s["total"], s["profit"]])
            QMessageBox.information(self, "Ekspor", f"Tersimpan:\n{path}")
