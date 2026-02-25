"""
Windows Power Cleaner - Utilities Module
المهام المساعدة: الصلاحيات، السجلات، التفاعل مع النظام
الإصدار: 2.0 - محسّن
"""

import os
import sys
import ctypes
import logging
import subprocess
from datetime import datetime
import tempfile


def setup_logging():
    """إعداد نظام التسجيل لحفظ سجلات التنظيف"""
    log_dir = os.path.join(os.path.expanduser("~"), "WPC_Logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"cleaner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def is_admin():
    """التحقق ما إذا كان البرنامج يعمل بصلاحيات المدير"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def request_admin():
    """طلب صلاحيات المدير وإعادة التشغيل"""
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()


def get_system_paths():
    """الحصول على مسارات النظام الهامة"""
    local_app = os.environ.get('LOCALAPPDATA', '')
    app_data = os.environ.get('APPDATA', '')
    user_profile = os.environ.get('USERPROFILE', os.path.expanduser('~'))

    paths = {
        'temp': os.environ.get('TEMP', tempfile.gettempdir()),
        'windows_temp': r'C:\Windows\Temp',
        'prefetch': r'C:\Windows\Prefetch',
        'recent': os.path.join(user_profile, 'Recent'),
        'cookies': os.path.join(local_app, 'Microsoft', 'Windows', 'Cookies'),
        'history': os.path.join(local_app, 'Microsoft', 'Windows', 'History'),
        'inet_cache': os.path.join(local_app, 'Microsoft', 'Windows', 'INetCache'),
        'local_temp': os.path.join(local_app, 'Temp'),
        'thumbnail_cache': os.path.join(local_app, 'Microsoft', 'Windows', 'Explorer'),
        'software_distribution': r'C:\Windows\SoftwareDistribution\Download',
        'recent_appdata': os.path.join(app_data, 'Microsoft', 'Windows', 'Recent'),
        # متصفحات
        'chrome_cache': os.path.join(local_app, 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
        'chrome_code_cache': os.path.join(local_app, 'Google', 'Chrome', 'User Data', 'Default', 'Code Cache'),
        'edge_cache': os.path.join(local_app, 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
        'brave_cache': os.path.join(local_app, 'BraveSoftware', 'Brave-Browser', 'User Data', 'Default', 'Cache'),
        'firefox_profiles': os.path.join(app_data, 'Mozilla', 'Firefox', 'Profiles'),
        'opera_cache': os.path.join(app_data, 'Opera Software', 'Opera Stable', 'Cache'),
    }
    return paths


def get_folder_size(folder_path):
    """حساب حجم المجلد بالبايت"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    if os.path.exists(fp) and not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
                except (PermissionError, OSError):
                    pass
    except (PermissionError, FileNotFoundError):
        pass
    return total_size


def format_size(size_bytes):
    """تحويل الحجم من بايت إلى صيغة مقروءة"""
    if size_bytes <= 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.2f} {size_names[i]}"


def get_disk_info(drive='C:\\'):
    """الحصول على معلومات القرص"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(drive)
        return {
            'total': total,
            'used': used,
            'free': free,
            'percent_used': (used / total) * 100
        }
    except Exception:
        return None
