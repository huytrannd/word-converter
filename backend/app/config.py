import os
from pathlib import Path
from dotenv import load_dotenv

# Tìm file .env ở thư mục gốc dự án hoặc backend
root_dir = Path(__file__).resolve().parent.parent.parent
dotenv_path = root_dir / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

class Settings:
    DATALAB_API_KEY: str = os.getenv("DATALAB_API_KEY", "").strip()
    DATALAB_CONVERT_MODE: str = os.getenv("DATALAB_CONVERT_MODE", "accurate").strip()
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    JOB_TTL_MINUTES: int = int(os.getenv("JOB_TTL_MINUTES", "30"))
    HOST: str = os.getenv("HOST", "127.0.0.1").strip()
    PORT: int = int(os.getenv("PORT", "8000"))

    # Thư mục lưu trữ tạm thời cho các công việc chuyển đổi
    STORAGE_DIR: Path = Path(__file__).resolve().parent.parent / "storage"

    @property
    def is_api_key_configured(self) -> bool:
        return bool(self.DATALAB_API_KEY and len(self.DATALAB_API_KEY) > 5)

settings = Settings()
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

