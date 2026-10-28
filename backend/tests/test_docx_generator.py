import zipfile
import pytest
from pathlib import Path
from backend.app.docx_generator import (
    generate_docx_from_markdown,
    verify_docx_file,
    fix_image_paths_in_markdown
)

def test_generate_docx_with_math_and_table(tmp_path):
    md_file = tmp_path / "math_sample.md"
    docx_file = tmp_path / "math_sample.docx"
    
    md_content = """# Đề Kiểm Tra Toán Học

## Câu 1
Giải phương trình:
$$x^2 - 4x + 3 = 0$$

## Câu 2
Cho biểu thức:
$$P = \\frac{\\sqrt{x} + 2}{\\sqrt{x} - 2}$$

Hàm số $y = \\int_0^x \\sin(t) dt$.

| $x$ | $1$ | $2$ |
| --- | --- | --- |
| $y$ | $3$ | $4$ |
"""
    md_file.write_text(md_content, encoding="utf-8")
    
    success, err = generate_docx_from_markdown(md_file, docx_file, tmp_path)
    assert success is True
    assert err == ""
    assert docx_file.exists()
    assert docx_file.stat().st_size > 0
    
    # Kiểm tra cấu trúc XML bên trong docx
    is_valid, v_err = verify_docx_file(docx_file)
    assert is_valid is True
    assert v_err == ""
    
    with zipfile.ZipFile(docx_file, "r") as z:
        xml = z.read("word/document.xml").decode("utf-8")
        # OMML equation tags do Word nhận diện
        assert "<m:oMath>" in xml or "<m:oMath " in xml
        assert "<m:f>" in xml or "<m:f " in xml  # fraction
        assert "<m:rad>" in xml or "<m:rad " in xml  # square root

def test_fix_image_paths_in_markdown(tmp_path):
    img_file = tmp_path / "diagram1.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    
    content = "Hình học: ![Hinh 1](diagram1.png) và text khác."
    fixed = fix_image_paths_in_markdown(content, tmp_path)
    assert img_file.name in fixed

def test_verify_docx_file_invalid(tmp_path):
    fake_docx = tmp_path / "invalid.docx"
    fake_docx.write_text("<html><body>Error</body></html>")
    
    is_valid, err = verify_docx_file(fake_docx)
    assert is_valid is False
    assert "HTML" in err or "ZIP" in err

