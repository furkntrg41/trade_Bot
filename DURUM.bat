@echo off
echo ========================================
echo    FREQTRADE BOT DURUMU
echo ========================================
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.
echo SON LOGLAR:
echo ----------------------------------------
docker logs freqtrade_bot --tail 10
echo ========================================
pause
