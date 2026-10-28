import pytest
from pathlib import Path
from backend.app.pdf_validator import validate_pdf_file, sanitize_filename

@pytest.fixture
def test_files_dir(tmp_path):
    d = tmp_path / "pdf_tests"
    d.mkdir()
    return d

def test_sanitize_filename():
    assert sanitize_filename("test.pdf") == "test.pdf"
    assert sanitize_filename("../../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("bai tap toan: 12.pdf") == "bai tap toan_ 12.pdf"
    assert sanitize_filename("file_khong_duoi") == "file_khong_duoi.pdf"
    assert sanitize_filename("") == "document.pdf"

def test_validate_valid_pdf(tmp_path):
    from backend.tests.generate_samples import create_sample_math_pdf
    pdf_path = tmp_path / "valid.pdf"
    create_sample_math_pdf(pdf_path)
    
    is_valid, err, page_count = validate_pdf_file(pdf_path)
    assert is_valid is True
    assert err == ""
    assert page_count == 1

def test_validate_empty_file(tmp_path):
    empty_path = tmp_path / "empty.pdf"
    empty_path.write_bytes(b"")
    
    is_valid, err, count = validate_pdf_file(empty_path)
    assert is_valid is False
    assert "rỗng" in err

def test_validate_fake_pdf(tmp_path):
    fake_path = tmp_path / "fake.pdf"
    fake_path.write_text("Day la file text binh thuong khong phai PDF")
    
    is_valid, err, count = validate_pdf_file(fake_path)
    assert is_valid is False
    assert "Định dạng file không hợp lệ" in err

def test_validate_corrupt_pdf(tmp_path):
    corrupt_path = tmp_path / "corrupt.pdf"
    corrupt_path.write_bytes(b"%PDF-1.4 header here but corrupted rest of file")
    
    is_valid, err, count = validate_pdf_file(corrupt_path)
    assert is_valid is False
    assert "bị hỏng" in err

