import io
import zipfile
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def _make_valid_pdf():
    import pymupdf
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 72), "De thi Toan: x^2 - 5x + 6 = 0", fontsize=12)
    buf = doc.tobytes()
    doc.close()
    return buf

# ---------------------------------------------------------------------------
# /api/status
# ---------------------------------------------------------------------------
def test_system_status():
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert "api_key_configured" in data
    assert "max_upload_mb" in data
    assert data["pandoc_available"] is True

# ---------------------------------------------------------------------------
# /api/convert — kiểm tra validate
# ---------------------------------------------------------------------------
def test_convert_empty_file():
    r = client.post("/api/convert", files={"file": ("empty.pdf", b"", "application/pdf")})
    assert r.status_code == 400
    assert "rỗng" in r.json()["detail"]

def test_convert_invalid_format():
    r = client.post("/api/convert", files={"file": ("fake.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 400

def test_convert_no_api_key():
    """Khi chưa có API key, server trả 503."""
    with patch("backend.app.main.check_api_configuration", return_value=(False, "no key")):
        pdf = _make_valid_pdf()
        r = client.post("/api/convert", files={"file": ("test.pdf", pdf, "application/pdf")})
    assert r.status_code == 503

# ---------------------------------------------------------------------------
# /api/convert — pipeline đầy đủ với mock Datalab
# ---------------------------------------------------------------------------
MOCK_MARKDOWN = r"""# ĐỀ THI TOÁN

Câu 1: Giải $$x^2 - 7x + 12 = 0$$

Câu 2: Rút gọn $A = \frac{\sqrt{x}-1}{\sqrt{x}+1}$
"""

def test_convert_full_pipeline_success():
    """Test pipeline đầy đủ: PDF upload → mock Datalab → DOCX trả về."""
    pdf = _make_valid_pdf()

    with patch("backend.app.main.check_api_configuration", return_value=(True, "")), \
         patch("backend.app.main.convert_pdf_bytes_to_markdown",
               return_value=(True, MOCK_MARKDOWN, [], "")):

        r = client.post("/api/convert", files={"file": ("de_toan.pdf", pdf, "application/pdf")})

    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "attachment" in r.headers.get("content-disposition", "")

    # Kiểm tra DOCX nhận về hợp lệ và có Word Equation
    docx_bytes = r.content
    assert docx_bytes[:4] == b"PK\x03\x04"
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        assert "word/document.xml" in z.namelist()
        xml = z.read("word/document.xml").decode("utf-8")
        assert "<m:oMath>" in xml or "<m:oMath " in xml

def test_convert_datalab_error_returns_422():
    """Khi Datalab thất bại, API trả 422 với thông báo an toàn, không lộ API key hoặc chi tiết kỹ thuật."""
    pdf = _make_valid_pdf()

    with patch("backend.app.main.check_api_configuration", return_value=(True, "")), \
         patch("backend.app.main.convert_pdf_bytes_to_markdown",
               return_value=(False, None, [], "Lỗi xác thực API key")):

        r = client.post("/api/convert", files={"file": ("test.pdf", pdf, "application/pdf")})

    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "API key" not in detail
    assert "Không thể chuyển đổi" in detail
