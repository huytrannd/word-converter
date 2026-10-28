# MathPDF — Chuyển đề Toán PDF sang Word

Website chuyển đổi file PDF chứa đề Toán thành file Microsoft Word (.docx), hỗ trợ:
- Phương trình, bất phương trình, hệ phương trình
- Phân số, căn thức, số mũ, tích phân, đạo hàm, logarit
- Đề thi trắc nghiệm A/B/C/D
- Bảng biểu và hình ảnh trong PDF
- Công thức được xuất thành Word Equation thực sự (có thể chỉnh sửa trong Word)

---

## Yêu cầu hệ thống

| Phần mềm | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.11+ | Cài tại python.org |
| Node.js | 18+ | Cài tại nodejs.org |
| Pandoc | 3.x | Tự cài qua pypandoc (xem bên dưới) |

> **Lưu ý:** Hệ thống sử dụng **Datalab Convert API** — phải có API key mới hoạt động.

---

## Cài đặt

### 1. Sao chép cấu hình môi trường

```cmd
copy .env.example .env
```

Mở file `.env` và điền API key Datalab của bạn:

```env
DATALAB_API_KEY=dlb_xxxx_của_bạn_ở_đây
DATALAB_CONVERT_MODE=accurate
MAX_UPLOAD_MB=20
JOB_TTL_MINUTES=30
```

> **Quan trọng:** Không commit file `.env` lên Git. File này đã được thêm vào `.gitignore`.

**Lấy API key:** Đăng nhập tại [datalab.to](https://www.datalab.to) → API Keys → Tạo key mới.

---

### 2. Cài đặt Backend (Python)

```cmd
cd "d:\anti\web chuyển word, k giải"
python -m pip install -r backend\requirements.txt
```

Pandoc sẽ được tải tự động lần đầu khi backend khởi động. Để kiểm tra Pandoc thủ công:

```cmd
python -c "import pypandoc; pypandoc.get_pandoc_version()"
```

Nếu chưa cài, chạy lệnh sau một lần:

```cmd
python -c "import pypandoc; pypandoc.download_pandoc()"
```

---

### 3. Cài đặt Frontend (React + Vite + Tailwind)

```cmd
cd frontend
npm install
```

---

## Chạy dự án

### Chạy Backend

Mở một cửa sổ Command Prompt, di chuyển vào thư mục gốc dự án và chạy:

```cmd
cd "d:\anti\web chuyển word, k giải"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Backend sẽ khởi động tại `http://127.0.0.1:8000`.
Website (frontend đã build) cũng được phục vụ tại địa chỉ này sau bước build.

---

### Chạy Frontend (chế độ phát triển)

Mở thêm một cửa sổ Command Prompt:

```cmd
cd "d:\anti\web chuyển word, k giải\frontend"
npm run dev
```

Truy cập giao diện tại `http://localhost:5173`. Yêu cầu tới `/api/*` sẽ tự động được proxy tới backend trên cổng 8000.

---

### Build Frontend cho production

Nếu muốn phục vụ toàn bộ từ một cổng duy nhất (backend):

```cmd
cd "d:\anti\web chuyển word, k giải\frontend"
npm run build
```

Sau khi build xong, chỉ cần chạy backend và truy cập `http://127.0.0.1:8000` là đủ.

---

## Kiểm thử

### Chạy bộ test tự động

```cmd
cd "d:\anti\web chuyển word, k giải"
python -m pytest backend/tests -v
```

Bộ test bao gồm:
- Kiểm tra xác thực file PDF (hợp lệ, rỗng, fake, hỏng)
- Kiểm tra tạo file Word với công thức Toán học (OMML)
- Kiểm tra verify cấu trúc DOCX
- Kiểm tra toàn bộ pipeline API (upload → convert mock → download)
- Kiểm tra phân quyền và xử lý lỗi

### Kiểm thử thủ công

1. Mở `http://localhost:5173`
2. Kéo thả một file PDF đề Toán vào vùng upload
3. Nhấn "Chuyển sang Word"
4. Chờ xử lý → nhấn "Tải xuống Word"
5. Mở file Word và kiểm tra:
   - Công thức có hiển thị dưới dạng Word Equation không?
   - Hình ảnh có được chèn đúng không?
   - Nội dung có bị mất không?

---

## Cấu trúc dự án

```
web chuyển word, k giải/
├── .env.example            # Mẫu biến môi trường
├── .gitignore
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI app, endpoints, pipeline
│   │   ├── config.py       # Đọc biến môi trường
│   │   ├── pdf_validator.py  # Kiểm tra file PDF đầu vào
│   │   ├── datalab_service.py  # Gọi Datalab Convert API
│   │   ├── docx_generator.py   # Tạo DOCX từ Markdown qua Pandoc
│   │   └── job_manager.py      # Quản lý công việc chuyển đổi
│   ├── requirements.txt
│   ├── storage/            # Thư mục tạm lưu file (tự tạo, không commit)
│   └── tests/
│       ├── generate_samples.py
│       ├── test_api.py
│       ├── test_docx_generator.py
│       ├── test_end_to_end.py
│       └── test_pdf_validator.py
└── frontend/
    ├── src/
    │   ├── App.tsx          # Giao diện React
    │   └── index.css        # Tailwind CSS
    ├── tailwind.config.js
    ├── vite.config.ts       # Proxy API sang backend
    └── package.json
```

---

## Giới hạn và lưu ý kỹ thuật

| Hạng mục | Thực trạng |
|---|---|
| Công thức Toán học | Chuyển thành Word Equation OMML (chỉnh sửa được) |
| Hình ảnh / Hình vẽ | Được chèn vào file Word nếu Datalab trả về |
| PDF scan | Hỗ trợ qua OCR của Datalab (mode=accurate) |
| Dung lượng tối đa | 20 MB (điều chỉnh qua MAX_UPLOAD_MB) |
| API credits | Mỗi lần upload tốn 1 lượt Datalab credit |
| Thời gian xử lý | Phụ thuộc độ phức tạp tài liệu và Datalab API |
| Chính xác nội dung | Phụ thuộc vào chất lượng nhận diện của Datalab |

> **Quan trọng:** Công cụ này **không sửa, không giải, không bình luận** đề Toán. Kết quả là nội dung nguyên gốc được chuyển định dạng.

---

## Xử lý sự cố thường gặp

**"Hệ thống chưa được thiết lập API key"**
→ Tạo file `.env` từ `.env.example` và điền `DATALAB_API_KEY`.

**"Không thể chuyển đổi tài liệu này"**
→ Kiểm tra log backend để biết lỗi chi tiết. Thường do API key hết hạn hoặc tài liệu không hỗ trợ.

**Pandoc không tìm thấy**
→ Chạy: `python -c "import pypandoc; pypandoc.download_pandoc()"`

**npm không chạy được trên PowerShell**
→ Dùng `npm.cmd` thay vì `npm`, hoặc mở Command Prompt (cmd.exe) thông thường.

