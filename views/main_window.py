from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel,
)
from PyQt6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self, conn, config: dict):
        super().__init__()
        self.conn = conn
        self.config = config
        self.setWindowTitle(f"TopOneCashier — {config.get('store_name', 'Toko')}")
        self.setMinimumSize(1100, 650)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(170)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 16, 8, 8)
        sidebar_layout.setSpacing(4)

        logo = QLabel("TopOneCashier")
        logo.setObjectName("logoLabel")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(12)

        self.stack = QStackedWidget()
        self.nav_buttons: list[QPushButton] = []

        pages = [
            ("🛒  Kasir",      self._make_kasir),
            ("📦  Produk",     self._make_produk),
            ("📥  Stok Masuk", self._make_stok),
            ("📊  Laporan",    self._make_laporan),
        ]

        for i, (label, factory) in enumerate(pages):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("navButton")
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            self.stack.addWidget(factory())

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack)
        self._switch(0)

    def _switch(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _make_kasir(self):
        from views.kasir_view import KasirView
        return KasirView(self.conn, self.config)

    def _make_produk(self):
        from views.produk_view import ProdukView
        return ProdukView(self.conn)

    def _make_stok(self):
        from views.stok_view import StokView
        return StokView(self.conn)

    def _make_laporan(self):
        from views.laporan_view import LaporanView
        return LaporanView(self.conn)
