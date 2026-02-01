@echo off
chcp 65001 >nul
echo ========================================
echo   HETZNER SERVER'A OTOMATIK KURULUM
echo ========================================
echo.
echo Server: 91.95.133.146
echo User: root
echo.

set SERVER_IP=91.95.133.146
set SERVER_USER=root

echo GitHub repository URL'ini gir:
set /p GITHUB_URL="URL: "

if "%GITHUB_URL%"=="" (
    echo [HATA] URL girmediniz!
    pause
    exit /b 1
)

echo.
echo Binance API bilgilerini gir:
set /p API_KEY="API Key: "
set /p API_SECRET="API Secret: "

if "%API_KEY%"=="" (
    echo [HATA] API Key girmediniz!
    pause
    exit /b 1
)

echo.
echo [1/3] Server'a bağlanıyor...
echo.

REM SSH ile komutları çalıştır
ssh %SERVER_USER%@%SERVER_IP% "apt update && apt upgrade -y && apt install -y docker.io docker-compose git curl && systemctl start docker && systemctl enable docker"

echo.
echo [2/3] Projeyi çekiyor...
ssh %SERVER_USER%@%SERVER_IP% "cd /root && git clone %GITHUB_URL% || (cd freqtrade_bot && git pull)"

echo.
echo [3/3] API keys ayarlanıyor ve başlatılıyor...
ssh %SERVER_USER%@%SERVER_IP% "cd /root/freqtrade_bot && echo '{\"exchange\":{\"key\":\"%API_KEY%\",\"secret\":\"%API_SECRET%\"}}' > config_secrets.json && chmod 600 config_secrets.json && docker-compose up -d"

echo.
echo ========================================
echo   BAŞARILI! Bot çalışıyor.
echo ========================================
echo.
echo Web UI: http://91.95.133.146:8080
echo.
echo Log'ları görmek için:
echo   ssh %SERVER_USER%@%SERVER_IP% "cd /root/freqtrade_bot && docker-compose logs -f"
echo.
pause
