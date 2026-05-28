from pathlib import Path
from datetime import datetime
from utils.formatter import format_rupiah, format_datetime


class ReceiptPrinter:
    LINE_WIDTH = 32

    def __init__(self, printer_config: dict):
        self.config = printer_config
        self.printer = None
        self._connect()

    def _connect(self) -> bool:
        try:
            ptype = self.config.get("type", "")
            if ptype == "usb":
                from escpos.printer import Usb
                vid = int(self.config["vendor_id"], 16)
                pid = int(self.config["product_id"], 16)
                self.printer = Usb(vid, pid)
            elif ptype == "serial":
                from escpos.printer import Serial
                self.printer = Serial(self.config["port"])
            elif ptype == "network":
                from escpos.printer import Network
                self.printer = Network(self.config["ip"])
            return True
        except Exception:
            self.printer = None
            return False

    def print_receipt(self, transaction: dict, items: list[dict],
                      store: dict) -> bool:
        """Returns True jika berhasil cetak, False jika disimpan ke file."""
        text = self._format_receipt_text(transaction, items, store)
        if self.printer:
            try:
                self.printer.text(text)
                self.printer.cut()
                return True
            except Exception:
                pass
        self._save_to_file(text, transaction["id"])
        return False

    def _format_receipt_text(self, transaction: dict, items: list[dict],
                              store: dict) -> str:
        w = self.LINE_WIDTH
        sep = "=" * w
        thin = "-" * w

        lines = [
            sep,
            store.get("store_name", "TOKO").center(w),
            store.get("store_address", "").center(w),
            store.get("store_phone", "").center(w),
            sep,
            f"{format_datetime(transaction['date'])}  No: #{transaction['id']:04d}",
            thin,
        ]

        for item in items:
            lines.append(item["name"])
            qty_line = (f"  {item['qty']} {item['unit']} x "
                        f"{format_rupiah(item['price_sell'])}")
            sub_str = format_rupiah(item["subtotal"])
            pad = w - len(qty_line) - len(sub_str)
            lines.append(qty_line + " " * max(1, pad) + sub_str)

        lines.append(thin)

        if transaction.get("discount", 0) > 0:
            d = format_rupiah(transaction["discount"])
            lines.append(f"{'DISKON':<{w - len(d)}}{d}")

        total_str = format_rupiah(transaction["total"])
        lines.append(f"{'TOTAL':<{w - len(total_str)}}{total_str}")

        bayar_str = format_rupiah(transaction["payment"])
        lines.append(f"{'BAYAR':<{w - len(bayar_str)}}{bayar_str}")

        kembali_str = format_rupiah(transaction["change"])
        lines.append(f"{'KEMBALI':<{w - len(kembali_str)}}{kembali_str}")

        lines += [sep, "Terima kasih!".center(w), sep, "\n\n\n"]
        return "\n".join(lines)

    def _save_to_file(self, text: str, transaction_id: int) -> None:
        receipts_dir = Path("receipts")
        receipts_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = receipts_dir / f"struk_{transaction_id:04d}_{ts}.txt"
        path.write_text(text, encoding="utf-8")
