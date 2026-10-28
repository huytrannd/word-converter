import fitz  # PyMuPDF
from pathlib import Path

def create_sample_math_pdf(output_path: Path):
    doc = fitz.open()
    page = doc.new_page()
    
    # Thêm văn bản và công thức toán học mẫu
    text = (
        "DE THI KHAO SAT TOAN HOC\n\n"
        "Cau 1. Giai phuong trinh bac hai:\n"
        "x^2 - 5x + 6 = 0\n\n"
        "Cau 2. Tinh gia tri bieu thuc:\n"
        "P = (sqrt(a) + 1) / (sqrt(a) - 1)\n\n"
        "Cau 3. Tinh tich phan:\n"
        "I = integral_0^1 (2x + 1) dx\n\n"
        "Cau 4. Trac nghiem:\n"
        "A. 1    B. 2    C. 3    D. 4\n"
    )
    
    # Chèn text
    page.insert_text((50, 72), text, fontsize=12)
    
    # Vẽ một hình chữ nhật / đường thẳng hình học đơn giản
    rect = fitz.Rect(50, 300, 200, 400)
    page.draw_rect(rect, color=(0, 0, 0), width=1.5)
    page.insert_text((60, 350), "Hinh chu nhat ABCD", fontsize=10)
    
    doc.save(str(output_path))
    doc.close()

if __name__ == "__main__":
    test_dir = Path(__file__).parent / "sample_files"
    test_dir.mkdir(parents=True, exist_ok=True)
    create_sample_math_pdf(test_dir / "sample_math.pdf")
    print("Created sample_math.pdf")

