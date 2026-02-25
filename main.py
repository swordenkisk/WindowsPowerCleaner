"""
Windows Power Cleaner v2.0
واجهة رسومية محسّنة لأداة تنظيف الويندوز الشاملة
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QGroupBox, QCheckBox, QPushButton, QLabel,
    QProgressBar, QTextEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QListWidget, QStatusBar, QMessageBox, QHeaderView, QSplitter,
    QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette

from utils import is_admin, request_admin, setup_logging, format_size, get_disk_info
from cleaner import SystemCleaner
from scanner import LargeFileScanner


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 6px;
    background-color: #181825;
}
QTabBar::tab {
    background-color: #313244;
    color: #cdd6f4;
    padding: 8px 18px;
    border-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
}
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 10px;
    padding: 10px;
    font-weight: bold;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    min-width: 90px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QPushButton:disabled {
    background-color: #181825;
    color: #585b70;
    border-color: #313244;
}
QPushButton#safe_btn { border-left: 4px solid #a6e3a1; }
QPushButton#deep_btn { border-left: 4px solid #f9e2af; }
QPushButton#nuclear_btn { border-left: 4px solid #f38ba8; }

QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 5px;
    height: 14px;
    text-align: center;
    color: #cdd6f4;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #89b4fa, stop:1 #b4befe);
    border-radius: 5px;
}
QTextEdit {
    background-color: #11111b;
    color: #a6e3a1;
    border: 1px solid #313244;
    border-radius: 6px;
    font-family: Consolas, monospace;
    font-size: 12px;
}
QTableWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    gridline-color: #313244;
    alternate-background-color: #1e1e2e;
}
QTableWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
}
QHeaderView::section {
    background-color: #313244;
    color: #89b4fa;
    padding: 6px;
    border: none;
    font-weight: bold;
}
QListWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
}
QListWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
}
QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border-radius: 3px;
    border: 1px solid #45475a;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px;
}
QStatusBar {
    background-color: #11111b;
    color: #6c7086;
    border-top: 1px solid #313244;
}
QLabel#disk_label {
    color: #89b4fa;
    font-weight: bold;
    font-size: 13px;
}
"""


class CleanerThread(QThread):
    """خيط لعملية التنظيف في الخلفية"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, cleaner, mode):
        super().__init__()
        self.cleaner = cleaner
        self.mode = mode

    def run(self):
        self.cleaner.status_callback = lambda msg: self.status.emit(msg)
        result = self.cleaner.run_cleanup(self.mode)
        self.finished.emit(result)


class ScannerThread(QThread):
    """خيط لمسح الملفات الكبيرة"""
    file_found = pyqtSignal(dict)
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)

    def __init__(self, scanner):
        super().__init__()
        self.scanner = scanner

    def run(self):
        files = self.scanner.scan(
            callback=lambda f: self.file_found.emit(f),
            progress_callback=lambda n: self.progress.emit(n % 100)
        )
        self.finished.emit(files)


class DiskWidget(QFrame):
    """عنصر عرض معلومات القرص"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        self.label = QLabel("📀 محرك C:")
        self.label.setObjectName("disk_label")
        layout.addWidget(self.label)

        layout.addStretch()

        self.bar = QProgressBar()
        self.bar.setFixedWidth(200)
        self.bar.setFixedHeight(12)
        layout.addWidget(self.bar)

        self.size_label = QLabel()
        layout.addWidget(self.size_label)

        self.refresh()

    def refresh(self):
        info = get_disk_info('C:\\')
        if info:
            pct = int(info['percent_used'])
            self.bar.setValue(pct)
            free_str = format_size(info['free'])
            total_str = format_size(info['total'])
            self.size_label.setText(f"  {free_str} متاح من {total_str}  ({pct}% مستخدم)")
            if pct > 90:
                self.bar.setStyleSheet("QProgressBar::chunk { background: #f38ba8; border-radius:5px; }")
            elif pct > 70:
                self.bar.setStyleSheet("QProgressBar::chunk { background: #f9e2af; border-radius:5px; }")


class MainWindow(QMainWindow):
    """النافذة الرئيسية للتطبيق"""

    def __init__(self):
        super().__init__()
        self.logger = setup_logging()
        self.cleaner = None
        self.scanner = None
        self.cleaner_thread = None
        self.scan_thread = None
        self.init_ui()
        self.check_admin()

    def check_admin(self):
        """التحقق من صلاحيات المدير"""
        if not is_admin():
            reply = QMessageBox.question(
                self, "صلاحيات المدير",
                "🔐 هذه الأداة تعمل بشكل أفضل بصلاحيات المدير.\n"
                "بعض الملفات لن يمكن حذفها بدون صلاحيات.\n\n"
                "هل تريد تشغيلها كمسؤول؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                request_admin()

    def init_ui(self):
        """تهيئة واجهة المستخدم"""
        self.setWindowTitle("🧹 Windows Power Cleaner v2.0")
        self.setGeometry(100, 100, 920, 680)
        self.setStyleSheet(DARK_STYLE)

        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 5)
        main_layout.setSpacing(8)

        # معلومات القرص
        self.disk_widget = DiskWidget()
        main_layout.addWidget(self.disk_widget)

        # تبويبات
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # تبويب التنظيف
        self.cleanup_tab = QWidget()
        tabs.addTab(self.cleanup_tab, "🧹 تنظيف النظام")
        self.setup_cleanup_tab()

        # تبويب الملفات الكبيرة
        self.files_tab = QWidget()
        tabs.addTab(self.files_tab, "📁 الملفات الكبيرة")
        self.setup_files_tab()

        # تبويب التقارير
        self.reports_tab = QWidget()
        tabs.addTab(self.reports_tab, "📊 التقارير")
        self.setup_reports_tab()

        # تبويب معلومات
        self.about_tab = QWidget()
        tabs.addTab(self.about_tab, "ℹ️ حول")
        self.setup_about_tab()

        # شريط الحالة
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        admin_txt = "🔐 مسؤول" if is_admin() else "⚠️ بدون صلاحيات كاملة"
        self.status_bar.showMessage(f"جاهز  |  {admin_txt}")

    def setup_cleanup_tab(self):
        """إعداد تبويب التنظيف"""
        layout = QVBoxLayout(self.cleanup_tab)
        layout.setSpacing(8)

        # خيارات التنظيف
        options_group = QGroupBox("⚙️ خيارات التنظيف")
        options_layout = QHBoxLayout()

        left_opts = QVBoxLayout()
        self.dry_run_check = QCheckBox("🔍 وضع المحاكاة (عرض ما سيتم حذفه دون تنفيذ)")
        self.dry_run_check.setChecked(True)
        left_opts.addWidget(self.dry_run_check)

        self.recycle_bin_check = QCheckBox("♻️ استخدام سلة المحذوفات (يمكن الاسترجاع)")
        self.recycle_bin_check.setChecked(True)
        left_opts.addWidget(self.recycle_bin_check)

        right_opts = QVBoxLayout()
        self.restore_point_check = QCheckBox("💾 إنشاء نقطة استعادة قبل التنظيف")
        right_opts.addWidget(self.restore_point_check)

        self.browser_cache_check = QCheckBox("🌐 تنظيف كاش المتصفحات")
        self.browser_cache_check.setChecked(True)
        right_opts.addWidget(self.browser_cache_check)

        options_layout.addLayout(left_opts)
        options_layout.addLayout(right_opts)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # أوضاع التنظيف
        modes_group = QGroupBox("🚀 اختر وضع التنظيف")
        modes_layout = QHBoxLayout()
        modes_layout.setSpacing(12)

        self.safe_btn = QPushButton("🟢 آمن\nملفات مؤقتة + كاش المتصفحات")
        self.safe_btn.setObjectName("safe_btn")
        self.safe_btn.setMinimumHeight(60)
        self.safe_btn.setToolTip("تنظيف آمن: ملفات مؤقتة، كاش المتصفحات، ملفات حديثة")
        self.safe_btn.clicked.connect(lambda: self.start_cleanup('safe'))
        modes_layout.addWidget(self.safe_btn)

        self.deep_btn = QPushButton("🟡 عميق\nمع Prefetch + تحديثات قديمة")
        self.deep_btn.setObjectName("deep_btn")
        self.deep_btn.setMinimumHeight(60)
        self.deep_btn.setToolTip("تنظيف عميق: يشمل Prefetch وكاش تحديثات الويندوز")
        self.deep_btn.clicked.connect(lambda: self.start_cleanup('deep'))
        modes_layout.addWidget(self.deep_btn)

        self.nuclear_btn = QPushButton("🔴 شامل جداً\nمع سلة المحذوفات + DNS")
        self.nuclear_btn.setObjectName("nuclear_btn")
        self.nuclear_btn.setMinimumHeight(60)
        self.nuclear_btn.setToolTip("⚠️ تنظيف كامل - يشمل تفريغ سلة المحذوفات")
        self.nuclear_btn.clicked.connect(lambda: self.start_cleanup('nuclear'))
        modes_layout.addWidget(self.nuclear_btn)

        self.stop_clean_btn = QPushButton("⏹️ إيقاف")
        self.stop_clean_btn.setMinimumHeight(60)
        self.stop_clean_btn.setEnabled(False)
        self.stop_clean_btn.clicked.connect(self.stop_cleanup)
        modes_layout.addWidget(self.stop_clean_btn)

        modes_group.setLayout(modes_layout)
        layout.addWidget(modes_group)

        # شريط التقدم
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # وضع غير محدد
        layout.addWidget(self.progress_bar)

        # منطقة النتائج
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("نتائج التنظيف ستظهر هنا...")
        layout.addWidget(self.results_text)

    def setup_files_tab(self):
        """إعداد تبويب الملفات الكبيرة"""
        layout = QVBoxLayout(self.files_tab)
        layout.setSpacing(8)

        # خيارات المسح
        scan_group = QGroupBox("🔍 خيارات المسح")
        scan_layout = QHBoxLayout()

        scan_layout.addWidget(QLabel("الحجم الأدنى:"))
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(10, 50000)
        self.min_size_spin.setValue(100)
        self.min_size_spin.setSuffix(" MB")
        self.min_size_spin.setFixedWidth(100)
        scan_layout.addWidget(self.min_size_spin)

        scan_layout.addWidget(QLabel("  المسار:"))
        self.path_label = QLabel("C:\\")
        scan_layout.addWidget(self.path_label)

        scan_layout.addStretch()

        self.scan_btn = QPushButton("🔍 بدء المسح")
        self.scan_btn.clicked.connect(self.start_scan)
        scan_layout.addWidget(self.scan_btn)

        self.stop_scan_btn = QPushButton("⏹️ إيقاف")
        self.stop_scan_btn.clicked.connect(self.stop_scan)
        self.stop_scan_btn.setEnabled(False)
        scan_layout.addWidget(self.stop_scan_btn)

        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)

        # شريط تقدم المسح
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setVisible(False)
        layout.addWidget(self.scan_progress)

        # جدول الملفات
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(["📄 اسم الملف", "📁 المجلد", "💾 الحجم", "☑️"])
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSortingEnabled(True)
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.files_table.setColumnWidth(3, 50)
        layout.addWidget(self.files_table)

        # ملخص المسح
        self.scan_summary = QLabel("لم يتم المسح بعد")
        self.scan_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.scan_summary)

        # أزرار الإجراءات
        actions_layout = QHBoxLayout()

        self.delete_selected_btn = QPushButton("🗑️ حذف المحدد")
        self.delete_selected_btn.clicked.connect(self.delete_selected_files)
        actions_layout.addWidget(self.delete_selected_btn)

        self.select_all_btn = QPushButton("☑️ تحديد الكل")
        self.select_all_btn.clicked.connect(self.select_all_files)
        actions_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("☐ إلغاء التحديد")
        self.deselect_all_btn.clicked.connect(self.deselect_all_files)
        actions_layout.addWidget(self.deselect_all_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

    def setup_reports_tab(self):
        """إعداد تبويب التقارير"""
        layout = QVBoxLayout(self.reports_tab)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # قائمة التقارير
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("📋 سجلات التنظيف:"))
        self.reports_list = QListWidget()
        self.reports_list.itemClicked.connect(self.preview_report)
        left_layout.addWidget(self.reports_list)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.clicked.connect(self.load_reports)
        btn_layout.addWidget(refresh_btn)

        open_btn = QPushButton("📂 فتح المجلد")
        open_btn.clicked.connect(self.open_logs_folder)
        btn_layout.addWidget(open_btn)

        view_btn = QPushButton("👁️ عرض")
        view_btn.clicked.connect(self.view_report)
        btn_layout.addWidget(view_btn)
        left_layout.addLayout(btn_layout)

        # معاينة التقرير
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("📄 معاينة:"))
        self.report_preview = QTextEdit()
        self.report_preview.setReadOnly(True)
        right_layout.addWidget(self.report_preview)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)

        self.load_reports()

    def setup_about_tab(self):
        """تبويب معلومات البرنامج"""
        layout = QVBoxLayout(self.about_tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        about_text = QLabel("""
<div style='text-align:center; color:#cdd6f4; font-family:Arial;'>
<h1 style='color:#89b4fa;'>🧹 Windows Power Cleaner</h1>
<h3 style='color:#a6e3a1;'>الإصدار 2.0</h3>
<br>
<p style='font-size:14px;'>أداة شاملة ومجانية لتنظيف وتحسين أداء Windows</p>
<br>
<table style='margin:auto; color:#cdd6f4;' cellpadding='8'>
<tr><td>🗂️ تنظيف الملفات المؤقتة</td><td>✅</td></tr>
<tr><td>🌐 كاش المتصفحات (Chrome, Edge, Firefox, Brave, Opera)</td><td>✅</td></tr>
<tr><td>⚡ ملفات Prefetch</td><td>✅</td></tr>
<tr><td>🔄 كاش تحديثات Windows</td><td>✅</td></tr>
<tr><td>🗑️ سلة المحذوفات</td><td>✅</td></tr>
<tr><td>🖼️ كاش الصور المصغرة</td><td>✅</td></tr>
<tr><td>🌍 مسح كاش DNS</td><td>✅</td></tr>
<tr><td>📁 مسح الملفات الكبيرة</td><td>✅</td></tr>
<tr><td>🔍 وضع المحاكاة</td><td>✅</td></tr>
</table>
<br>
<p style='color:#6c7086;'>مفتوح المصدر - مجاني للاستخدام الشخصي والتجاري</p>
</div>
        """)
        about_text.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(about_text)

    # ─── أحداث التنظيف ───────────────────────────────────────

    def start_cleanup(self, mode):
        """بدء عملية التنظيف"""
        if mode == 'nuclear':
            reply = QMessageBox.warning(
                self, "⚠️ تحذير",
                "الوضع الشامل سيحذف:\n"
                "• جميع الملفات المؤقتة\n"
                "• كاش كل المتصفحات\n"
                "• ملفات Prefetch\n"
                "• كاش تحديثات الويندوز\n"
                "• محتوى سلة المحذوفات\n\n"
                "هل أنت متأكد من الاستمرار؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if self.restore_point_check.isChecked() and is_admin():
            self._create_restore_point()

        self.cleaner = SystemCleaner(
            dry_run=self.dry_run_check.isChecked(),
            use_recycle_bin=self.recycle_bin_check.isChecked()
        )

        self.cleaner_thread = CleanerThread(self.cleaner, mode)
        self.cleaner_thread.status.connect(self.update_status)
        self.cleaner_thread.finished.connect(self.cleanup_finished)

        # تعطيل الأزرار
        for btn in (self.safe_btn, self.deep_btn, self.nuclear_btn):
            btn.setEnabled(False)
        self.stop_clean_btn.setEnabled(True)

        self.progress_bar.setVisible(True)
        self.results_text.clear()
        self.cleaner_thread.start()

    def stop_cleanup(self):
        """إيقاف التنظيف"""
        if self.cleaner:
            self.cleaner.stop()
        self.stop_clean_btn.setEnabled(False)

    def update_status(self, message):
        """تحديث حالة التطبيق"""
        self.status_bar.showMessage(message)
        self.results_text.append(message)
        # تمرير للأسفل
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def cleanup_finished(self, result):
        """اكتمال عملية التنظيف"""
        self.progress_bar.setVisible(False)
        for btn in (self.safe_btn, self.deep_btn, self.nuclear_btn):
            btn.setEnabled(True)
        self.stop_clean_btn.setEnabled(False)

        dry = " (محاكاة)" if result.get('dry_run') else ""
        msg = (
            f"✅ اكتمل التنظيف{dry}!\n\n"
            f"الملفات المعالجة: {result['files_deleted']}\n"
            f"الملفات الفاشلة: {result.get('files_failed', 0)}\n"
            f"المساحة المحررة: {format_size(result['space_freed'])}\n"
            f"الوقت: {result.get('elapsed_seconds', 0)} ثانية"
        )
        QMessageBox.information(self, "✅ تم", msg)
        self.disk_widget.refresh()
        self.load_reports()

    # ─── أحداث المسح ─────────────────────────────────────────

    def start_scan(self):
        """بدء مسح الملفات الكبيرة"""
        self.scanner = LargeFileScanner(
            root_path='C:\\',
            min_size_mb=self.min_size_spin.value()
        )

        self.scan_thread = ScannerThread(self.scanner)
        self.scan_thread.file_found.connect(self.add_file_to_table)
        self.scan_thread.progress.connect(self.scan_progress.setValue)
        self.scan_thread.finished.connect(self.scan_finished)

        self.files_table.setRowCount(0)
        self.files_table.setSortingEnabled(False)
        self.scan_btn.setEnabled(False)
        self.stop_scan_btn.setEnabled(True)
        self.scan_progress.setVisible(True)
        self.scan_summary.setText("🔍 جاري المسح...")

        self.scan_thread.start()

    def stop_scan(self):
        """إيقاف المسح"""
        if self.scanner:
            self.scanner.stop_scan()

    def add_file_to_table(self, file_info):
        """إضافة ملف إلى الجدول"""
        row = self.files_table.rowCount()
        self.files_table.insertRow(row)

        name_item = QTableWidgetItem(file_info['name'])
        folder_item = QTableWidgetItem(file_info['folder'])
        size_item = QTableWidgetItem(file_info['size_formatted'])

        # ترتيب صحيح بالحجم
        size_item.setData(Qt.ItemDataRole.UserRole, file_info['size'])

        self.files_table.setItem(row, 0, name_item)
        self.files_table.setItem(row, 1, folder_item)
        self.files_table.setItem(row, 2, size_item)

        from PyQt6.QtWidgets import QCheckBox as CB
        cb = CB()
        cb.setChecked(False)
        container = QWidget()
        cb_layout = QHBoxLayout(container)
        cb_layout.addWidget(cb)
        cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        self.files_table.setCellWidget(row, 3, container)

    def scan_finished(self, files):
        """اكتمال المسح"""
        self.scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.scan_progress.setVisible(False)
        self.files_table.setSortingEnabled(True)

        total = sum(f['size'] for f in files)
        self.scan_summary.setText(
            f"✅ تم العثور على {len(files)} ملف | الحجم الإجمالي: {format_size(total)}"
        )

    def delete_selected_files(self):
        """حذف الملفات المحددة"""
        selected = []
        for row in range(self.files_table.rowCount()):
            container = self.files_table.cellWidget(row, 3)
            if container:
                cb = container.findChild(type(container.children()[1]))
                if cb and cb.isChecked():
                    filepath = os.path.join(
                        self.files_table.item(row, 1).text(),
                        self.files_table.item(row, 0).text()
                    )
                    selected.append(filepath)

        if not selected:
            QMessageBox.warning(self, "⚠️ تنبيه", "لم يتم تحديد أي ملفات للحذف.")
            return

        reply = QMessageBox.question(
            self, "🗑️ تأكيد الحذف",
            f"هل أنت متأكد من حذف {len(selected)} ملف؟\n"
            "الملفات ستُنقل إلى سلة المحذوفات.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted = 0
            errors = 0
            for filepath in selected:
                try:
                    from send2trash import send2trash
                    send2trash(filepath)
                    deleted += 1
                except Exception as e:
                    errors += 1

            QMessageBox.information(
                self, "✅ تم",
                f"تم حذف {deleted} ملف بنجاح.\n"
                + (f"فشل: {errors} ملف." if errors else "")
            )
            self.disk_widget.refresh()
            self.start_scan()

    def select_all_files(self):
        """تحديد كل الملفات"""
        self._set_all_checked(True)

    def deselect_all_files(self):
        """إلغاء تحديد كل الملفات"""
        self._set_all_checked(False)

    def _set_all_checked(self, state):
        for row in range(self.files_table.rowCount()):
            container = self.files_table.cellWidget(row, 3)
            if container:
                from PyQt6.QtWidgets import QCheckBox as CB
                for child in container.findChildren(CB):
                    child.setChecked(state)

    # ─── التقارير ──────────────────────────────────────────────

    def load_reports(self):
        """تحميل قائمة التقارير"""
        self.reports_list.clear()
        log_dir = os.path.join(os.path.expanduser("~"), "WPC_Logs")

        if os.path.exists(log_dir):
            files = sorted(
                [f for f in os.listdir(log_dir) if f.endswith('.log')],
                reverse=True
            )[:30]
            for f in files:
                self.reports_list.addItem(f)

    def preview_report(self, item):
        """معاينة التقرير المحدد"""
        log_dir = os.path.join(os.path.expanduser("~"), "WPC_Logs")
        filepath = os.path.join(log_dir, item.text())
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.report_preview.setPlainText(f.read())
            except Exception:
                pass

    def view_report(self):
        """فتح التقرير بالتطبيق الافتراضي"""
        current = self.reports_list.currentItem()
        if current:
            log_dir = os.path.join(os.path.expanduser("~"), "WPC_Logs")
            filepath = os.path.join(log_dir, current.text())
            if os.path.exists(filepath):
                os.startfile(filepath)

    def open_logs_folder(self):
        """فتح مجلد السجلات"""
        log_dir = os.path.join(os.path.expanduser("~"), "WPC_Logs")
        os.makedirs(log_dir, exist_ok=True)
        os.startfile(log_dir)

    # ─── دوال مساعدة ──────────────────────────────────────────

    def _create_restore_point(self):
        """إنشاء نقطة استعادة النظام"""
        try:
            import subprocess
            subprocess.run([
                'powershell', '-Command',
                'Checkpoint-Computer -Description "WPC Restore Point" -RestorePointType MODIFY_SETTINGS'
            ], capture_output=True, timeout=30)
            self.status_bar.showMessage("✓ تم إنشاء نقطة استعادة")
        except Exception as e:
            self.logger.warning(f"فشل إنشاء نقطة الاستعادة: {e}")


def main():
    """نقطة الدخول الرئيسية"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
