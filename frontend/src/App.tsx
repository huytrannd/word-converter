import { useState, useRef, useEffect, type DragEvent, type ChangeEvent } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, RefreshCw, Download, X } from 'lucide-react';

interface ConversionResponse {
  job_id: string;
  filename: string;
  file_size: number;
  page_count: number;
  status: 'pending' | 'validating' | 'converting' | 'generating_docx' | 'completed' | 'failed';
  message: string;
  error?: string | null;
  completed: boolean;
}

interface SystemStatus {
  status: string;
  api_key_configured: boolean;
  convert_mode: string;
  max_upload_mb: number;
  pandoc_available: boolean;
}

export default function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [pageCount, setPageCount] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentJob, setCurrentJob] = useState<ConversionResponse | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCompleted, setIsCompleted] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<number | null>(null);

  // Kiểm tra trạng thái hệ thống khi khởi động
  useEffect(() => {
    fetch('/api/system/status')
      .then(res => res.json())
      .then(data => setSystemStatus(data))
      .catch(() => {
        // Nếu không gọi được (ví dụ backend chưa bật), không làm sập giao diện
      });

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFile = (file: File) => {
    setErrorMessage(null);
    setIsCompleted(false);
    setCurrentJob(null);

    // Kiểm tra định dạng file
    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      setErrorMessage('Định dạng file không hợp lệ. Vui lòng chỉ chọn file PDF.');
      setSelectedFile(null);
      return;
    }

    // Kiểm tra dung lượng
    const maxMb = systemStatus?.max_upload_mb || 20;
    if (file.size > maxMb * 1024 * 1024) {
      setErrorMessage(`Dung lượng file vượt quá giới hạn cho phép (${maxMb} MB).`);
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setErrorMessage('File bạn chọn bị rỗng (0 bytes). Vui lòng chọn file khác.');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setPageCount(null);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isSubmitting) setIsDragging(true);
  };

  const onDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (isSubmitting) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const onFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  const resetSelection = () => {
    if (isSubmitting) return;
    if (pollingRef.current) clearInterval(pollingRef.current);
    setSelectedFile(null);
    setPageCount(null);
    setCurrentJob(null);
    setIsCompleted(false);
    setErrorMessage(null);
    setStatusMessage('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const startConversion = async () => {
    if (!selectedFile || isSubmitting) return;

    setIsSubmitting(true);
    setErrorMessage(null);
    setStatusMessage('Đang tải tài liệu...');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('/api/conversions', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Không thể gửi yêu cầu chuyển đổi.');
      }

      const job: ConversionResponse = await response.json();
      setCurrentJob(job);
      if (job.page_count > 0) setPageCount(job.page_count);

      // Bắt đầu polling theo dõi trạng thái
      pollJobStatus(job.job_id);

    } catch (err: any) {
      setIsSubmitting(false);
      setErrorMessage(err.message || 'Không thể chuyển đổi tài liệu này. Vui lòng thử lại bằng file PDF khác.');
    }
  };

  const pollJobStatus = (jobId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);

    pollingRef.current = window.setInterval(async () => {
      try {
        const res = await fetch(`/api/conversions/${jobId}`);
        if (!res.ok) {
          throw new Error('Lỗi khi kiểm tra tiến trình xử lý.');
        }

        const data: ConversionResponse = await res.json();
        setCurrentJob(data);

        if (data.page_count > 0) {
          setPageCount(data.page_count);
        }

        if (data.message) {
          setStatusMessage(data.message);
        }

        if (data.status === 'completed') {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setIsSubmitting(false);
          setIsCompleted(true);
          setStatusMessage('Chuyển đổi hoàn tất');
        } else if (data.status === 'failed') {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setIsSubmitting(false);
          setErrorMessage(data.error || 'Không thể chuyển đổi tài liệu này. Vui lòng thử lại bằng file PDF khác.');
        }
      } catch (err: any) {
        if (pollingRef.current) clearInterval(pollingRef.current);
        setIsSubmitting(false);
        setErrorMessage('Mất kết nối với máy chủ khi đang xử lý tài liệu. Vui lòng thử lại.');
      }
    }, 1500);
  };

  const downloadResult = () => {
    if (!currentJob) return;
    window.location.href = `/api/conversions/${currentJob.job_id}/download`;
  };

  return (
    <div className="min-h-screen bg-white text-[#292929] flex flex-col font-sans">
      {/* Header tối giản */}
      <header className="border-b border-[#F2CACA] py-4 px-6 md:px-12 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-2xl font-bold tracking-tight text-[#292929]">MathPDF</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-10 sm:py-16">
        <div className="w-full max-w-xl mx-auto flex flex-col items-center">
          
          {/* Tiêu đề chính */}
          <h1 className="text-3xl sm:text-4xl font-extrabold text-[#292929] text-center mb-3 tracking-tight">
            Chuyển PDF Toán sang Word
          </h1>
          <p className="text-base text-[#777777] text-center mb-8">
            Tải đề Toán PDF lên và chuyển thành file Word.
          </p>

          {/* Cảnh báo chưa cấu hình API key nếu có */}
          {systemStatus && !systemStatus.api_key_configured && (
            <div className="w-full mb-6 p-4 rounded-lg bg-[#FFF7F7] border border-[#F2CACA] flex items-start space-x-3 text-sm text-[#292929]">
              <AlertCircle className="w-5 h-5 text-[#E57373] flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-[#E57373]">Lưu ý dành cho người quản trị:</span> Chưa phát hiện biến môi trường <code className="bg-white px-1.5 py-0.5 rounded border border-[#F2CACA] text-xs font-mono">DATALAB_API_KEY</code> trong file <code className="bg-white px-1.5 py-0.5 rounded border border-[#F2CACA] text-xs font-mono">.env</code>. Vui lòng bổ sung khóa API trước khi thực hiện chuyển đổi trực tuyến.
              </div>
            </div>
          )}

          {/* Hộp thao tác chính */}
          <div className="w-full bg-white rounded-2xl border border-[#F2CACA] p-6 sm:p-8 shadow-sm transition-all">
            
            {/* 1. Trạng thái khi chưa chọn file */}
            {!selectedFile && !isCompleted && (
              <div
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                className={`border-2 border-dashed rounded-xl p-8 sm:p-12 text-center transition-colors flex flex-col items-center justify-center cursor-pointer ${
                  isDragging
                    ? 'border-[#E57373] bg-[#FFF7F7]'
                    : 'border-[#F2CACA] bg-white hover:bg-[#FFF7F7]'
                }`}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={onFileInputChange}
                  accept=".pdf,application/pdf"
                  className="hidden"
                />

                <div className="w-16 h-16 rounded-full bg-[#FFF7F7] flex items-center justify-center mb-4 text-[#E57373] border border-[#F2CACA]">
                  <Upload className="w-8 h-8" />
                </div>

                <p className="text-lg font-medium text-[#292929] mb-1">
                  Kéo thả file PDF vào đây
                </p>
                <p className="text-sm text-[#777777] mb-4">
                  hoặc
                </p>

                <button
                  type="button"
                  className="px-6 py-2.5 rounded-lg bg-[#E57373] hover:bg-[#D65F65] text-white font-medium text-sm transition-colors shadow-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                >
                  Chọn file PDF
                </button>
              </div>
            )}

            {/* 2. Trạng thái sau khi đã chọn file (chưa hoàn thành) */}
            {selectedFile && !isCompleted && (
              <div className="space-y-6">
                <div className="p-4 rounded-xl bg-[#FFF7F7] border border-[#F2CACA] flex items-center justify-between">
                  <div className="flex items-center space-x-3 overflow-hidden">
                    <div className="p-2.5 rounded-lg bg-white border border-[#F2CACA] text-[#E57373] flex-shrink-0">
                      <FileText className="w-6 h-6" />
                    </div>
                    <div className="overflow-hidden">
                      <p className="text-sm font-semibold text-[#292929] truncate max-w-[240px] sm:max-w-xs">
                        {selectedFile.name}
                      </p>
                      <p className="text-xs text-[#777777] mt-0.5">
                        {formatFileSize(selectedFile.size)}
                        {pageCount ? ` • ${pageCount} trang` : ''}
                      </p>
                    </div>
                  </div>

                  {!isSubmitting && (
                    <button
                      type="button"
                      onClick={resetSelection}
                      title="Xóa hoặc chọn file khác"
                      className="p-1.5 rounded-lg text-[#777777] hover:text-[#292929] hover:bg-white transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  )}
                </div>

                {/* Đang trong quá trình xử lý */}
                {isSubmitting && (
                  <div className="py-4 flex flex-col items-center justify-center space-y-3">
                    <div className="animate-spin text-[#E57373]">
                      <RefreshCw className="w-7 h-7" />
                    </div>
                    <p className="text-sm font-medium text-[#292929]">
                      {statusMessage || 'Đang xử lý tài liệu...'}
                    </p>
                  </div>
                )}

                {/* Thông báo lỗi nếu có */}
                {errorMessage && (
                  <div className="p-3.5 rounded-lg bg-[#FFF7F7] border border-[#F2CACA] flex items-start space-x-2 text-sm text-[#292929]">
                    <AlertCircle className="w-5 h-5 text-[#E57373] flex-shrink-0 mt-0.5" />
                    <p className="flex-1">{errorMessage}</p>
                  </div>
                )}

                {/* Nút hành động chính */}
                <div className="pt-2">
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={startConversion}
                    className={`w-full py-3 px-6 rounded-xl font-semibold text-white transition-colors flex items-center justify-center space-x-2 ${
                      isSubmitting
                        ? 'bg-[#E57373]/60 cursor-not-allowed'
                        : 'bg-[#E57373] hover:bg-[#D65F65] shadow-sm'
                    }`}
                  >
                    <span>{isSubmitting ? 'Đang chuyển đổi...' : 'Chuyển sang Word'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* 3. Trạng thái khi chuyển đổi thành công */}
            {isCompleted && (
              <div className="text-center py-6 space-y-5">
                <div className="w-16 h-16 rounded-full bg-[#FFF7F7] border border-[#F2CACA] text-[#E57373] mx-auto flex items-center justify-center">
                  <CheckCircle2 className="w-9 h-9" />
                </div>

                <div>
                  <h3 className="text-xl font-bold text-[#292929]">
                    Chuyển đổi hoàn tất
                  </h3>
                  <p className="text-xs text-[#777777] mt-1 truncate max-w-sm mx-auto">
                    {selectedFile?.name}
                  </p>
                </div>

                <div className="pt-2 flex flex-col sm:flex-row gap-3 justify-center">
                  <button
                    type="button"
                    onClick={downloadResult}
                    className="py-3 px-6 rounded-xl bg-[#E57373] hover:bg-[#D65F65] text-white font-semibold flex items-center justify-center space-x-2 shadow-sm transition-colors"
                  >
                    <Download className="w-5 h-5" />
                    <span>Tải xuống Word</span>
                  </button>

                  <button
                    type="button"
                    onClick={resetSelection}
                    className="py-3 px-6 rounded-xl bg-white hover:bg-[#FFF7F7] border border-[#F2CACA] text-[#292929] font-medium transition-colors"
                  >
                    Chuyển đổi file khác
                  </button>
                </div>
              </div>
            )}

          </div>

        </div>
      </main>

      {/* Footer tối giản */}
      <footer className="border-t border-[#F2CACA] py-5 text-center text-xs text-[#777777]">
        MathPDF — Công cụ chuyển đổi đề thi Toán sang file Word
      </footer>
    </div>
  );
}
