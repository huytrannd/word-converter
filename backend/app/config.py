import os
from pathlib import Path
from dotenv import load_dotenv

# Tìm file .env: ưu tiên thư mục gốc dự án
_root = Path(__file__).resolve().parent.parent.parent
_env_path = _root / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()  # fallback: đọc từ biến môi trường hệ thống (Render tự inject)

class Settings:
    DATALAB_API_KEY: str = os.getenv("DATALAB_API_KEY", "").strip()
    DATALAB_CONVERT_MODE: str = os.getenv("DATALAB_CONVERT_MODE", "accurate").strip()
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    HOST: str = os.getenv("HOST", "0.0.0.0").strip()
    PORT: int = int(os.getenv("PORT", "8000"))

    @property
    def is_api_key_configured(self) -> bool:
        return bool(self.DATALAB_API_KEY and len(self.DATALAB_API_KEY) > 5)

# Không gọi mkdir() ở đây — tránh crash trên môi trường read-only
settings = Settings()
