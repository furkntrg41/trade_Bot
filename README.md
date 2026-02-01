# FreqAI Trading Bot

## HIZLI BAŞLANGIÇ

### Bot'u Başlat
`BASLAT.bat` dosyasına çift tıkla

### Bot'u Kapat
`KAPAT.bat` dosyasına çift tıkla

### Durum Kontrol
`DURUM.bat` dosyasına çift tıkla

---

## TELEGRAM KOMUTLARI

| Komut | Açıklama |
|-------|----------|
| `/status` | Açık pozisyonları göster |
| `/profit` | Toplam kar/zarar |
| `/balance` | Bakiye |
| `/daily` | Günlük performans |
| `/trades` | Son işlemler |
| `/start` | Bot bilgisi |
| `/help` | Tüm komutlar |

---

## FREQUI WEB ARAYÜZÜ

Tarayıcıda aç: **http://localhost:8080**

- Username: `freqtrader`
- Password: `furkan123`

---

## TERMİNAL KOMUTLARI (Opsiyonel)

```powershell
# Bot'u başlat
cd C:\Users\furka\Desktop\freqtrade_bot
docker compose up -d

# Bot'u kapat
docker compose down

# Logları izle (canlı)
docker logs -f freqtrade_bot

# Son 20 log satırı
docker logs freqtrade_bot --tail 20

# CPU/RAM kullanımı
docker stats --no-stream

# Bot'u yeniden başlat
docker compose restart freqtrade
```

---

## DOSYA YAPISI

```
freqtrade_bot/
├── BASLAT.bat          ← Bot'u başlat
├── KAPAT.bat           ← Bot'u kapat
├── DURUM.bat           ← Durum kontrol
├── config.json         ← Bot ayarları
├── docker-compose.yml  ← Docker ayarları
├── Dockerfile          ← Image tanımı
└── user_data/
    ├── strategies/     ← Strateji dosyaları
    ├── models/         ← Eğitilmiş ML modelleri
    ├── data/           ← Fiyat verileri
    └── logs/           ← Log dosyaları
```

---

## SORUN GİDERME

### Bot başlamıyor
1. Docker Desktop açık mı kontrol et
2. `KAPAT.bat` çalıştır, sonra `BASLAT.bat` çalıştır

### Telegram mesaj gelmiyor
1. Bot token doğru mu? (config.json)
2. Chat ID doğru mu? (config.json)
3. Bot'a `/start` yazdın mı?

### "No active trade" diyor
Normal. Bot sinyal bekliyor. Threshold değerine ulaşınca trade açacak.

---

## ÖNEMLİ NOTLAR

⚠️ **DRY-RUN MODU AKTİF** - Gerçek para kullanılmıyor, simülasyon.

⚠️ **API KEY YOK** - Live trading için Binance API key ekle.

⚠️ **7/24 ÇALIŞMASI İÇİN** - Bilgisayar açık kalmalı.

---

## İLETİŞİM

Sorun olursa GitHub Copilot'a sor.
