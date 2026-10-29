import logging
import urllib.parse
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse

from .config import settings
from .pdf_validator import sanitize_filename, validate_pdf_bytes
from .datalab_service import check_api_configuration, convert_pdf_bytes_to_markdown
from .docx_generator import generate_docx_from_markdown_and_images, _ensure_pandoc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mathpdf_api")

app = FastAPI(
    title="MathPDF API",
    description="Chuyển đổi đề Toán PDF sang Word (.docx)",
    version="2.0.0",
    docs_url=None,   # Ẩn /docs trên production
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Endpoint 1: Kiểm tra trạng thái hệ thống
# ---------------------------------------------------------------------------
@app.get("/api/status")
async def get_status():
    """Trạng thái cấu hình — không để lộ API key."""
    pandoc_ok = _ensure_pandoc()
    api_ok, _ = check_api_configuration()
    return {
        "status": "ready",
        "api_key_configured": api_ok,
        "convert_mode": settings.DATALAB_CONVERT_MODE,
        "max_upload_mb": settings.MAX_UPLOAD_MB,
        "pandoc_available": pandoc_ok,
    }

# ---------------------------------------------------------------------------
# Endpoint 2: Chuyển đổi PDF → DOCX (xử lý đồng bộ, trả file về luôn)
# ---------------------------------------------------------------------------
@app.post("/api/convert")
async def convert_pdf(file: UploadFile = File(...)):
    """
    Nhận PDF, chuyển sang DOCX và trả file về trong cùng một request.
    Không cần polling, không cần job ID, không cần storage.
    """
    # --- Kiểm tra cấu hình ---
    api_ok, api_err = check_api_configuration()
    if not api_ok:
        logger.error(f"API key chưa cấu hình: {api_err}")
        raise HTTPException(
            status_code=503,
            detail="Dịch vụ chuyển đổi chưa sẵn sàng. Vui lòng liên hệ quản trị viên."
        )

    # --- Đọc và validate file ---
    original_name = sanitize_filename(file.filename or "tailieu.pdf")

    try:
        pdf_bytes = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Không thể đọc dữ liệu file tải lên.")

    is_valid, val_err, page_count = validate_pdf_bytes(pdf_bytes, settings.MAX_UPLOAD_MB)
    if not is_valid:
        raise HTTPException(status_code=400, detail=val_err)

    logger.info(f"Nhận file: {original_name} ({len(pdf_bytes)} bytes, {page_count} trang)")

    # --- Gọi Datalab Convert API (chạy trong worker thread để không xung đột event loop) ---
    import asyncio
    success, markdown_text, images, convert_err = await asyncio.to_thread(
        convert_pdf_bytes_to_markdown, pdf_bytes, original_name
    )
    if not success or not markdown_text:
        logger.error(f"Datalab convert thất bại: {convert_err}")
        # Thông báo thân thiện, an toàn cho người dùng cuối, không để lộ thông tin kỹ thuật nội bộ
        if "credit" in convert_err.lower():
            detail = "Dịch vụ tạm thời gián đoạn hạn mức. Vui lòng liên hệ quản trị viên."
        elif "thời gian" in convert_err.lower() or "timeout" in convert_err.lower():
            detail = "Tài liệu quá dài hoặc phức tạp. Vui lòng thử với file có ít trang hơn."
        else:
            detail = "Không thể chuyển đổi tài liệu này. Vui lòng thử lại bằng file PDF khác."
        raise HTTPException(status_code=422, detail=detail)

    # --- Tạo DOCX (chạy trong worker thread) ---
    out_stem = Path(original_name).stem
    gen_ok, docx_bytes, gen_err = await asyncio.to_thread(
        generate_docx_from_markdown_and_images,
        markdown_text, images, f"{out_stem}.docx"
    )
    if not gen_ok or not docx_bytes:
        logger.error(f"Tạo DOCX thất bại: {gen_err}")
        raise HTTPException(
            status_code=500,
            detail="Không thể tạo file Word từ kết quả nhận diện. Vui lòng thử lại."
        )

    # --- Trả file DOCX về trực tiếp ---
    out_filename = f"{out_stem}.docx"
    encoded_name = urllib.parse.quote(out_filename)
    logger.info(f"Trả về DOCX: {out_filename} ({len(docx_bytes)} bytes)")

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{encoded_name}"; '
                f"filename*=UTF-8''{encoded_name}"
            ),
            "Content-Length": str(len(docx_bytes)),
        },
    )

# ---------------------------------------------------------------------------
# Phục vụ frontend tĩnh (nếu đã build)
# ---------------------------------------------------------------------------
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    _assets = _frontend_dist / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        target = _frontend_dist / full_path
        if target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(_frontend_dist / "index.html"))
