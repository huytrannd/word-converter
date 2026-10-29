import pytest
from backend.app.pdf_validator import sanitize_filename, validate_pdf_bytes

def test_sanitize_filename():
    assert sanitize_filename("test.pdf") == "test.pdf"
    assert sanitize_filename("../../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("bai tap toan: 12.pdf") == "bai tap toan_ 12.pdf"
    assert sanitize_filename("file_khong_duoi") == "file_khong_duoi.pdf"
    assert sanitize_filename("") == "document.pdf"

def _make_valid_pdf_bytes():
    """Tạo PDF bytes hợp lệ tối thiểu bằng PyMuPDF."""
    import pymupdf
    doc = pymupdf.open()
    doc.new_page()
    doc.new_page().insert_text((50, 72), "Cau 1: x^2 - 1 = 0", fontsize=12)
    buf = doc.tobytes()
    doc.close()
    return buf

def test_validate_valid_pdf():
    pdf = _make_valid_pdf_bytes()
    is_valid, err, pages = validate_pdf_bytes(pdf, max_mb=20)
    assert is_valid is True
    assert err == ""
    assert pages >= 1

def test_validate_empty_bytes():
    is_valid, err, pages = validate_pdf_bytes(b"", max_mb=20)
    assert is_valid is False
    assert "rỗng" in err

def test_validate_too_large():
    big_data = b"%PDF-1.4" + b"x" * (21 * 1024 * 1024)
    is_valid, err, pages = validate_pdf_bytes(big_data, max_mb=20)
    assert is_valid is False
    assert "giới hạn" in err or "vượt quá" in err

def test_validate_fake_pdf():
    is_valid, err, pages = validate_pdf_bytes(b"This is not a PDF at all", max_mb=20)
    assert is_valid is False

def test_validate_corrupt_pdf():
    corrupt = b"%PDF-1.4 corrupt data that cannot be parsed as pdf"
    is_valid, err, pages = validate_pdf_bytes(corrupt, max_mb=20)
    assert is_valid is False
    assert "hỏng" in err
