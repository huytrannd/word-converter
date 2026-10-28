import os
import re
import zipfile
from pathlib import Path
from typing import Tuple, List
import pypandoc

def ensure_pandoc_available() -> bool:
    """Đảm bảo Pandoc đã sẵn sàng hoạt động."""
    try:
        pypandoc.get_pandoc_version()
        return True
    except Exception:
        try:
            pypandoc.download_pandoc()
            pypandoc.get_pandoc_version()
            return True
        except Exception:
            return False

def fix_image_paths_in_markdown(markdown_content: str, images_dir: Path) -> str:
    """
    Chuẩn hóa các đường dẫn hình ảnh trong Markdown để Pandoc tìm thấy đúng file ảnh trên đĩa.
    Ví dụ: ![](image_0.png) -> ![](/absolute/path/to/image_0.png) hoặc đường dẫn tương đối đúng.
    """
    if not images_dir.exists():
        return markdown_content

    # Tìm các mẫu ![](...)
    def replace_img_src(match):
        alt = match.group(1)
        src = match.group(2).strip()
        # Nếu đường dẫn đã là tuyệt đối và tồn tại, giữ nguyên
        src_path = Path(src)
        if src_path.is_file():
            return f"![{alt}]({src_path.as_posix()})"
        
        # Thử tìm file theo tên trong images_dir
        candidate = images_dir / src_path.name
        if candidate.is_file():
            return f"![{alt}]({candidate.as_posix()})"
        
        return match.group(0)

    pattern = r'!\[(.*?)\]\((.*?)\)'
    updated = re.sub(pattern, replace_img_src, markdown_content)
    return updated

def generate_docx_from_markdown(
    markdown_path: Path,
    output_docx_path: Path,
    resource_dir: Path
) -> Tuple[bool, str]:
    """
    Tạo file Word (.docx) từ file Markdown bằng Pandoc với hỗ trợ công thức Toán học (OMML) và hình ảnh.
    """
    if not ensure_pandoc_available():
        return False, "Công cụ Pandoc chưa sẵn sàng trên hệ thống máy chủ."

    if not markdown_path.exists():
        return False, "Không tìm thấy file nội dung Markdown để chuyển đổi."

    try:
        # Đọc nội dung Markdown và chuẩn hóa đường dẫn hình ảnh
        with open(markdown_path, "r", encoding="utf-8") as f:
            content = f.read()

        fixed_content = fix_image_paths_in_markdown(content, resource_dir)
        temp_fixed_md = markdown_path.parent / "processed_content.md"
        with open(temp_fixed_md, "w", encoding="utf-8") as f:
            f.write(fixed_content)

        # Pandoc chuyển đổi Markdown sang docx:
        # --from=markdown+tex_math_dollars+raw_tex bảo toàn các công thức $...$, $$...$$ thành OMML Equation
        # --resource-path hỗ trợ tìm kiếm hình ảnh
        extra_args = [
            '--from=markdown+tex_math_dollars+raw_tex+pipe_tables+strikeout',
            f'--resource-path={resource_dir.as_posix()}',
        ]

        pypandoc.convert_file(
            str(temp_fixed_md),
            'docx',
            outputfile=str(output_docx_path),
            extra_args=extra_args
        )

        # Xóa file Markdown tạm
        if temp_fixed_md.exists():
            try:
                temp_fixed_md.unlink()
            except Exception:
                pass

        # Kiểm tra tính hợp lệ của file DOCX đầu ra
        is_valid, verify_err = verify_docx_file(output_docx_path)
        if not is_valid:
            return False, f"File Word tạo ra không hợp lệ: {verify_err}"

        return True, ""

    except Exception as e:
        return False, f"Lỗi trong quá trình tạo file Word: {str(e)}"

def verify_docx_file(docx_path: Path) -> Tuple[bool, str]:
    """
    Xác minh kỹ thuật file DOCX theo tiêu chuẩn Phần VI:
    1. File tồn tại
    2. Dung lượng > 0
    3. File là một gói ZIP hợp lệ
    4. Chứa word/document.xml
    5. Không phải file lỗi HTML hoặc chuỗi lỗi
    """
    if not docx_path.exists():
        return False, "File kết quả không tồn tại."

    size = docx_path.stat().st_size
    if size == 0:
        return False, "File kết quả có dung lượng 0 bytes."

    # Đọc thử header kiểm tra không phải file HTML
    try:
        with open(docx_path, "rb") as f:
            header = f.read(100)
            if b"<html" in header.lower() or b"<!doctype html" in header.lower():
                return False, "Kết quả trả về là trang HTML lỗi thay vì tài liệu Word."
            # DOCX là zip file, phải bắt đầu bằng PK (0x50 0x4B 0x03 0x04)
            if not header.startswith(b"PK\x03\x04"):
                return False, "File không có định dạng nén ZIP chuẩn của Microsoft Word."
    except Exception as e:
        return False, f"Không thể đọc header file: {str(e)}"

    # Kiểm tra cấu trúc ZIP & document.xml
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            file_list = z.namelist()
            if "word/document.xml" not in file_list:
                return False, "Gói tài liệu Word thiếu thành phần cấu trúc chính (word/document.xml)."
            if "[Content_Types].xml" not in file_list:
                return False, "Gói tài liệu Word thiếu file [Content_Types].xml."
            
            # Đọc thử document.xml
            doc_xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
            if not doc_xml.strip():
                return False, "Nội dung tài liệu Word bị trống."
    except Exception as e:
        return False, f"Gói tài liệu Word bị lỗi cấu trúc nén: {str(e)}"

    return True, ""

