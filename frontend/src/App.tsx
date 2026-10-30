import { useState, useRef, useEffect, type DragEvent, type ChangeEvent } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, Download, X } from 'lucide-react';

interface SystemStatus {
  status: string;
  api_key_configured: boolean;
  max_upload_mb: number;
  pandoc_available: boolean;
}

export default function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [pageCount, setPageCount] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [downloadFilename, setDownloadFilename] = useState('');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Kiểm tra trạng thái hệ thống khi khởi động
  useEffect(() => {
    fetch('/api/status')
      .then(res => res.json())
      .then(setSystemStatus)
      .catch(() => { /* backend chưa bật — không crash UI */ });
  }, []);

  // Giải phóng object URL khi không cần nữa
  useEffect(() => {
    return () => {
      if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    };
  }, [downloadUrl]);

  const formatFileSize = (bytes: number) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const s = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${s[i]}`;
  };

  const handleFile = (file: File) => {
    setErrorMessage(null);
    setDownloadUrl(null);

    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      setErrorMessage('Định dạng file không hợp lệ. Vui lòng chỉ chọn file PDF.');
      return;
    }
    const maxMb = systemStatus?.max_upload_mb ?? 20;
    if (file.size > maxMb * 1024 * 1024) {
      setErrorMessage(`Dung lượng file vượt quá giới hạn cho phép (${maxMb} MB).`);
      return;
    }
    if (file.size === 0) {
      setErrorMessage('File bạn chọn bị rỗng. Vui lòng chọn file khác.');
      return;
    }
    setSelectedFile(file);
    setPageCount(null);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault(); e.stopPropagation();
    if (!isProcessing) setIsDragging(true);
  };
  const onDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault(); e.stopPropagation();
    setIsDragging(false);
  };
  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault(); e.stopPropagation();
    setIsDragging(false);
    if (isProcessing) return;
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  };
  const onFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) handleFile(e.target.files[0]);
  };

  const resetAll = () => {
    if (isProcessing) return;
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    setSelectedFile(null);
    setPageCount(null);
    setDownloadUrl(null);
    setDownloadFilename('');
    setErrorMessage(null);
    setStatusMessage('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const startConversion = async () => {
    if (!selectedFile || isProcessing) return;

    setIsProcessing(true);
    setErrorMessage(null);
    setDownloadUrl(null);
    setStatusMessage('Đang tải tài liệu...');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setStatusMessage('Đang chuyển đổi...');

      const res = await fetch('https://word-converter-yx1f.onrender.com/api/convert', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        // Lấy thông báo lỗi từ server (đã được lọc, không chứa thông tin nhạy cảm)
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Không thể chuyển đổi tài liệu này. Vui lòng thử lại.');
      }

      setStatusMessage('Đang chuẩn bị file Word...');

      // Server trả file DOCX trực tiếp — đọc vào blob và tạo URL tải xuống
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      // Lấy tên file từ header Content-Disposition
      const disposition = res.headers.get('Content-Disposition') ?? '';
      const fnMatch = disposition.match(/filename="([^"]+)"/);
      const filename = fnMatch ? decodeURIComponent(fnMatch[1]) : `${selectedFile.name.replace(/\.pdf$/i, '')}.docx`;

      setDownloadUrl(url);
      setDownloadFilename(filename);
      setStatusMessage('Chuyển đổi hoàn tất');

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Không thể chuyển đổi tài liệu này. Vui lòng thử lại.';
      setErrorMessage(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  const triggerDownload = () => {
    if (!downloadUrl) return;
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = downloadFilename;
    a.click();
  };

  const isCompleted = !!downloadUrl && !isProcessing;

  return (
    <div className="min-h-screen bg-white text-[#292929] flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-[#F2CACA] py-4 px-6 md:px-12">
        <span className="text-2xl font-bold tracking-tight text-[#292929]">MathPDF</span>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-10 sm:py-16">
        <div className="w-full max-w-xl mx-auto flex flex-col items-center">

          <h1 className="text-3xl sm:text-4xl font-extrabold text-[#292929] text-center mb-3 tracking-tight">
            Chuyển PDF Toán sang Word
          </h1>
          <p className="text-base text-[#777777] text-center mb-8">
            Tải đề Toán PDF lên và chuyển thành file Word.
          </p>

          {/* Cảnh báo API key */}
          {systemStatus && !systemStatus.api_key_configured && (
            <div className="w-full mb-6 p-4 rounded-lg bg-[#FFF7F7] border border-[#F2CACA] flex items-start space-x-3 text-sm">
              <AlertCircle className="w-5 h-5 text-[#E57373] flex-shrink-0 mt-0.5" />
              <span>
                <strong className="text-[#E57373]">Lưu ý quản trị viên:</strong>{' '}
                Biến môi trường <code className="bg-white px-1 rounded border border-[#F2CACA] text-xs font-mono">DATALAB_API_KEY</code> chưa được cấu hình.
              </span>
            </div>
          )}

          {/* Card thao tác */}
          <div className="w-full bg-white rounded-2xl border border-[#F2CACA] p-6 sm:p-8 shadow-sm">

            {/* Chưa chọn file và chưa hoàn thành */}
            {!selectedFile && !isCompleted && (
              <div
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 sm:p-12 text-center cursor-pointer flex flex-col items-center transition-colors ${isDragging ? 'border-[#E57373] bg-[#FFF7F7]' : 'border-[#F2CACA] bg-white hover:bg-[#FFF7F7]'
                  }`}
              >
                <input
                  type="file" ref={fileInputRef} onChange={onFileInputChange}
                  accept=".pdf,application/pdf" className="hidden"
                />
                <div className="w-16 h-16 rounded-full bg-[#FFF7F7] flex items-center justify-center mb-4 text-[#E57373] border border-[#F2CACA]">
                  <Upload className="w-8 h-8" />
                </div>
                <p className="text-lg font-medium text-[#292929] mb-1">Kéo thả file PDF vào đây</p>
                <p className="text-sm text-[#777777] mb-4">hoặc</p>
                <button
                  type="button"
                  onClick={e => { e.stopPropagation(); fileInputRef.current?.click(); }}
                  className="px-6 py-2.5 rounded-lg bg-[#E57373] hover:bg-[#D65F65] text-white font-medium text-sm transition-colors shadow-sm"
                >
                  Chọn file PDF
                </button>
              </div>
            )}

            {/* Đã chọn file, chưa hoàn thành */}
            {selectedFile && !isCompleted && (
              <div className="space-y-5">
                {/* Thông tin file */}
                <div className="p-4 rounded-xl bg-[#FFF7F7] border border-[#F2CACA] flex items-center justify-between">
                  <div className="flex items-center space-x-3 overflow-hidden">
                    <div className="p-2.5 rounded-lg bg-white border border-[#F2CACA] text-[#E57373] flex-shrink-0">
                      <FileText className="w-6 h-6" />
                    </div>
                    <div className="overflow-hidden">
                      <p className="text-sm font-semibold text-[#292929] truncate max-w-[220px] sm:max-w-xs">
                        {selectedFile.name}
                      </p>
                      <p className="text-xs text-[#777777] mt-0.5">
                        {formatFileSize(selectedFile.size)}
                        {pageCount ? ` • ${pageCount} trang` : ''}
                      </p>
                    </div>
                  </div>
                  {!isProcessing && (
                    <button
                      onClick={resetAll}
                      title="Xóa hoặc chọn file khác"
                      className="p-1.5 rounded-lg text-[#777777] hover:text-[#292929] hover:bg-white transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  )}
                </div>

                {/* Trạng thái đang xử lý */}
                {isProcessing && (
                  <div className="py-4 flex flex-col items-center space-y-3">
                    <Loader2 className="w-7 h-7 text-[#E57373] animate-spin" />
                    <p className="text-sm font-medium text-[#292929]">{statusMessage}</p>
                    <p className="text-xs text-[#777777]">Có thể mất vài chục giây với tài liệu dài...</p>
                  </div>
                )}

                {/* Lỗi */}
                {errorMessage && (
                  <div className="p-3.5 rounded-lg bg-[#FFF7F7] border border-[#F2CACA] flex items-start space-x-2 text-sm">
                    <AlertCircle className="w-5 h-5 text-[#E57373] flex-shrink-0 mt-0.5" />
                    <p>{errorMessage}</p>
                  </div>
                )}

                {/* Nút chuyển đổi */}
                {!isProcessing && (
                  <button
                    onClick={startConversion}
                    className="w-full py-3 px-6 rounded-xl bg-[#E57373] hover:bg-[#D65F65] text-white font-semibold shadow-sm transition-colors"
                  >
                    Chuyển sang Word
                  </button>
                )}
              </div>
            )}

            {/* Hoàn thành */}
            {isCompleted && (
              <div className="text-center py-6 space-y-5">
                <div className="w-16 h-16 rounded-full bg-[#FFF7F7] border border-[#F2CACA] text-[#E57373] mx-auto flex items-center justify-center">
                  <CheckCircle2 className="w-9 h-9" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-[#292929]">Chuyển đổi hoàn tất</h3>
                  <p className="text-xs text-[#777777] mt-1 truncate max-w-sm mx-auto">{selectedFile?.name}</p>
                </div>
                <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
                  <button
                    onClick={triggerDownload}
                    className="py-3 px-6 rounded-xl bg-[#E57373] hover:bg-[#D65F65] text-white font-semibold flex items-center justify-center space-x-2 shadow-sm transition-colors"
                  >
                    <Download className="w-5 h-5" />
                    <span>Tải xuống Word</span>
                  </button>
                  <button
                    onClick={resetAll}
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

      {/* Footer */}
      <footer className="border-t border-[#F2CACA] py-5 text-center text-xs text-[#777777]">
        MathPDF — Công cụ chuyển đổi đề thi Toán sang file Word
      </footer>
    </div>
  );
}
