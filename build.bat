@echo off
echo ========================================
echo   Windows Power Cleaner - Build Script
echo ========================================
echo.

:: التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python غير مثبت! قم بتثبيته من python.org
    pause
    exit /b 1
)

:: تثبيت المتطلبات
echo [1/3] تثبيت المكتبات المطلوبة...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] فشل تثبيت المكتبات
    pause
    exit /b 1
)

:: تثبيت PyInstaller
echo.
echo [2/3] تثبيت PyInstaller...
pip install pyinstaller

:: بناء الملف التنفيذي
echo.
echo [3/3] بناء ملف .exe ...

if exist "icon.ico" (
    pyinstaller --onefile --windowed --name "WindowsPowerCleaner" --icon=icon.ico --add-data "*.py;." main.py
) else (
    pyinstaller --onefile --windowed --name "WindowsPowerCleaner" --add-data "*.py;." main.py
)

if errorlevel 1 (
    echo [ERROR] فشل بناء الملف التنفيذي
    pause
    exit /b 1
)

echo.
echo ========================================
echo  تم بنجاح! الملف موجود في مجلد dist/
echo ========================================
pause
