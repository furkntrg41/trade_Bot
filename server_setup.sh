#!/bin/bash

# Server Setup Script
# Kullanım: bash server_setup.sh

set -e  # Hata durumunda dur

echo "========================================="
echo "  FREQTRADE BOT - SERVER KURULUMU"
echo "========================================="
echo ""

# Renkli çıktı
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Docker kontrolü
echo -e "${YELLOW}[1/8] Docker kontrolü...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker yüklü değil. Kuruluyor...${NC}"
    sudo apt update
    sudo apt install -y docker.io docker-compose git curl
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✓ Docker kuruldu${NC}"
else
    echo -e "${GREEN}✓ Docker zaten kurulu${NC}"
fi

# 2. Git kontrolü
echo -e "${YELLOW}[2/8] Git kontrolü...${NC}"
if ! command -v git &> /dev/null; then
    sudo apt install -y git
    echo -e "${GREEN}✓ Git kuruldu${NC}"
else
    echo -e "${GREEN}✓ Git zaten kurulu${NC}"
fi

# 3. Repository clone
echo -e "${YELLOW}[3/8] GitHub repository'yi klonla...${NC}"
read -p "GitHub repo URL (örn: https://github.com/user/freqtrade_bot.git): " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo -e "${RED}✗ URL girmediniz!${NC}"
    exit 1
fi

if [ -d "freqtrade_bot" ]; then
    echo -e "${YELLOW}freqtrade_bot klasörü mevcut. Güncelleniyor...${NC}"
    cd freqtrade_bot
    git pull
else
    git clone $REPO_URL
    cd freqtrade_bot
fi

echo -e "${GREEN}✓ Proje hazır${NC}"

# 4. API Keys
echo -e "${YELLOW}[4/8] API Keys ayarlanıyor...${NC}"
echo ""
echo "Binance API bilgilerinizi girin:"
read -p "API Key: " API_KEY
read -sp "API Secret: " API_SECRET
echo ""

# config_secrets.json oluştur
cat > config_secrets.json << EOF
{
    "exchange": {
        "key": "$API_KEY",
        "secret": "$API_SECRET"
    }
}
EOF

chmod 600 config_secrets.json
echo -e "${GREEN}✓ API keys kaydedildi${NC}"

# 5. config.json'da dry_run kontrolü
echo -e "${YELLOW}[5/8] Trading modu seçimi...${NC}"
echo "1) Dry Run (Test - Gerçek para kullanmaz)"
echo "2) Live Trading (GERÇEK PARA!)"
read -p "Seçiminiz (1/2): " TRADING_MODE

if [ "$TRADING_MODE" = "2" ]; then
    echo -e "${RED}UYARI: GERÇEK PARA İLE TRADİNG YAPILACAK!${NC}"
    read -p "Emin misiniz? (evet/hayir): " CONFIRM
    if [ "$CONFIRM" = "evet" ]; then
        sed -i 's/"dry_run": true/"dry_run": false/' config.json
        echo -e "${GREEN}✓ Live trading aktif${NC}"
    else
        echo -e "${YELLOW}Dry run modunda kalıyor${NC}"
    fi
else
    echo -e "${GREEN}✓ Dry run (test) modunda${NC}"
fi

# 6. Firewall
echo -e "${YELLOW}[6/8] Firewall ayarları...${NC}"
if command -v ufw &> /dev/null; then
    sudo ufw allow 8080/tcp
    echo -e "${GREEN}✓ Port 8080 açıldı${NC}"
else
    echo -e "${YELLOW}UFW yüklü değil, firewall atlanıyor${NC}"
fi

# 7. Docker build & start
echo -e "${YELLOW}[7/8] Docker container başlatılıyor...${NC}"
sudo docker-compose down 2>/dev/null || true
sudo docker-compose up -d --build

echo -e "${GREEN}✓ Container başlatıldı${NC}"

# 8. Health check
echo -e "${YELLOW}[8/8] Container durumu kontrol ediliyor...${NC}"
sleep 5
sudo docker-compose ps

echo ""
echo "========================================="
echo -e "${GREEN}  KURULUM TAMAMLANDI!${NC}"
echo "========================================="
echo ""
echo "📊 Log'ları izle:"
echo "   sudo docker-compose logs -f"
echo ""
echo "🛑 Durdur:"
echo "   sudo docker-compose stop"
echo ""
echo "🔄 Yeniden başlat:"
echo "   sudo docker-compose restart"
echo ""
echo "🌐 Web UI:"
echo "   http://$(curl -s ifconfig.me):8080"
echo ""
echo "✅ Bot 7/24 çalışıyor!"
