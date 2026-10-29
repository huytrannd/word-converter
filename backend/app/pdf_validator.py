import re
from pathlib import Path
from typing import Tuple
import io

def sanitize_filename(filename: str) -> str:
    """Làm sạch tên file, loại bỏ ký tự nguy hiểm và chống directory traversal."""
    if not filename:
        return "document.pdf"
    clean = Path(filename).name
    clean = re.sub(r'[\\/:*?"<>|\x00]', '_', clean)
    clean = clean.strip('. ')
    if not clean.lower().endswith('.pdf'):
        clean += '.pdf'
    return clean or "document.pdf"

def validate_pdf_bytes(data: bytes, max_mb: int) -> Tuple[bool, str, int]:
    """
    Kiểm tra PDF từ bytes trong memory — không cần ghi ra đĩa trước.
    Trả về: (is_valid, error_message, page_count)
    """
    if len(data) == 0:
        return False, "File tải lên bị rỗng (0 bytes).", 0

    if len(data) > max_mb * 1024 * 1024:
        return False, f"Dung lượng file vượt quá giới hạn {max_mb} MB.", 0

    # Kiểm tra magic bytes
    if not data[:1024].find(b"%PDF-") >= 0:
        return False, "Định dạng file không hợp lệ. Chỉ chấp nhận file PDF.", 0

    # Kiểm tra cấu trúc bằng PyMuPDF (mở từ bytes, không cần file path)
    try:
        import pymupdf
        doc = pymupdf.open(stream=data, filetype="pdf")
        page_count = len(doc)
        doc.close()
        if page_count == 0:
            return False, "File PDF không chứa trang nào hợp lệ.", 0
        return True, "", page_count
    except Exception:
        return False, "File PDF bị hỏng hoặc không thể đọc được cấu trúc nội dung.", 0
