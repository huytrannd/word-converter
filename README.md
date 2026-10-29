# MathPDF — Chuyển Đề Toán PDF sang Word (.docx)

Website tối giản chuyển đổi tài liệu PDF chứa đề Toán sang Microsoft Word (.docx), bảo toàn công thức toán học dưới dạng **Word Equation (OMML)** thực sự và giữ nguyên hình vẽ/bảng biểu.

---

## 1. Kiến trúc tối giản (Đã tối ưu hóa)

Dự án đã được rút gọn tối đa để vận hành ổn định trên môi trường máy chủ như Render:
- **1 Request đồng bộ**: Người dùng tải PDF lên → Backend xác thực → Gọi Datalab Convert → Tạo Word DOCX → Trả file tải về ngay lập tức.
- **Không cần cơ sở dữ liệu, không cần tài khoản, không lưu trữ dài hạn**: Xử lý hoàn toàn trong bộ nhớ và thư mục tạm `tempfile`, tự động dọn dẹp khi request hoàn tất.
- **Không BackgroundTasks, không Polling**: Giao diện giữ nguyên trải nghiệm trực quan, hiển thị trạng thái xử lý mượt mà.

---

## 2. Cấu hình biến môi trường (.env)

Tạo file `.env` ở thư mục gốc dự án (hoặc sao chép từ `.env.example`):

```env
DATALAB_API_KEY=dlb_xxxx_của_bạn_ở_đây
DATALAB_CONVERT_MODE=accurate
MAX_UPLOAD_MB=20
HOST=0.0.0.0
PORT=8000
```

> **Bảo mật:** File `.env` tuyệt đối không được đưa lên Git. Hãy kiểm tra `.gitignore`.

---

## 3. Chạy kiểm thử tự động

```cmd
python -m pytest backend/tests -v
```
Toàn bộ 18 bài kiểm thử (validate PDF bytes, Pandoc OMML math equations, nhúng hình ảnh, xử lý lỗi API và mock end-to-end pipeline) đều đã vượt qua 100%.

---

## 4. Chạy dự án ở máy cục bộ (Local)

### Cách 1: Chạy trọn gói (Một cổng duy nhất 8000)

Frontend đã được build vào thư mục `frontend/dist`. Backend FastAPI sẽ tự động phục vụ cả giao diện web lẫn API:

```cmd
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Mở trình duyệt: `http://127.0.0.1:8000`

### Cách 2: Chế độ phát triển (Dev Mode)

Mở 2 cửa sổ dòng lệnh:
1. **Backend**:
   ```cmd
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. **Frontend**:
   ```cmd
   cd frontend
   npm run dev
   ```
   Mở trình duyệt: `http://localhost:5173` (Vite tự động proxy API sang cổng 8000).

---

## 5. Hướng dẫn Triển khai lên Render (Render.com)

Backend phù hợp nhất khi triển khai dưới dạng **Web Service** trên Render:

### Cách làm nhanh:
1. Đẩy mã nguồn dự án lên GitHub / GitLab của bạn (nhớ không commit file `.env`).
2. Đăng nhập [render.com](https://dashboard.render.com).
3. Chọn **New +** → **Web Service** → Chọn Repository của bạn.
4. Điền các thông tin:
   - **Name**: `mathpdf-backend`
   - **Region**: `Singapore` (hoặc khu vực gần bạn nhất)
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r backend/requirements.txt && python -c "import pypandoc; pypandoc.download_pandoc()"
     ```
   - **Start Command**: 
     ```bash
     uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
     ```
5. Tại mục **Environment Variables**, thêm:
   - `DATALAB_API_KEY`: *(Dán khóa API Datalab của bạn vào đây)*
   - `DATALAB_CONVERT_MODE`: `accurate`
   - `MAX_UPLOAD_MB`: `20`
   - `PYTHON_VERSION`: `3.11.9`
6. Bấm **Create Web Service**.

> **Mẹo triển khai Frontend:**
> - Bạn có thể giữ frontend chạy chung trực tiếp trên Render Web Service (vì backend đã tích hợp sẵn `frontend/dist`), chỉ cần chạy `npm run build` trước khi push code.
> - Hoặc nếu deploy Frontend riêng lên Vercel: trong `frontend/vite.config.ts`, trỏ proxy hoặc cấu hình base URL tới đường dẫn `https://mathpdf-backend.onrender.com`.
