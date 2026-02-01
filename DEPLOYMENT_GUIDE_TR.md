# 🚀 Cloud Sunucuda 7/24 Deployment Guide

## 1️⃣ Sunucu Seçimi (Önerilen)

| Sağlayıcı | Spec | Fiyat/Ay | Uygunluk |
|-----------|------|----------|---------|
| **DigitalOcean** | 4GB RAM, 2 vCPU | $24 | ✅ Harika (App Platform ile auto-deploy) |
| **Linode** | 4GB RAM, 2 vCPU | $24 | ✅ Güvenilir |
| **AWS** | t3.medium | ~$35 | ⚠️ Biraz pahalı ama scalable |
| **Hetzner** | 4GB RAM, 2 vCPU | €7-10 | ✅ En ucuz |
| **Vultr** | 2GB RAM, 1 vCPU | $6 | ⚠️ Minimum config |

---

## 2️⃣ Sunucuya SSH Bağlantısı (Linux)

```bash
# SSH key oluştur (eğer yoksa)
ssh-keygen -t rsa -b 4096

# Sunucuya bağlan
ssh root@SUNUCU_IP

# Docker & Docker Compose kur
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose git

# Docker daemon başlat
sudo systemctl start docker
sudo systemctl enable docker

# Current user'ı docker group'a ekle (sudo olmadan çalıştırmak için)
sudo usermod -aG docker $USER
```

---

## 3️⃣ Projeyi Sunucuya Yükle

```bash
# SSH ile sunucuya bağlan
ssh root@SUNUCU_IP

# Projeyi clone et (GitHub'dan)
git clone https://github.com/SENIN_REPO/freqtrade_bot.git
cd freqtrade_bot

# Alternatif: SCP ile upload et
scp -r freqtrade_bot root@SUNUCU_IP:/root/
```

---

## 4️⃣ API Keys'i Güvenli Şekilde Ekle

```bash
# Secrets dosyası oluştur (BAŞTA BU!)
cat > config_secrets.json << 'EOF'
{
    "exchange": {
        "key": "YOUR_BINANCE_API_KEY",
        "secret": "YOUR_BINANCE_API_SECRET"
    }
}
EOF

# Dosya izinlerini kısıtla
chmod 600 config_secrets.json

# config.json'da bunu ekle:
# "exchange": { "__include_secrets": ["config_secrets.json"] }
```

---

## 5️⃣ Docker Container'ı Başlat

```bash
# Sunucuda
cd /root/freqtrade_bot

# Build et (ilk kez)
docker-compose build

# Container'ı başlat (detached mode - arka planda)
docker-compose up -d

# Log'ları kontrol et
docker-compose logs -f freqtrade

# Container'ın durumunu kontrol et
docker-compose ps
```

---

## 6️⃣ Erişim & Monitoring

### Web Dashboard'a Erişim
```
http://SUNUCU_IP:8080
```

### SSH Üzerinden Log İzle
```bash
docker-compose logs -f --tail=100
```

### Container Restart
```bash
docker-compose restart freqtrade
```

### Container Stop (Acil Durum)
```bash
docker-compose down
```

---

## 7️⃣ Auto-Restart & Backup

### Sunucuya SSH ile bağlan ve cron job ekle

```bash
# Her gün saat 02:00'de backup al
crontab -e

# Aşağıdakini ekle:
0 2 * * * cd /root/freqtrade_bot && tar -czf user_data_backup_$(date +\%Y\%m\%d).tar.gz user_data/ && find . -name "user_data_backup_*.tar.gz" -mtime +7 -delete
```

---

## 8️⃣ Sorun Giderme

### Container devamlı restart atıyor?
```bash
docker-compose logs freqtrade  # Hata mesajını gör
```

### Port 8080 zaten kullanılıyor?
```bash
# docker-compose.yml'de değiştir:
ports:
  - "0.0.0.0:9090:8080"  # 9090'a değiştir
```

### RAM yetmiyor?
```bash
# compose'ta memory limitini azalt:
memory: 8G  # 6G veya 4G'e düşür
```

### Binance connection sorunu?
```bash
# DNS kontrol et
docker exec freqtrade_bot curl -I https://api.binance.com
```

---

## 9️⃣ Güvenlik İpuçları 🔒

✅ **YAPILMASI GEREKENLER:**
- SSH port'u değiştir: `22 → 2222`
- Firewall kur: `sudo ufw enable`
- SSH key authentication kullan (password değil)
- API keys'i `.env` ya da `config_secrets.json`'da sakla
- Sunucu firewall'ında port 8080'i kısıtla (VPN arkasında tutmanı öner)

❌ **YAPILMAMASI GEREKENLER:**
- API keys'i config.json'da açık tutma
- SSH password authentication'ı açık tutma
- Tüm portları internet'e açma

---

## 🔟 Kontrol Listesi

- [ ] Sunucu seç ve kirayala
- [ ] Docker & Docker Compose kur
- [ ] Projeyi sunucuya yükle
- [ ] API keys'i ekle (secrets dosyasında)
- [ ] `docker-compose up -d` çalıştır
- [ ] `http://SUNUCU_IP:8080` açarak doğrula
- [ ] Log'ları kontrol et
- [ ] Backup cron job'u kur
- [ ] Firewall kuralları ayarla
- [ ] Test trade yap (dry_run mode'de)

---

## 📊 İyi Bilmeniz Gerekenler

- **Dry Run**: Para harcamayan test modu. İlk başta bunu kullan! ✅
- **Live Trading**: Gerçek para harca. Dikkatli ol! ⚠️
- **Backtesting**: Geçmiş verilerle test et deployment'tan önce
- **Model Training**: İlk bağlantıda FreqAI model'i eğitecek (5-10 dakika)
- **Disk Space**: Feather dosyaları önemli yer kaplıyor. 50GB disk öner

