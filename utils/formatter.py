from datetime import datetime


def format_rupiah(amount: float) -> str:
    """Format angka sebagai Rupiah: Rp 15.000"""
    return "Rp {:,.0f}".format(amount).replace(",", ".")


def format_datetime(dt_str: str) -> str:
    """'YYYY-MM-DD HH:MM:SS' -> 'DD/MM/YYYY HH:MM'"""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%d/%m/%Y %H:%M")


def format_date(dt_str: str) -> str:
    """'YYYY-MM-DD HH:MM:SS' -> 'DD/MM/YYYY'"""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%d/%m/%Y")
