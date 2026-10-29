import re
import zipfile
import tempfile
import logging
from pathlib import Path
from typing import Tuple, List, Dict

logger = logging.getLogger("docx_generator")

def _ensure_pandoc() -> bool:
    """Đảm bảo Pandoc sẵn sàng. Tự tải về nếu chưa có (Render hỗ trợ)."""
    try:
        import pypandoc
        pypandoc.get_pandoc_version()
        return True
    except Exception:
        try:
            import pypandoc
            pypandoc.download_pandoc()
            pypandoc.get_pandoc_version()
            return True
        except Exception:
            return False

def _fix_image_refs(markdown: str, images: List[Dict]) -> str:
    """
    Chuẩn hóa đường dẫn ảnh trong Markdown theo danh sách images đã nhận được.
    images: [{"name": "img0.png", "data": bytes}, ...]
    Hàm này không ghi file — chỉ thay thế tên để khớp với tên file sẽ được ghi vào tmpdir.
    """
    if not images:
        return markdown

    image_names = {img["name"] for img in images}

    def replace_img(match):
        alt = match.group(1)
        src = match.group(2).strip()
        # Nếu basename của src khớp với một file trong images, giữ basename
        basename = Path(src).name
        if basename in image_names:
            return f"![{alt}]({basename})"
        return match.group(0)

    return re.sub(r'!\[(.*?)\]\((.*?)\)', replace_img, markdown)

def generate_docx_from_markdown_and_images(
    markdown_text: str,
    images: List[Dict],
    output_filename: str = "output.docx"
) -> Tuple[bool, bytes, str]:
    """
    Tạo DOCX từ Markdown (có thể chứa công thức LaTeX $...$ và $$...$$) và hình ảnh.
    Dùng Pandoc để chuyển đổi — tất cả file tạm được xử lý trong tempfile.TemporaryDirectory.

    Trả về: (success, docx_bytes, error_message)
    """
    if not _ensure_pandoc():
        return False, b"", "Pandoc chưa sẵn sàng trên máy chủ."

    if not markdown_text or not markdown_text.strip():
        return False, b"", "Nội dung Markdown trống, không thể tạo file Word."

    try:
        import pypandoc

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # 1. Ghi hình ảnh vào tempdir để Pandoc tìm thấy
            for img in images:
                img_file = tmp_path / img["name"]
                img_file.write_bytes(img["data"])

            # 2. Chuẩn hóa đường dẫn ảnh trong Markdown
            fixed_md = _fix_image_refs(markdown_text, images)

            # 3. Ghi Markdown đã chuẩn hóa
            md_file = tmp_path / "content.md"
            md_file.write_text(fixed_md, encoding="utf-8")

            # 4. Chạy Pandoc
            #    --from=markdown+tex_math_dollars+raw_tex: $...$ và $$...$$ → OMML Equation trong Word
            #    --resource-path: Pandoc tìm hình ảnh trong tmpdir
            docx_file = tmp_path / output_filename
            pypandoc.convert_file(
                str(md_file),
                "docx",
                outputfile=str(docx_file),
                extra_args=[
                    "--from=markdown+tex_math_dollars+raw_tex+pipe_tables+strikeout",
                    f"--resource-path={tmp_dir}",
                ],
            )

            # 5. Đọc DOCX vào memory
            if not docx_file.exists() or docx_file.stat().st_size == 0:
                return False, b"", "Pandoc không tạo được file DOCX."

            docx_bytes = docx_file.read_bytes()

        # 6. Kiểm tra nhanh DOCX trong memory
        ok, err = _verify_docx_bytes(docx_bytes)
        if not ok:
            return False, b"", err

        logger.info(f"DOCX tạo thành công: {len(docx_bytes)} bytes.")
        return True, docx_bytes, ""

    except Exception as e:
        logger.error(f"Lỗi tạo DOCX: {e}")
        return False, b"", f"Lỗi trong quá trình tạo file Word: {e}"

def _verify_docx_bytes(data: bytes) -> Tuple[bool, str]:
    """Kiểm tra nhanh cấu trúc DOCX từ bytes trong memory."""
    if len(data) == 0:
        return False, "File kết quả có dung lượng 0 bytes."

    if data[:4] != b"PK\x03\x04":
        if data[:5].lower() in (b"<html", b"<!doc"):
            return False, "Kết quả là trang HTML lỗi thay vì file Word."
        return False, "File không có định dạng ZIP chuẩn của Microsoft Word."

    try:
        import io
        with zipfile.ZipFile(io.BytesIO(data), "r") as z:
            names = z.namelist()
            if "word/document.xml" not in names:
                return False, "Gói tài liệu Word thiếu word/document.xml."
            if "[Content_Types].xml" not in names:
                return False, "Gói tài liệu Word thiếu [Content_Types].xml."
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
            if not xml.strip():
                return False, "Nội dung tài liệu Word bị trống."
    except Exception as e:
        return False, f"Gói DOCX bị lỗi cấu trúc: {e}"

    return True, ""
