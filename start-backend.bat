@echo off
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
echo.
echo ================================================
echo   تشغيل الـ Backend - راقب رسالة "OKX public WS connected"
echo   لإيقاف السيرفر: اضغط CTRL+C
echo ================================================
echo.
uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
