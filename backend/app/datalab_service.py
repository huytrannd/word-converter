import os
import logging
from pathlib import Path
from typing import Tuple, Optional
from .config import settings

logger = logging.getLogger("datalab_service")

class DatalabService:
    def __init__(self):
        self.api_key = settings.DATALAB_API_KEY
        self.mode = settings.DATALAB_CONVERT_MODE

    def check_configuration(self) -> Tuple[bool, str]:
        """Kiểm tra cấu hình API key mà không làm lộ key."""
        if not settings.is_api_key_configured:
            return False, "Hệ thống chưa được cấu hình API key Datalab (DATALAB_API_KEY)."
        return True, ""

    def convert_pdf_to_markdown(self, pdf_path: Path, output_dir: Path) -> Tuple[bool, Optional[Path], str]:
        """
        Gọi Datalab Convert API để chuyển file PDF sang Markdown và lưu các hình ảnh đính kèm.
        Trả về: (success: bool, markdown_file_path: Optional[Path], error_message: str)
        """
        is_configured, config_err = self.check_configuration()
        if not is_configured:
            return False, None, config_err

        try:
            from datalab_sdk import DatalabClient, ConvertOptions
            from datalab_sdk.exceptions import (
                DatalabAuthenticationError,
                DatalabPaymentRequiredError,
                DatalabRateLimitError,
                DatalabTimeoutError,
                DatalabAPIError
            )
        except ImportError as e:
            return False, None, f"Lỗi nạp thư viện Datalab SDK: {str(e)}"

        try:
            # Khởi tạo client với API key bảo mật từ biến môi trường
            client = DatalabClient(api_key=self.api_key)

            options = ConvertOptions(
                output_format="markdown",
                mode=self.mode,
                paginate=True
            )

            logger.info("Bắt đầu gửi tài liệu tới Datalab API...")
            # Gọi Datalab Convert API với polling tích hợp của SDK
            result = client.convert(
                file_path=str(pdf_path),
                options=options,
                max_polls=180,
                poll_interval=2
            )

            # Kiểm tra trạng thái trả về
            if hasattr(result, "status") and result.status != "complete":
                err_msg = getattr(result, "error", None) or "Quá trình chuyển đổi tài liệu chưa hoàn thành."
                return False, None, f"Datalab trả về trạng thái không hoàn thành: {err_msg}"

            if hasattr(result, "error") and result.error:
                return False, None, f"Datalab báo lỗi: {result.error}"

            # Lưu output (markdown và các hình ảnh trích xuất)
            output_dir.mkdir(parents=True, exist_ok=True)
            if hasattr(result, "save_output"):
                result.save_output(output_path=str(output_dir), save_images=True)

            # Tìm file markdown vừa được lưu trong output_dir
            md_files = list(output_dir.glob("*.md"))
            if not md_files:
                # Nếu save_output không ghi file .md mà nội dung nằm trong result.markdown
                if hasattr(result, "markdown") and result.markdown:
                    md_path = output_dir / "document.md"
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(result.markdown)
                    return True, md_path, ""
                return False, None, "Không tìm thấy nội dung Markdown sau khi Datalab hoàn tất xử lý."

            return True, md_files[0], ""

        except DatalabAuthenticationError:
            logger.error("Datalab Authentication Failed: Khóa API không hợp lệ hoặc đã hết hạn.")
            return False, None, "Lỗi xác thực Datalab API: Khóa API không hợp lệ hoặc đã bị vô hiệu hóa."
        except DatalabPaymentRequiredError:
            logger.error("Datalab Payment Required: Tài khoản không đủ credit.")
            return False, None, "Tài khoản Datalab API đã hết hạn mức credit."
        except DatalabRateLimitError:
            logger.error("Datalab Rate Limit: Đã vượt quá giới hạn tần suất gọi API.")
            return False, None, "Đã vượt quá giới hạn tần suất yêu cầu tới Datalab API. Vui lòng thử lại sau giây lát."
        except DatalabTimeoutError:
            logger.error("Datalab Timeout: Quá thời gian chờ phản hồi từ Datalab.")
            return False, None, "Quá thời gian xử lý từ máy chủ Datalab. Vui lòng thử lại với tài liệu ngắn hơn."
        except DatalabAPIError as e:
            logger.error(f"Datalab API Error: {str(e)}")
            return False, None, f"Lỗi từ dịch vụ Datalab: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected conversion error: {str(e)}")
            return False, None, f"Lỗi xử lý trong quá trình giao tiếp với Datalab API: {str(e)}"

datalab_service = DatalabService()

