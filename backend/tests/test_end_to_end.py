import io
import time
import zipfile
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app, run_conversion_pipeline
from backend.app.job_manager import job_manager
from backend.tests.generate_samples import create_sample_math_pdf

client = TestClient(app)

def test_full_pipeline_success(tmp_path):
    # 1. Tạo file PDF test
    pdf_path = tmp_path / "de_toan_sample.pdf"
    create_sample_math_pdf(pdf_path)

    # 2. Upload file PDF
    with open(pdf_path, "rb") as f:
        response = client.post("/api/conversions", files={"file": ("de_toan_sample.pdf", f, "application/pdf")})
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    job = job_manager.get_job(job_id)
    assert job is not None

    # 3. Giả lập kết quả trả về từ Datalab
    markdown_content = (
        "# ĐỀ THI TOÁN HỌC\n\n"
        "Câu 1: Giải phương trình $$x^2 - 7x + 12 = 0$$\n\n"
        "Câu 2: Rút gọn biểu thức $$A = \\frac{\\sqrt{x}-1}{\\sqrt{x}+1}$$\n\n"
        "Câu 3: Tính đạo hàm hàm số $y = \\sin(2x) + \\cos(3x)$.\n"
    )

    def mock_convert_pdf(pdf_file, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        md_file = out_dir / "converted.md"
        md_file.write_text(markdown_content, encoding="utf-8")
        return True, md_file, ""

    # Chạy pipeline với mock datalab convert
    with patch("backend.app.main.datalab_service.convert_pdf_to_markdown", side_effect=mock_convert_pdf), \
         patch("backend.app.main.datalab_service.check_configuration", return_value=(True, "")):
        import asyncio
        asyncio.run(run_conversion_pipeline(job_id))

    # 4. Kiểm tra trạng thái hoàn thành
    status_resp = client.get(f"/api/conversions/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "completed"
    assert status_data["completed"] is True
    assert status_data["message"] == "Chuyển đổi hoàn tất"

    # 5. Tải file Word về và xác thực chất lượng kỹ thuật
    dl_resp = client.get(f"/api/conversions/{job_id}/download")
    assert dl_resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in dl_resp.headers["content-type"]
    
    # Đọc nội dung docx tải về
    docx_bytes = io.BytesIO(dl_resp.content)
    with zipfile.ZipFile(docx_bytes, "r") as z:
        assert "word/document.xml" in z.namelist()
        xml_content = z.read("word/document.xml").decode("utf-8")
        # Kiểm tra native OMML math equations
        assert "<m:oMath>" in xml_content or "<m:oMath " in xml_content
        assert "<m:f>" in xml_content or "<m:f " in xml_content

def test_pipeline_missing_api_key(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    create_sample_math_pdf(pdf_path)

    with open(pdf_path, "rb") as f:
        response = client.post("/api/conversions", files={"file": ("test.pdf", f, "application/pdf")})
    job_id = response.json()["job_id"]

    # Giả lập chưa có API key
    with patch("backend.app.main.datalab_service.check_configuration", return_value=(False, "Chưa có API key")):
        import asyncio
        asyncio.run(run_conversion_pipeline(job_id))

    status_resp = client.get(f"/api/conversions/{job_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "failed"
    assert "DATALAB_API_KEY" in status_resp.json()["error"]

