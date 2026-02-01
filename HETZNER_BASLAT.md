# 🚀 HETZNER SERVER'A YÜKLEME

## Server Bilgileri
- **IP:** 91.95.133.146
- **Kullanıcı:** root
- **Şifre:** acaanYM3EsuP
- **Sistem:** Ubuntu 4GB RAM

---

## ADIM 1: SSH ile Bağlan

### Windows PowerShell'den:
```powershell
ssh root@91.95.133.146
# Şifre: acaanYM3EsuP
```

### İlk giriş sorusu gelirse "yes" yaz

---

## ADIM 2: Server'da Docker Kur

```bash
# Sistem güncellemesi
apt update && apt upgrade -y

# Docker kur
apt install -y docker.io docker-compose git curl

# Docker'ı başlat
systemctl start docker
systemctl enable docker

# Kontrol et
docker --version
docker-compose --version
```

---

## ADIM 3: GitHub'dan Projeyi Çek

```bash
# Ana dizine git
cd /root

# Projeyi klonla (GitHub repo URL'ini kullan)
git clone https://github.com/KULLANICI_ADIN/freqtrade_bot.git

# Proje klasörüne gir
cd freqtrade_bot
```

---

## ADIM 4: API Keys Ekle

```bash
# API keys dosyasını oluştur
nano config_secrets.json
```

**İçerik (kendi bilgilerinle değiştir):**
```json
{
    "exchange": {
        "key": "GERÇEK_BINANCE_API_KEY",
        "secret": "GERÇEK_BINANCE_API_SECRET"
    }
}
```

**Kaydet:** `Ctrl+O`, Enter, `Ctrl+X`

```bash
# Dosya izinlerini kısıtla
chmod 600 config_secrets.json
```

---

## ADIM 5: config.json'u Güncelle (OPSIYONEL)

Dry run modundan çıkmak için (gerçek trading):
```bash
nano config.json
# "dry_run": true -> "dry_run": false yap
```

---

## ADIM 6: Docker Container Başlat

```bash
# Container'ı oluştur ve başlat
docker-compose up -d

# Log'ları izle
docker-compose logs -f freqtrade
```

---

## ADIM 7: Firewall (Gerekirse)

```bash
# Port 8080'i aç (Web UI için)
ufw allow 8080/tcp
ufw enable
```

---

## 📊 KONTROL KOMANTLARı

```bash
# Container durumu
docker-compose ps

# Log'lar
docker-compose logs -f

# Yeniden başlat
docker-compose restart

# Durdur
docker-compose stop

# Tamamen kaldır
docker-compose down
```

---

## 🌐 WEB UI ERİŞİM

Tarayıcıdan:
```
http://91.95.133.146:8080
```

---

## 🔄 GÜNCELLEME (GitHub'dan)

```bash
cd /root/freqtrade_bot
git pull
docker-compose up -d --build
```

---

## 🛑 ACİL DURDURMA

```bash
docker-compose stop
```

---

## ✅ TEK KOMUTLA HERŞEYİ KURMA

Server'a bağlandıktan sonra:

```bash
cd /root && \
apt update && apt upgrade -y && \
apt install -y docker.io docker-compose git curl && \
systemctl start docker && systemctl enable docker && \
git clone https://github.com/KULLANICI_ADIN/freqtrade_bot.git && \
cd freqtrade_bot && \
echo '{"exchange":{"key":"API_KEY","secret":"API_SECRET"}}' > config_secrets.json && \
chmod 600 config_secrets.json && \
docker-compose up -d && \
docker-compose logs -f
```

(API_KEY ve API_SECRET'i kendi bilgilerinle değiştir)
