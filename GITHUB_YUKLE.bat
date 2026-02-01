@echo off
echo ========================================
echo   FREQTRADE BOT - GITHUB'A YUKLEME
echo ========================================
echo.

REM Git yüklü mü kontrol et
git --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Git yuklu degil!
    echo https://git-scm.com/download/win adresinden indir
    pause
    exit /b 1
)

echo [1/6] Git repository'yi hazirlaniyor...
if not exist .git (
    git init
    echo Git repository olusturuldu.
) else (
    echo Git repository zaten mevcut.
)

echo.
echo [2/6] Dosyalar ekleniyor...
git add .

echo.
echo [3/6] Commit yapiliyor...
set /p COMMIT_MSG="Commit mesaji girin (varsayilan: 'Update'): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Update
git commit -m "%COMMIT_MSG%"

echo.
echo [4/6] GitHub repository URL'i gerekli!
echo GitHub'da yeni bir repo olustur: https://github.com/new
echo Sonra buraya URL'i yapistir.
echo Ornek: https://github.com/kullaniciadi/freqtrade_bot.git
echo.
set /p REPO_URL="GitHub repository URL: "

if "%REPO_URL%"=="" (
    echo [HATA] URL girmediniz!
    pause
    exit /b 1
)

echo.
echo [5/6] Remote repository ekleniyor...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo.
echo [6/6] GitHub'a gonderiliyor...
git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo [HATA] Push basarisiz! Muhtemel nedenler:
    echo - GitHub login gerekiyor
    echo - Repository izinleri yanlis
    echo - Network sorunu
    echo.
    echo Manuel olarak dene:
    echo git push -u origin main
    pause
    exit /b 1
)

echo.
echo ========================================
echo   BASARILI! GitHub'a yuklendi.
echo ========================================
echo.
echo Simdi server'da calistir:
echo   ssh root@SUNUCU_IP
echo   git clone %REPO_URL%
echo   cd freqtrade_bot
echo   sudo docker-compose up -d
echo.
pause
