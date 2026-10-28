import asyncio
import logging
import urllib.parse
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import settings
from .pdf_validator import sanitize_filename, validate_pdf_file
from .job_manager import job_manager, JobInfo
from .datalab_service import datalab_service
from .docx_generator import generate_docx_from_markdown, ensure_pandoc_available

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mathpdf_api")

app = FastAPI(
    title="MathPDF API",
    description="Hệ thống chuyển đổi đề Toán PDF sang Word (.docx)",
    version="1.0.0"
)

# Cấu hình CORS để frontend React giao tiếp thuận tiện
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def run_conversion_pipeline(job_id: str):
    """
    Quy trình xử lý chuyển đổi tài liệu PDF sang Word chạy trong nền:
    1. Kiểm tra cấu hình và file đầu vào
    2. Gọi Datalab Convert API
    3. Tạo file Word (.docx) chứa công thức toán và hình ảnh
    4. Kiểm tra chất lượng và tính hợp lệ của file DOCX
    5. Cập nhật trạng thái hoàn thành
    """
    job = job_manager.get_job(job_id)
    if not job or not job.pdf_path or not job.job_dir:
        return

    try:
        # Bước 1: Đang tải và kiểm tra
        job_manager.update_status(job_id, "validating", "Đang kiểm tra tài liệu...")
        is_valid, val_err, page_count = validate_pdf_file(job.pdf_path)
        if not is_valid:
            job_manager.update_status(job_id, "failed", "Kiểm tra tài liệu thất bại", error=val_err)
            return

        job.page_count = page_count

        # Kiểm tra API key đã sẵn sàng chưa
        is_configured, config_err = datalab_service.check_configuration()
        if not is_configured:
            job_manager.update_status(
                job_id, 
                "failed", 
                "Hệ thống chưa sẵn sàng", 
                error="Hệ thống chưa được thiết lập API key Datalab. Vui lòng cấu hình DATALAB_API_KEY trong file .env."
            )
            return

        # Bước 2: Đang chuyển đổi với Datalab
        job_manager.update_status(job_id, "converting", "Đang chuyển đổi...")
        extracted_dir = job.job_dir / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        # Chạy convert đồng bộ trong threadpool để không block event loop
        loop = asyncio.get_event_loop()
        success, md_path, convert_err = await loop.run_in_executor(
            None,
            datalab_service.convert_pdf_to_markdown,
            job.pdf_path,
            extracted_dir
        )

        if not success or not md_path:
            logger.error(f"Datalab conversion failed for job {job_id}: {convert_err}")
            # Thông báo an toàn cho người dùng
            user_error = "Không thể chuyển đổi tài liệu này. Vui lòng thử lại bằng file PDF khác."
            if "credit" in convert_err.lower():
                user_error = "Hạn mức dịch vụ nhận diện tạm thời gián đoạn. Vui lòng liên hệ quản trị viên."
            elif "xác thực" in convert_err.lower():
                user_error = "Lỗi xác thực dịch vụ. Vui lòng kiểm tra lại cấu hình API key."
            
            job_manager.update_status(job_id, "failed", "Chuyển đổi thất bại", error=user_error)
            return

        # Bước 3: Đang chuẩn bị file Word
        job_manager.update_status(job_id, "generating_docx", "Đang chuẩn bị file Word...")
        
        gen_success, gen_err = await loop.run_in_executor(
            None,
            generate_docx_from_markdown,
            md_path,
            job.docx_path,
            extracted_dir
        )

        if not gen_success:
            logger.error(f"DOCX generation failed for job {job_id}: {gen_err}")
            job_manager.update_status(
                job_id, 
                "failed", 
                "Tạo file Word thất bại", 
                error="Không thể tạo file Word từ kết quả nhận diện. Vui lòng thử lại."
            )
            return

        # Bước 4: Thành công
        job_manager.update_status(job_id, "completed", "Chuyển đổi hoàn tất")
        logger.info(f"Job {job_id} hoàn thành thành công.")

    except Exception as e:
        logger.exception(f"Lỗi không mong muốn trong job {job_id}: {e}")
        job_manager.update_status(
            job_id, 
            "failed", 
            "Lỗi xử lý", 
            error="Không thể chuyển đổi tài liệu này. Vui lòng thử lại bằng file PDF khác."
        )

@app.get("/api/system/status")
async def get_system_status():
    """Kiểm tra trạng thái cấu hình hệ thống (không để lộ API key)."""
    pandoc_ok = ensure_pandoc_available()
    return {
        "status": "ready",
        "api_key_configured": settings.is_api_key_configured,
        "convert_mode": settings.DATALAB_CONVERT_MODE,
        "max_upload_mb": settings.MAX_UPLOAD_MB,
        "pandoc_available": pandoc_ok
    }

@app.post("/api/conversions")
async def create_conversion(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Tiếp nhận file PDF, xác thực sơ bộ và khởi chạy tiến trình chuyển đổi."""
    # Dọn dẹp các job cũ đã quá hạn
    job_manager.cleanup_expired_jobs()

    original_name = sanitize_filename(file.filename or "tailieu.pdf")
    
    # Đọc nội dung file
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Không thể đọc dữ liệu file tải lên.")

    file_size = len(content)
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

    if file_size == 0:
        raise HTTPException(status_code=400, detail="File tải lên bị rỗng (0 bytes).")

    if file_size > max_bytes:
        raise HTTPException(
            status_code=400, 
            detail=f"Dung lượng file vượt quá giới hạn {settings.MAX_UPLOAD_MB} MB."
        )

    # Kiểm tra nhanh magic bytes
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Định dạng file không hợp lệ. Chỉ chấp nhận file PDF.")

    # Tạo job
    job = job_manager.create_job(original_filename=original_name, file_size=file_size)

    # Lưu file PDF vào thư mục riêng của job
    try:
        with open(job.pdf_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Lỗi ghi file tải lên: {e}")
        raise HTTPException(status_code=500, detail="Không thể lưu trữ file tạm trên máy chủ.")

    # Khởi chạy quy trình chuyển đổi trong background task
    background_tasks.add_task(run_conversion_pipeline, job.job_id)

    return JSONResponse(status_code=202, content=job.to_dict())

@app.get("/api/conversions/{job_id}")
async def get_conversion_status(job_id: str):
    """Kiểm tra trạng thái của một công việc chuyển đổi."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu chuyển đổi này hoặc file đã hết hạn.")
    return job.to_dict()

@app.get("/api/conversions/{job_id}/download")
async def download_conversion_result(job_id: str):
    """Tải xuống file Word (.docx) sau khi chuyển đổi thành công."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu chuyển đổi này.")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Tài liệu chưa được chuyển đổi xong hoặc chuyển đổi thất bại.")

    if not job.docx_path or not job.docx_path.exists():
        raise HTTPException(status_code=404, detail="File kết quả không tồn tại trên hệ thống.")

    # Đặt tên file đầu ra dựa trên tên file gốc (.pdf -> .docx)
    out_filename = Path(job.original_filename).stem + ".docx"
    encoded_filename = urllib.parse.quote(out_filename)

    return FileResponse(
        path=str(job.docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=\"{encoded_filename}\"; filename*=UTF-8''{encoded_filename}"
        }
    )

# Phục vụ Frontend tĩnh nếu đã được build
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    # Mount assets
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Tránh chặn các API endpoint
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API route not found")
        
        target_file = frontend_dist / full_path
        if target_file.is_file():
            return FileResponse(str(target_file))
        return FileResponse(str(frontend_dist / "index.html"))

