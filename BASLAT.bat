@echo off
echo ========================================
echo    FREQTRADE BOT BASLATILIYOR...
echo ========================================
cd /d C:\Users\furka\Desktop\freqtrade_bot
docker compose up -d
echo.
echo Bot baslatildi! Kontrol ediliyor...
timeout /t 5 /nobreak >nul
docker ps --format "table {{.Names}}\t{{.Status}}"
echo.
echo FreqUI aciliyor...
start http://localhost:8080
echo.
echo ========================================
echo [OK] Bot calisiyor
echo [OK] FreqUI: http://localhost:8080
echo [OK] Telegram'dan /status yazarak kontrol et
echo.
echo Kapatmak icin KAPAT.bat calistir
echo ========================================
pause
