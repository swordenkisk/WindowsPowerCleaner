"""
Windows Power Cleaner - Cleaning Module
تنظيف الملفات المؤقتة والكاش
الإصدار: 2.0 - محسّن مع إصلاح الأخطاء
"""

import os
import shutil
import glob
import logging
import ctypes
from datetime import datetime
from utils import get_system_paths, get_folder_size, format_size

logger = logging.getLogger(__name__)


class SystemCleaner:
    """تنظيف ملفات النظام المؤقتة والكاش"""

    def __init__(self, dry_run=False, use_recycle_bin=True, status_callback=None):
        self.dry_run = dry_run
        self.use_recycle_bin = use_recycle_bin
        self.paths = get_system_paths()
        self.cleaned_size = 0
        self.cleaned_files = 0
        self.failed_files = 0
        self.status_callback = status_callback  # دالة لتحديث الواجهة
        self.running = True

    def _emit_status(self, message):
        """إرسال رسالة حالة"""
        logger.info(message)
        if self.status_callback:
            self.status_callback(message)

    def _safe_remove_file(self, filepath):
        """حذف ملف بأمان"""
        try:
            size = os.path.getsize(filepath)
            if not self.dry_run:
                if self.use_recycle_bin:
                    try:
                        from send2trash import send2trash
                        send2trash(filepath)
                    except Exception:
                        os.remove(filepath)
                else:
                    os.remove(filepath)
            self.cleaned_size += size
            self.cleaned_files += 1
            self._emit_status(f"✓ تم: {os.path.basename(filepath)} ({format_size(size)})")
            return True
        except PermissionError:
            self.failed_files += 1
            return False
        except FileNotFoundError:
            return False
        except Exception as e:
            self.failed_files += 1
            logger.warning(f"فشل حذف {filepath}: {e}")
            return False

    def _safe_remove_dir(self, dirpath):
        """حذف مجلد بأمان"""
        try:
            size = get_folder_size(dirpath)
            if not self.dry_run:
                if self.use_recycle_bin:
                    try:
                        from send2trash import send2trash
                        send2trash(dirpath)
                    except Exception:
                        shutil.rmtree(dirpath, ignore_errors=True)
                else:
                    shutil.rmtree(dirpath, ignore_errors=True)
            self.cleaned_size += size
            self.cleaned_files += 1
            return True
        except Exception as e:
            self.failed_files += 1
            logger.warning(f"فشل حذف المجلد {dirpath}: {e}")
            return False

    def _clean_folder(self, folder_path, pattern='*', recursive=False):
        """تنظيف محتويات مجلد"""
        if not os.path.exists(folder_path) or not self.running:
            return

        try:
            if recursive:
                for item in os.listdir(folder_path):
                    if not self.running:
                        break
                    item_path = os.path.join(folder_path, item)
                    if os.path.isfile(item_path):
                        self._safe_remove_file(item_path)
                    elif os.path.isdir(item_path):
                        self._safe_remove_dir(item_path)
            else:
                search_pattern = os.path.join(folder_path, pattern)
                for item in glob.glob(search_pattern):
                    if not self.running:
                        break
                    if os.path.isfile(item):
                        self._safe_remove_file(item)
                    elif os.path.isdir(item):
                        self._safe_remove_dir(item)
        except (PermissionError, OSError) as e:
            logger.warning(f"خطأ في تنظيف {folder_path}: {e}")

    def clean_temp_files(self):
        """تنظيف الملفات المؤقتة"""
        self._emit_status("🗂️ جاري تنظيف الملفات المؤقتة...")
        temp_paths = [
            self.paths.get('temp', ''),
            self.paths.get('windows_temp', ''),
            self.paths.get('local_temp', ''),
        ]
        for path in temp_paths:
            if path and os.path.exists(path):
                self._clean_folder(path, recursive=True)

    def clean_prefetch(self):
        """تنظيف مجلد Prefetch"""
        self._emit_status("⚡ جاري تنظيف Prefetch...")
        path = self.paths.get('prefetch', '')
        if path and os.path.exists(path):
            self._clean_folder(path, pattern='*.pf')

    def clean_recent_files(self):
        """تنظيف قائمة الملفات الحديثة"""
        self._emit_status("📋 جاري تنظيف الملفات الحديثة...")
        recent_paths = [
            self.paths.get('recent', ''),
            self.paths.get('recent_appdata', ''),
            os.path.join(self.paths.get('recent_appdata', ''), 'AutomaticDestinations'),
            os.path.join(self.paths.get('recent_appdata', ''), 'CustomDestinations'),
        ]
        for path in recent_paths:
            if path and os.path.exists(path):
                self._clean_folder(path, recursive=True)

    def clean_browser_cache(self):
        """تنظيف كاش المتصفحات"""
        self._emit_status("🌐 جاري تنظيف كاش المتصفحات...")

        # Chrome
        for key in ('chrome_cache', 'chrome_code_cache'):
            path = self.paths.get(key, '')
            if path and os.path.exists(path):
                self._clean_folder(path, recursive=True)

        # Edge
        edge_path = self.paths.get('edge_cache', '')
        if edge_path and os.path.exists(edge_path):
            self._clean_folder(edge_path, recursive=True)

        # Brave
        brave_path = self.paths.get('brave_cache', '')
        if brave_path and os.path.exists(brave_path):
            self._clean_folder(brave_path, recursive=True)

        # Opera
        opera_path = self.paths.get('opera_cache', '')
        if opera_path and os.path.exists(opera_path):
            self._clean_folder(opera_path, recursive=True)

        # Firefox - كل البروفايلات
        firefox_base = self.paths.get('firefox_profiles', '')
        if firefox_base and os.path.exists(firefox_base):
            try:
                for profile in os.listdir(firefox_base):
                    profile_path = os.path.join(firefox_base, profile)
                    for cache_dir in ('cache2', 'startupCache', 'thumbnails'):
                        cache_path = os.path.join(profile_path, cache_dir)
                        if os.path.exists(cache_path):
                            self._clean_folder(cache_path, recursive=True)
            except (PermissionError, OSError):
                pass

    def clean_windows_update_cache(self):
        """تنظيف كاش تحديثات الويندوز"""
        self._emit_status("🔄 جاري تنظيف كاش تحديثات الويندوز...")
        path = self.paths.get('software_distribution', '')
        if path and os.path.exists(path):
            self._clean_folder(path, recursive=True)

    def clean_dns_cache(self):
        """مسح كاش DNS"""
        if not self.dry_run:
            try:
                import subprocess
                subprocess.run(['ipconfig', '/flushdns'],
                               capture_output=True, timeout=10)
                self._emit_status("✓ تم مسح كاش DNS")
            except Exception as e:
                logger.warning(f"فشل مسح DNS: {e}")

    def clean_inet_cache(self):
        """تنظيف كاش الإنترنت"""
        self._emit_status("🌍 جاري تنظيف كاش الإنترنت...")
        path = self.paths.get('inet_cache', '')
        if path and os.path.exists(path):
            self._clean_folder(path, recursive=True)

    def clean_thumbnail_cache(self):
        """تنظيف كاش الصور المصغرة"""
        self._emit_status("🖼️ جاري تنظيف كاش الصور المصغرة...")
        path = self.paths.get('thumbnail_cache', '')
        if path and os.path.exists(path):
            self._clean_folder(path, pattern='thumbcache_*.db')

    def clean_recycle_bin(self):
        """تفريغ سلة المحذوفات"""
        self._emit_status("🗑️ جاري تفريغ سلة المحذوفات...")
        if not self.dry_run:
            try:
                # SHERB_NOCONFIRMATION=0x0001, SHERB_NOPROGRESSUI=0x0002, SHERB_NOSOUND=0x0004
                ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
                self._emit_status("✓ تم تفريغ سلة المحذوفات")
            except Exception as e:
                logger.warning(f"خطأ في تفريغ سلة المحذوفات: {e}")

    def stop(self):
        """إيقاف عملية التنظيف"""
        self.running = False

    def run_cleanup(self, mode='safe'):
        """تشغيل عملية التنظيف حسب الوضع المختار"""
        self.running = True
        self.cleaned_size = 0
        self.cleaned_files = 0
        self.failed_files = 0

        start_time = datetime.now()

        self._emit_status(f"\n{'='*50}")
        self._emit_status(f"🚀 بدء التنظيف - الوضع: {mode}")
        self._emit_status(f"المحاكاة: {'نعم ✓' if self.dry_run else 'لا'}")
        self._emit_status(f"{'='*50}\n")

        # الوضع الآمن - تنظيف أساسي
        if mode in ('safe', 'deep', 'nuclear'):
            self.clean_temp_files()
            self.clean_recent_files()
            self.clean_browser_cache()
            self.clean_inet_cache()
            self.clean_thumbnail_cache()

        # الوضع العميق - تنظيف إضافي
        if mode in ('deep', 'nuclear'):
            self.clean_prefetch()
            self.clean_windows_update_cache()
            self.clean_dns_cache()

        # الوضع الشامل - تنظيف كامل
        if mode == 'nuclear':
            self.clean_recycle_bin()

        elapsed = (datetime.now() - start_time).seconds

        self._emit_status(f"\n{'='*50}")
        self._emit_status(f"✅ اكتمل التنظيف في {elapsed} ثانية!")
        self._emit_status(f"الملفات المحذوفة: {self.cleaned_files}")
        self._emit_status(f"الملفات الفاشلة: {self.failed_files}")
        self._emit_status(f"المساحة المحررة: {format_size(self.cleaned_size)}")
        self._emit_status(f"{'='*50}\n")

        return {
            'files_deleted': self.cleaned_files,
            'files_failed': self.failed_files,
            'space_freed': self.cleaned_size,
            'elapsed_seconds': elapsed,
            'dry_run': self.dry_run,
        }
