import io
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.job_manager import job_manager
from backend.tests.generate_samples import create_sample_math_pdf

client = TestClient(app)

def test_system_status():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "api_key_configured" in data
    assert "max_upload_mb" in data
    assert data["pandoc_available"] is True

def test_upload_invalid_file():
    # File text giả PDF
    files = {"file": ("test.pdf", io.BytesIO(b"not a real pdf content"), "application/pdf")}
    response = client.post("/api/conversions", files=files)
    assert response.status_code == 400
    assert "không hợp lệ" in response.json()["detail"]

def test_upload_empty_file():
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    response = client.post("/api/conversions", files=files)
    assert response.status_code == 400
    assert "rỗng" in response.json()["detail"]

def test_get_nonexistent_job():
    response = client.get("/api/conversions/non-existent-uuid")
    assert response.status_code == 404

def test_download_nonexistent_job():
    response = client.get("/api/conversions/non-existent-uuid/download")
    assert response.status_code == 404

def test_upload_valid_pdf_creates_job(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    create_sample_math_pdf(pdf_path)
    
    with open(pdf_path, "rb") as f:
        files = {"file": ("de_thi_toan.pdf", f, "application/pdf")}
        response = client.post("/api/conversions", files=files)
        
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["filename"] == "de_thi_toan.pdf"
    assert data["status"] in ("pending", "validating", "converting", "generating_docx", "failed", "completed")
    
    # Kiểm tra endpoint status của job vừa tạo
    status_resp = client.get(f"/api/conversions/{data['job_id']}")
    assert status_resp.status_code == 200
    assert status_resp.json()["job_id"] == data["job_id"]

