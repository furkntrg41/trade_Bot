# 🚀 SERVER'A YÜKLEME REHBERİ

## Seçenek 1️⃣: SCP ile Dosya Transfer (EN KOLAY)

### Windows PowerShell'den:

```powershell
# 1. Önce dosyaları zip'le
Compress-Archive -Path "C:\Users\furka\Desktop\freqtrade_bot\*" -DestinationPath "C:\Users\furka\Desktop\freqtrade_bot.zip"

# 2. WinSCP kullan (GUI)
# https://winscp.net/eng/download.php indir
# Server IP, kullanıcı adı, şifre gir
# freqtrade_bot.zip dosyasını sürükle-bırak
```

### Server'da (SSH ile bağlandıktan sonra):

```bash
# ZIP'i aç
unzip freqtrade_bot.zip -d freqtrade_bot
cd freqtrade_bot

# Docker'ı başlat
sudo docker-compose up -d

# Log'ları izle
sudo docker-compose logs -f
```

---

## Seçenek 2️⃣: Git ile (ÖNERİLEN)

### GitHub'a yükle:

```powershell
# Windows'ta proje klasöründe
cd C:\Users\furka\Desktop\freqtrade_bot

# Git init (eğer yapılmadıysa)
git init
git add .
git commit -m "Initial commit"

# GitHub'da yeni repo oluştur, sonra:
git remote add origin https://github.com/KULLANICI_ADIN/freqtrade_bot.git
git branch -M main
git push -u origin main
```

### Server'da:

```bash
# SSH ile bağlan
ssh root@SUNUCU_IP

# Docker kur (eğer yoksa)
sudo apt update
sudo apt install -y docker.io docker-compose git

# Projeyi çek
git clone https://github.com/KULLANICI_ADIN/freqtrade_bot.git
cd freqtrade_bot

# Başlat
sudo docker-compose up -d
```

---

## ⚠️ ÖNEMLİ: API Key'leri Güvenli Ekle

```bash
# Server'da
cd freqtrade_bot

# Secrets dosyası oluştur
nano config_secrets.json
```

**config_secrets.json içeriği:**
```json
{
    "exchange": {
        "key": "GERÇEK_BINANCE_API_KEY",
        "secret": "GERÇEK_BINANCE_API_SECRET"
    }
}
```

**config.json'ı güncelle:**
```json
{
    "exchange": {
        "name": "binance",
        "key": "${API_KEY}",
        "secret": "${API_SECRET}",
        ...
    }
}
```

Veya environment variable kullan:
```bash
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
```

---

## 🔧 SORUN GİDERME

### 1. Docker çalışmıyorsa:
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Port kapalıysa:
```bash
sudo ufw allow 8080/tcp
sudo ufw status
```

### 3. Container log'unu kontrol et:
```bash
sudo docker-compose logs freqtrade
```

### 4. Container'ı yeniden başlat:
```bash
sudo docker-compose restart
```

### 5. Tamamen temizleyip baştan:
```bash
sudo docker-compose down
sudo docker-compose up -d --build
```

---

## 📊 MONİTORİNG

```bash
# Container durumu
sudo docker-compose ps

# Log'ları canlı izle
sudo docker-compose logs -f freqtrade

# Resource kullanımı
sudo docker stats freqtrade_bot

# Web UI erişimi
http://SUNUCU_IP:8080
```

---

## 🛑 DURDURMA & KAPATMA

```bash
# Güvenli durdur (pozisyonları kapat)
sudo docker-compose stop

# Tamamen kaldır
sudo docker-compose down

# Tamamen temizle (volume'lar dahil)
sudo docker-compose down -v
```

---

## 💡 HIZLI BAŞLATApproach

```bash
# Tek komutla her şey
ssh root@SUNUCU_IP "cd freqtrade_bot && sudo docker-compose up -d && sudo docker-compose logs -f"
```

---

## 📝 CHECKLIST

- [ ] Server'da Docker kurulu mu? (`docker --version`)
- [ ] Git kurulu mu? (`git --version`)
- [ ] API keys config_secrets.json'da mı?
- [ ] config.json'da dry_run: false yaptın mı? (gerçek trade için)
- [ ] Port 8080 açık mı? (`sudo ufw status`)
- [ ] Container çalışıyor mu? (`sudo docker-compose ps`)
- [ ] Log'da hata var mı? (`sudo docker-compose logs`)

---

## 🎯 SONUÇ

✅ Server'a atmak için **en kolay yol**: Git kullan
✅ Güvenlik için API keys'i ayrı dosyada tut
✅ Docker ile başlat, 7/24 çalışır
✅ Log'ları sürekli kontrol et

**Herhangi bir hata alırsan, log çıktısını gönder yardımcı olayım!**
