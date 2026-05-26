from utils.formatter import format_rupiah, format_datetime, format_date


def test_format_rupiah_thousands():
    assert format_rupiah(15000) == "Rp 15.000"


def test_format_rupiah_millions():
    assert format_rupiah(1500000) == "Rp 1.500.000"


def test_format_rupiah_zero():
    assert format_rupiah(0) == "Rp 0"


def test_format_rupiah_with_float():
    assert format_rupiah(15000.0) == "Rp 15.000"


def test_format_datetime():
    assert format_datetime("2026-05-26 14:32:00") == "26/05/2026 14:32"


def test_format_date():
    assert format_date("2026-05-26 14:32:00") == "26/05/2026"
