@echo off
setlocal

set KEY=%USERPROFILE%\.ssh\hetzner_trading_bot
set HOST=root@2.29.39.13
set OPTS=-i "%KEY%" -o StrictHostKeyChecking=no

echo ================================================
echo   نشر المنصة على سيرفر Hetzner (2.29.39.13)
echo ================================================
echo.

echo [1/5] التحقق من الاتصال...
ssh %OPTS% %HOST% "echo connected"
if errorlevel 1 (
    echo فشل الاتصال بالسيرفر. تحقق من عنوان الـ IP والمفتاح.
    pause
    exit /b 1
)

echo [2/5] إنشاء مجلد التطبيق على السيرفر...
ssh %OPTS% %HOST% "mkdir -p /opt/trading-bot"

echo [3/5] رفع ملفات الـ backend والواجهة...
scp %OPTS% -r "%~dp0backend\app" %HOST%:/opt/trading-bot/
scp %OPTS% "%~dp0backend\requirements.txt" %HOST%:/opt/trading-bot/
scp %OPTS% "%~dp0backend\.env" %HOST%:/opt/trading-bot/
scp %OPTS% -r "%~dp0backend\static_frontend" %HOST%:/opt/trading-bot/

echo [4/5] رفع سكربت الإعداد...
scp %OPTS% "%~dp0deploy\setup-vps.sh" %HOST%:/root/setup-vps.sh

echo [5/5] تشغيل الإعداد على السيرفر (قد يأخذ دقيقة أو دقيقتين)...
ssh %OPTS% %HOST% "bash /root/setup-vps.sh"

echo.
echo ================================================
echo   انتهى النشر. افتح الرابط التالي للتأكد:
echo   http://2.29.39.13:8000/api/health
echo ================================================
pause
