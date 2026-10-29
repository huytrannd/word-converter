import logging
import tempfile
from pathlib import Path
from typing import Tuple, Optional
from .config import settings

logger = logging.getLogger("datalab_service")

def check_api_configuration() -> Tuple[bool, str]:
    """Kiểm tra API key đã cấu hình chưa, không để lộ giá trị key."""
    if not settings.is_api_key_configured:
        return False, "Hệ thống chưa được cấu hình DATALAB_API_KEY."
    return True, ""

def convert_pdf_bytes_to_markdown(
    pdf_bytes: bytes,
    original_filename: str = "document.pdf"
) -> Tuple[bool, Optional[str], list, str]:
    """
    Gọi Datalab Convert API để chuyển PDF sang Markdown.
    Nhận bytes, ghi vào tempfile trong quá trình xử lý, xóa sau khi xong.

    Trả về:
        (success, markdown_text, images_list, error_message)
        images_list: danh sách dict {"name": str, "data": bytes}
    """
    is_ok, err = check_api_configuration()
    if not is_ok:
        return False, None, [], err

    try:
        from datalab_sdk import DatalabClient, ConvertOptions
        from datalab_sdk.exceptions import (
            DatalabAuthenticationError,
            DatalabPaymentRequiredError,
            DatalabRateLimitError,
            DatalabTimeoutError,
            DatalabAPIError,
        )
    except ImportError as e:
        return False, None, [], f"Lỗi nạp thư viện Datalab SDK: {e}"

    try:
        client = DatalabClient(api_key=settings.DATALAB_API_KEY)
        options = ConvertOptions(
            output_format="markdown",
            mode=settings.DATALAB_CONVERT_MODE,
            paginate=True,
        )

        # Ghi PDF vào tempfile để Datalab SDK đọc, xóa ngay sau khi xong
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_pdf = Path(tmp_dir) / original_filename
            tmp_pdf.write_bytes(pdf_bytes)

            logger.info(f"Gửi tài liệu tới Datalab API (mode={settings.DATALAB_CONVERT_MODE})...")
            result = client.convert(
                file_path=str(tmp_pdf),
                options=options,
                save_output=tmp_dir,       # SDK lưu markdown + ảnh vào đây
                max_polls=180,
                poll_interval=2,
            )

            # Kiểm tra kết quả
            if hasattr(result, "status") and result.status != "complete":
                err_msg = getattr(result, "error", None) or "Chuyển đổi chưa hoàn thành."
                return False, None, [], f"Datalab trả về trạng thái không hoàn thành: {err_msg}"

            if hasattr(result, "error") and result.error:
                return False, None, [], f"Datalab báo lỗi: {result.error}"

            # Lấy nội dung markdown
            markdown_text = None
            if hasattr(result, "markdown") and result.markdown:
                markdown_text = result.markdown
            else:
                # SDK đã lưu file .md vào tmp_dir qua save_output
                md_files = list(Path(tmp_dir).glob("*.md"))
                if md_files:
                    markdown_text = md_files[0].read_text(encoding="utf-8")

            if not markdown_text:
                return False, None, [], "Không tìm thấy nội dung Markdown sau khi Datalab xử lý."

            # Lấy hình ảnh đã trích xuất (nếu có)
            images = []
            if hasattr(result, "images") and result.images:
                # result.images là dict {filename: bytes} theo SDK
                for name, data in result.images.items():
                    if isinstance(data, bytes):
                        images.append({"name": name, "data": data})
            else:
                # Fallback: tìm file ảnh trong tmp_dir do save_output ghi
                for img_file in Path(tmp_dir).glob("*.png"):
                    images.append({"name": img_file.name, "data": img_file.read_bytes()})
                for img_file in Path(tmp_dir).glob("*.jpg"):
                    images.append({"name": img_file.name, "data": img_file.read_bytes()})

            logger.info(f"Datalab hoàn tất: {len(markdown_text)} ký tự, {len(images)} hình ảnh.")
            return True, markdown_text, images, ""

    except DatalabAuthenticationError:
        logger.error("Datalab Auth Error: API key không hợp lệ hoặc hết hạn.")
        return False, None, [], "Lỗi xác thực Datalab API: Khóa API không hợp lệ."
    except DatalabPaymentRequiredError:
        logger.error("Datalab Payment Required: Hết credit.")
        return False, None, [], "Tài khoản Datalab API đã hết credit."
    except DatalabRateLimitError:
        logger.error("Datalab Rate Limit exceeded.")
        return False, None, [], "Đã vượt quá giới hạn tần suất Datalab API. Vui lòng thử lại sau giây lát."
    except DatalabTimeoutError:
        logger.error("Datalab Timeout.")
        return False, None, [], "Quá thời gian chờ xử lý. Vui lòng thử với tài liệu ngắn hơn."
    except DatalabAPIError as e:
        logger.error(f"Datalab API Error: {e}")
        return False, None, [], f"Lỗi từ dịch vụ Datalab: {e}"
    except Exception as e:
        logger.error(f"Unexpected error during conversion: {e}")
        return False, None, [], f"Lỗi không xác định trong quá trình gọi Datalab API: {e}"
