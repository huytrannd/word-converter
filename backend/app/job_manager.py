import time
import uuid
import shutil
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from .config import settings

logger = logging.getLogger("job_manager")

@dataclass
class JobInfo:
    job_id: str
    original_filename: str
    file_size: int
    page_count: int = 0
    status: str = "pending"  # pending, validating, converting, generating_docx, completed, failed
    status_message: str = "Đang tiếp nhận tài liệu..."
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    job_dir: Optional[Path] = None
    pdf_path: Optional[Path] = None
    docx_path: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "filename": self.original_filename,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "status": self.status,
            "message": self.status_message,
            "error": self.error_message if self.status == "failed" else None,
            "completed": self.status == "completed",
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }

class JobManager:
    def __init__(self):
        self._jobs: Dict[str, JobInfo] = {}

    def create_job(self, original_filename: str, file_size: int) -> JobInfo:
        """Tạo một công việc chuyển đổi mới với mã định danh ngẫu nhiên khó đoán."""
        job_id = str(uuid.uuid4())
        job_dir = settings.STORAGE_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        job = JobInfo(
            job_id=job_id,
            original_filename=original_filename,
            file_size=file_size,
            job_dir=job_dir,
            pdf_path=job_dir / "input.pdf",
            docx_path=job_dir / "output.docx"
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Lấy thông tin công việc theo job_id."""
        return self._jobs.get(job_id)

    def update_status(self, job_id: str, status: str, message: str, error: Optional[str] = None):
        """Cập nhật trạng thái xử lý."""
        job = self.get_job(job_id)
        if not job:
            return
        job.status = status
        job.status_message = message
        if error is not None:
            job.error_message = error
        if status in ("completed", "failed"):
            job.completed_at = time.time()

    def cleanup_expired_jobs(self):
        """Dọn dẹp các thư mục và thông tin công việc đã hết thời hạn TTL."""
        now = time.time()
        ttl_seconds = settings.JOB_TTL_MINUTES * 60
        expired_ids = []

        for jid, job in self._jobs.items():
            if now - job.created_at > ttl_seconds:
                expired_ids.append(jid)
                if job.job_dir and job.job_dir.exists():
                    try:
                        shutil.rmtree(job.job_dir, ignore_errors=True)
                    except Exception as e:
                        logger.warning(f"Lỗi khi dọn dẹp thư mục job {jid}: {e}")

        for jid in expired_ids:
            self._jobs.pop(jid, None)

        if expired_ids:
            logger.info(f"Đã dọn dẹp {len(expired_ids)} công việc quá hạn TTL.")

job_manager = JobManager()

