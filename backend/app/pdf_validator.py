import re
from pathlib import Path
from typing import Tuple
import fitz  # PyMuPDF
from .config import settings

def sanitize_filename(filename: str) -> str:
    """Làm sạch tên file, loại bỏ các ký tự nguy hiểm và chống directory traversal."""
    if not filename:
        return "document.pdf"
    
    # Loại bỏ đường dẫn nếu có
    clean_name = Path(filename).name
    # Thay thế các ký tự không an toàn cho hệ thống file
    clean_name = re.sub(r'[\/:*?"<>|\\x00]', '_', clean_name)
    clean_name = clean_name.strip('. ')
    if not clean_name.lower().endswith('.pdf'):
        clean_name += '.pdf'
    if not clean_name:
        clean_name = "document.pdf"
    return clean_name

def validate_pdf_file(file_path: Path) -> Tuple[bool, str, int]:
    """
    Kiểm tra file có phải là PDF hợp lệ không.
    Trả về: (is_valid: bool, error_message: str, page_count: int)
    """
    if not file_path.exists():
        return False, "File không tồn tại trên máy chủ.", 0
    
    # 1. Kiểm tra kích thước file
    file_size = file_path.stat().st_size
    if file_size == 0:
        return False, "File tải lên bị rỗng (0 bytes).", 0
    
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if file_size > max_bytes:
        return False, f"File vượt quá dung lượng tối đa cho phép ({settings.MAX_UPLOAD_MB} MB).", 0
    
    # 2. Kiểm tra magic bytes
    try:
        with open(file_path, "rb") as f:
            header = f.read(1024)
            if b"%PDF-" not in header:
                return False, "Định dạng file không hợp lệ. Chỉ chấp nhận file PDF.", 0
    except Exception as e:
        return False, f"Không thể đọc file: {str(e)}", 0
    
    # 3. Kiểm tra cấu trúc bằng PyMuPDF
    try:
        doc = fitz.open(str(file_path))
        page_count = len(doc)
        if page_count == 0:
            doc.close()
            return False, "File PDF không chứa trang nào hợp lệ.", 0
        doc.close()
    except Exception:
        return False, "File PDF bị hỏng hoặc không thể đọc được cấu trúc nội dung.", 0
        
    return True, "", page_count

