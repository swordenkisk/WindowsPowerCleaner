"""
Windows Power Cleaner - Scanner Module
مسح الملفات الكبيرة وتحليل المساحة
الإصدار: 2.0 - محسّن
"""

import os
from utils import format_size


# المجلدات التي يجب تجاهلها دائماً
SKIP_DIRS = {
    'windows\\system32',
    'windows\\syswow64',
    'windows\\winsxs',
    'program files\\windows',
    '$recycle.bin',
    'system volume information',
    'windows\\servicing',
    'windows\\installer',
}


class LargeFileScanner:
    """مسح وعرض الملفات الكبيرة في النظام"""

    def __init__(self, root_path='C:\\', min_size_mb=100):
        self.root_path = root_path
        self.min_size_mb = min_size_mb
        self.min_size_bytes = min_size_mb * 1024 * 1024
        self.large_files = []
        self.scanning = False
        self.scanned_count = 0
        self.error_count = 0

    def _should_skip(self, path):
        """تحقق إذا كان يجب تجاهل هذا المسار"""
        lower = path.lower()
        return any(skip in lower for skip in SKIP_DIRS)

    def scan(self, callback=None, progress_callback=None):
        """مسح الملفات الكبيرة"""
        self.large_files = []
        self.scanning = True
        self.scanned_count = 0
        self.error_count = 0

        try:
            for dirpath, dirnames, filenames in os.walk(self.root_path, topdown=True):
                if not self.scanning:
                    break

                # تجاهل مجلدات النظام الحساسة (في المكان لتجنب الدخول إليها)
                dirnames[:] = [
                    d for d in dirnames
                    if not self._should_skip(os.path.join(dirpath, d))
                ]

                for filename in filenames:
                    if not self.scanning:
                        break

                    filepath = os.path.join(dirpath, filename)
                    try:
                        if os.path.exists(filepath) and not os.path.islink(filepath):
                            size_bytes = os.path.getsize(filepath)
                            self.scanned_count += 1

                            if size_bytes >= self.min_size_bytes:
                                file_info = {
                                    'path': filepath,
                                    'size': size_bytes,
                                    'size_formatted': format_size(size_bytes),
                                    'name': filename,
                                    'folder': dirpath,
                                    'extension': os.path.splitext(filename)[1].lower()
                                }
                                self.large_files.append(file_info)

                                if callback:
                                    callback(file_info)

                            if progress_callback and self.scanned_count % 500 == 0:
                                progress_callback(self.scanned_count)

                    except (PermissionError, OSError):
                        self.error_count += 1
                        continue

        except Exception as e:
            print(f"خطأ في المسح: {e}")

        # ترتيب حسب الحجم تنازلياً
        self.large_files.sort(key=lambda x: x['size'], reverse=True)
        self.scanning = False
        return self.large_files

    def stop_scan(self):
        """إيقاف المسح"""
        self.scanning = False

    def get_summary(self):
        """ملخص نتائج المسح"""
        total_size = sum(f['size'] for f in self.large_files)
        return {
            'count': len(self.large_files),
            'total_size': total_size,
            'total_size_formatted': format_size(total_size),
            'scanned_files': self.scanned_count,
            'errors': self.error_count,
        }
