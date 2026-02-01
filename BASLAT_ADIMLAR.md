# 🚀 HETZNER SERVER KURULUM - ADIM ADIM

## ⚠️ ÖNEMLİ: Server Henüz Başlatılmamış

Hetzner panelinden server'ın AÇIK olması gerekiyor.

---

## ADIM 1: Hetzner Console'dan Server'ı Başlat

1. **Hetzner Console'a git:** https://console.hetzner.cloud/
2. **CPX22** server'ına tıkla (ubuntu-4gb-nbg1-1)
3. Eğer **OFF** ise, **"Actions" > "Power On"** yap
4. Server **ON** olana kadar bekle (30-60 saniye)

---

## ADIM 2: SSH Key Ekle (İlk Kez İçin)

### Windows PowerShell'de SSH key oluştur:

```powershell
# SSH key oluştur (eğer yoksa)
ssh-keygen -t rsa -b 4096 -f $env:USERPROFILE\.ssh\hetzner_key

# Public key'i göster
Get-Content $env:USERPROFILE\.ssh\hetzner_key.pub
```

### Hetzner Console'da:
1. **Security** > **SSH Keys** > **Add SSH Key**
2. Public key'i yapıştır (yukarıdaki komutun çıktısı)
3. Name: "windows-laptop"
4. **Add SSH Key**

### Server'a key'i ekle:
1. **Servers** > **CPX22**
2. **Rescue** > **Enable rescue & power cycle** 
3. VEYA Hetzner Console > **Launch Console** (web tabanlı terminal)
4. Root şifresiyle giriş yap: `acaanYM3EsuP`

```bash
# Server'da (Hetzner web console'dan)
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "BURAYA_PUBLIC_KEY_YAPIŞTIR" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

---

## ADIM 3: Windows'tan SSH ile Bağlan

```powershell
# Şifre ile bağlan (ilk kez)
ssh root@91.95.133.146

# VEYA SSH key ile
ssh -i $env:USERPROFILE\.ssh\hetzner_key root@91.95.133.146
```

---

## ADIM 4: Otomatik Kurulum (Server'da)

Server'a bağlandıktan sonra bu komutu çalıştır:

```bash
curl -fsSL https://raw.githubusercontent.com/furkntrg41/trade_Bot/main/server_setup.sh | bash
```

VEYA manuel:

```bash
# Docker kur
apt update && apt upgrade -y
apt install -y docker.io docker-compose git curl
systemctl start docker
systemctl enable docker

# Proje çek
cd /root
git clone https://github.com/furkntrg41/trade_Bot.git
cd trade_Bot

# API keys ekle (Binance bilgilerini gir)
cat > config_secrets.json << 'EOF'
{
    "exchange": {
        "key": "BINANCE_API_KEY_BURAYA",
        "secret": "BINANCE_API_SECRET_BURAYA"
    }
}
EOF

chmod 600 config_secrets.json

# Başlat
docker-compose up -d

# Log'ları izle
docker-compose logs -f
```

---

## ADIM 5: Kontrol

```bash
# Container durumu
docker-compose ps

# Log'lar
docker-compose logs -f freqtrade

# Web UI
# Tarayıcıdan: http://91.95.133.146:8080
```

---

## 🔥 HIZLI BAŞLATMA (Tek Komut)

Server'a bağlandıktan sonra:

```bash
cd /root && \
apt update && apt install -y docker.io docker-compose git && \
systemctl start docker && systemctl enable docker && \
git clone https://github.com/furkntrg41/trade_Bot.git && \
cd trade_Bot && \
read -p "Binance API Key: " API_KEY && \
read -sp "Binance API Secret: " API_SECRET && \
echo "{\"exchange\":{\"key\":\"$API_KEY\",\"secret\":\"$API_SECRET\"}}" > config_secrets.json && \
chmod 600 config_secrets.json && \
docker-compose up -d && \
echo -e "\n\n✅ BOT BAŞLATILDI!\nWeb UI: http://91.95.133.146:8080" && \
docker-compose logs -f
```

---

## ❌ SORUN GİDERME

### "Connection timed out" hatası:
- Server **ON** mu? (Hetzner Console'dan kontrol et)
- Firewall kapalı mı? Server'da: `ufw status`
- SSH port açık mı? `netstat -tulpn | grep 22`

### "Permission denied":
- Root şifresi doğru mu? `acaanYM3EsuP`
- SSH key doğru mu? `~/.ssh/authorized_keys` kontrol et

### Docker çalışmıyor:
```bash
systemctl status docker
systemctl restart docker
journalctl -u docker -n 50
```

---

## 📱 MOBİL: Hetzner App

Telefondan yönetmek için:
- **iOS:** https://apps.apple.com/app/hetzner-cloud/id1156813748
- **Android:** https://play.google.com/store/apps/details?id=com.hetzner.cloud

---

## ✅ BAŞARILI KURULUM SONRASI

Bot çalışıyorsa göreceğin log'lar:
```
✅ Docker container başladı
✅ FreqAI modeli yüklendi
✅ WebSocket bağlantısı kuruldu
✅ Pairs izleniyor: 10 pairs
📊 Signal bekleniyor...
```

Web UI: **http://91.95.133.146:8080**

---

## 🛠️ SONRAKI ADIMLAR

1. **Dry run test et:** 24 saat izle
2. **Gerçek trading:** `config.json` > `"dry_run": false`
3. **Monitoring:** Telegram bot ekle (opsiyonel)
4. **Backup:** Otomatik backup setup

---

**Sorular için burdayım! Server açıldıktan sonra devam edelim.**
