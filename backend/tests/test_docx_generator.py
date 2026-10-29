import io
import zipfile
import pytest
from backend.app.docx_generator import (
    generate_docx_from_markdown_and_images,
    _verify_docx_bytes,
    _fix_image_refs,
)

MATH_MARKDOWN = r"""# Đề Kiểm Tra Toán Học

## Câu 1
Giải phương trình:
$$x^2 - 4x + 3 = 0$$

## Câu 2
Rút gọn biểu thức:
$$P = \frac{\sqrt{x} + 2}{\sqrt{x} - 2}$$

## Câu 3
Đạo hàm của hàm số $y = \sin(x) \cdot e^x$ là gì?

| $x$ | $1$ | $2$ | $3$ |
|---|---|---|---|
| $y$ | $0$ | $1$ | $4$ |
"""

def test_generate_docx_with_math_equations():
    """DOCX tạo ra phải chứa Word Equation OMML (m:oMath)."""
    success, docx_bytes, err = generate_docx_from_markdown_and_images(
        MATH_MARKDOWN, images=[]
    )
    assert success is True, f"Thất bại: {err}"
    assert len(docx_bytes) > 0

    # Kiểm tra OMML equations trong XML
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
        assert "<m:oMath>" in xml or "<m:oMath " in xml, "Không tìm thấy Word Equation trong DOCX"
        assert "<m:f>" in xml or "<m:f " in xml, "Không tìm thấy phần tử fraction"
        assert "<m:rad>" in xml or "<m:rad " in xml, "Không tìm thấy phần tử radical/sqrt"

def test_generate_docx_with_image(tmp_path):
    """DOCX phải chứa hình ảnh được nhúng vào."""
    # Tạo PNG 1x1 pixel tối thiểu (PNG header chuẩn)
    png_bytes = (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02'
        b'\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
        b'\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    md_with_img = MATH_MARKDOWN + "\n\n![Hình vẽ minh họa](diagram.png)\n"
    images = [{"name": "diagram.png", "data": png_bytes}]

    success, docx_bytes, err = generate_docx_from_markdown_and_images(
        md_with_img, images=images
    )
    assert success is True, f"Thất bại: {err}"

    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        names = z.namelist()
        # Pandoc nhúng ảnh vào word/media/
        has_image = any("word/media" in n for n in names)
        assert has_image, f"Không tìm thấy ảnh trong DOCX. Files: {names}"

def test_verify_docx_invalid_html():
    """File HTML phải bị từ chối."""
    bad = b"<html><body>Error page</body></html>"
    ok, err = _verify_docx_bytes(bad)
    assert ok is False
    assert "HTML" in err

def test_verify_docx_empty():
    ok, err = _verify_docx_bytes(b"")
    assert ok is False

def test_fix_image_refs_replaces_path():
    md = "Text ![fig](path/to/diagram.png) text"
    images = [{"name": "diagram.png", "data": b""}]
    result = _fix_image_refs(md, images)
    assert "diagram.png" in result
    # Đường dẫn gốc nên bị thay
    assert "path/to/diagram.png" not in result

def test_fix_image_refs_no_images():
    md = "No images here, just text."
    result = _fix_image_refs(md, images=[])
    assert result == md
