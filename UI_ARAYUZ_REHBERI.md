# 🖥️ FREQTRADE UI - WEB ARAYÜZ ERIŞIM KÉĞU

## Hızlı Başlangıç (2 dakika)

### Method 1: SSH Tunnel (ÖNERILEN - En Güvenli)

**Step 1:** PowerShell'de tunnel aç

```bash
ssh -i $HOME\.ssh\id_rsa_hetzner -L 8080:localhost:8080 root@91.98.133.146
```

**Output:**
```
Welcome to Ubuntu 22.04 LTS
(Bağlantı açık kalmaya devam edecek)
```

**Step 2:** Yeni PowerShell penceresi aç ve browser'ı başlat

```bash
start http://localhost:8080/
```

**Result:** FreqTrade Web UI açılacak! ✅

---

## Web UI Sayfaları Detaylı

### 1. DASHBOARD (Ana Sayfa)

**Nedir:** Bot'un genel durumu ve özet istatistikler

**Göreceğin Şeyler:**
- 🟢 **Status:** RUNNING (yeşil = sağlıklı)
- ⏱️ **Uptime:** "12 minutes" (bot kaç süredir açık)
- 💾 **Memory:** 2.8 GB / 3.5 GB (RAM kullanımı - 80%)
- 🔄 **CPU:** 45% (işlemci kullanımı)
- 📊 **Disk:** 42 GB / 50 GB free
- 📈 **Open Trades:** 0 (şu an açık işlem sayısı)
- 📊 **Max Open Trades:** 2 (maksimum eş zamanlı trade)
- 💰 **Total Profit:** +541.75 USDT (toplam kâr)
- ✅ **Win Rate:** 100% (kazanılan işlem yüzdesi)

**Ne zaman kontrol et:**
- Güne başlarken (sistem sağlıklı mı?)
- Memory yüksekse (restart gerek mi?)
- İşlem açılmışsa (monitöre et)

---

### 2. TRADES (İşlem Geçmişi)

**Nedir:** Açık ve kapalı işlemlerin detaylı listesi

**Göreceğin Şeyler:**

**Aktif İşlemler (Open Trades):**
```
Pair          Entry Price    Entry Date    Current P&L    Status
─────────────────────────────────────────────────────────────
BTC/USDT      42510.50       22:26         +50 USDT       OPEN
ETH/USDT      2249.75        22:26         +180 USDT      OPEN
```

**Kapalı İşlemler (Trade History):**
```
Pair          Entry→Exit     Duration      Profit      ROI      Status
─────────────────────────────────────────────────────────────────────
BTC/ETH       42510→42498    15 min        +541.75 USDT  2.1%     ✅ WIN
SOL/ADA       180.50→181.00  22 min        -45.50 USDT   -0.8%    ❌ LOSS
```

**Detaylı Trade View:**
- Candle chart (fiyat grafiği)
- Entry/exit prices (giriş/çıkış fiyatları)
- Trade notes (not ve açıklamalar)
- Full trade history (tüm işlem detayları)

**Ne zaman kontrol et:**
- Yeni işlem açıldığında (gerçekten açıldı mı?)
- İşlem sırasında (P&L izleme)
- İşlem kapatıldığında (kâr/zarar kontrolü)

---

### 3. ANALYSIS (Analiz)

**Nedir:** İşlem performans analizi ve istatistikler

**Göreceğin Şeyler:**

**Overall Statistics:**
- Total Trades: 1
- Wins: 1 (100%)
- Losses: 0 (0%)
- Average Trade Duration: 15 minutes
- Profit Factor: Infinite (no losses)
- Best Trade: +541.75 USDT (100% ROI)
- Worst Trade: N/A

**Profit Distribution:**
- Pie chart: Profit kaynakları
- Monthly statistics: Aylık özet
- Hourly statistics: Saatlik özet

**Pair Performance:**
```
Pair          Trades    Wins    Win%      Avg P&L        Status
─────────────────────────────────────────────────────────────
BTC/ETH       1         1       100%      +541.75 USDT    🟢 GOOD
SOL/ADA       0         0       N/A       N/A             ⚪ NONE
```

**Ne zaman kontrol et:**
- Hafta sonunda (haftalık özet)
- Ay sonunda (aylık perfomans)
- Strateji değiştirdikten sonra

---

### 4. LOGS (Günlükler)

**Nedir:** Real-time sistem günlükleri ve hata mesajları

**Göreceğin Şeyler:**

```
2026-02-02 22:26:05  [freqtrade.bot] - INFO - Bot heartbeat. PID=1
2026-02-02 22:26:07  [freqtrade.worker] - INFO - RPC Server started
2026-02-02 22:26:10  [freqtrade.exchange] - INFO - Connected to Binance

[STRATEGY] signals
─────────────────
2026-02-02 22:26:15  [STRATEGY] Signal PAIR_001 | Z-Score: -2.345 | Action: OPEN

[EXECUTION] events
──────────────────
2026-02-02 22:26:16  [EXECUTION] Order Placed | BTC LONG | 0.5 @ 42510.50
2026-02-02 22:26:17  [EXECUTION] Order Filled | BTC | ID: 123456
2026-02-02 22:26:18  [EXECUTION] Order Placed | ETH SHORT | 8.3 @ 2249.75

[SAFETY] alerts
───────────────
2026-02-02 22:27:30  [SAFETY] Hedging Update | Delta: 0.00 | Status: BALANCED
```

**Log Seviyeleri:**
- 🔵 **INFO:** Bilgi mesajları (normal)
- 🟡 **WARNING:** Uyarılar (önem düşük)
- 🔴 **ERROR:** Hata mesajları (dikkat gerek)

**Ne zaman kontrol et:**
- Red/ERROR logs var mı?
- Warning'ler sıkça mı tekrarlanıyor?
- Trade açıldığında (execution logs'ları görmek için)

---

### 5. SETTINGS (Ayarlar)

**Nedir:** Bot kontrol ve ayar değiştirme paneli

**Göreceğin Şeyler:**

**Bot Kontrol:**
- ▶️ START button (botu başlat)
- ⏸️ STOP button (botu durdur)
- 🔄 RELOAD CONFIG (config yeniden yükle)

**Trading Mode:**
- 🧪 Dry-run toggle (test modu)
- 💰 Live trading toggle (gerçek para)

**Pair Selection:**
- Whitelist: Hangi pair'larla işlem yap
- Add/Remove pairs: Pair ekle/sil

**Risk Parameters:**
- Max stake: Maksimum stake per trade
- Max open trades: Maksimum eş zamanlı işlem
- Stoploss: Stop-loss seviyesi

**Ne zaman kontrol et:**
- Dry-run vs Live arasında switch yapmak
- Pair eklemek/silmek
- Risk parametrelerini ayarlamak

---

### 6. RPC (Komut Paneli)

**Nedir:** Manuel bot kontrol komutları

**Komutlar:**

**Forcebuy (Manuel trade açma):**
```
Pair: BTC/USDT:USDT
Price: 42500 (optional)
Response: {"tradeid": 123, "status": "BUY"}
```

**Forcesell (Manuel trade kapatma):**
```
Trade ID: 123
Response: {"tradeid": 123, "status": "SELL"}
```

**Bot Control:**
- Start: Bot başlat
- Stop: Bot durdur
- Reload Config: Config yeniden yükle

**Locks Management:**
- View locked pairs
- Remove locks
- Add temporary locks

**Ne zaman kontrol et:**
- Emergency durumda (hızlı manuel trade)
- Lock yönetimi gerekiyorsa
- Config değiştirip reload etmek

---

## REST API Endpoints (Terminal Erişimi)

### Health Check

```bash
curl http://localhost:8080/api/v1/ping
```

**Response:**
```json
{"status": "pong"}
```

---

### Bot Status

```bash
curl http://localhost:8080/api/v1/status
```

**Response:**
```json
{
  "state": "RUNNING",
  "bot_version": "docker-2026.2-dev-98b56a49",
  "pid": 1,
  "uptime": "12 minutes",
  "trading_mode": "futures",
  "margin_mode": "isolated"
}
```

---

### Get All Trades

```bash
curl http://localhost:8080/api/v1/trades
```

**Response:**
```json
[
  {
    "id": 1,
    "pair": "BTC/USDT:USDT",
    "stake_amount": 100,
    "amount": 0.5,
    "open_rate": 42510.50,
    "close_rate": 42498.50,
    "profit_abs": 541.75,
    "profit_ratio": 0.021,
    "open_date": "2026-02-02T22:26:05+00:00",
    "close_date": "2026-02-02T22:41:05+00:00",
    "trade_duration": 15
  }
]
```

---

### Trade Statistics

```bash
curl http://localhost:8080/api/v1/trades/statistics
```

**Response:**
```json
{
  "total_trades": 1,
  "trades_count": 1,
  "first_trade_date": "2026-02-02T22:26:05+00:00",
  "first_trade_timestamp": 1738535165,
  "latest_trade_date": "2026-02-02T22:41:05+00:00",
  "latest_trade_timestamp": 1738536065,
  "wins": 1,
  "losses": 0,
  "draws": 0,
  "total_profit_abs": 541.75,
  "total_profit_ratio": 0.021,
  "avg_profit": 2.1,
  "avg_duration": 900
}
```

---

### Current Open Orders

```bash
curl http://localhost:8080/api/v1/locks
```

**Response:**
```json
[]
```

(Boş array = hiç lock yok = tüm pair'lar serbest)

---

### Get Strategies

```bash
curl http://localhost:8080/api/v1/strategies
```

**Response:**
```json
{
  "strategies": ["FreqaiExampleStrategy"],
  "strategy": "FreqaiExampleStrategy"
}
```

---

### Force Buy (Manuel Trade Açma)

```bash
curl -X POST http://localhost:8080/api/v1/forcebuy \
  -H "Content-Type: application/json" \
  -d '{"pair": "BTC/USDT:USDT", "price": 42500}'
```

**Response:**
```json
{
  "tradeid": 2,
  "pair": "BTC/USDT:USDT",
  "status": "BUY"
}
```

---

### Force Sell (Manuel Trade Kapatma)

```bash
curl -X POST http://localhost:8080/api/v1/forcesell \
  -H "Content-Type: application/json" \
  -d '{"tradeid": 2}'
```

**Response:**
```json
{
  "tradeid": 2,
  "status": "SELL"
}
```

---

### Start Bot

```bash
curl -X POST http://localhost:8080/api/v1/start
```

**Response:**
```json
{"status": "RUNNING"}
```

---

### Stop Bot

```bash
curl -X POST http://localhost:8080/api/v1/stop
```

**Response:**
```json
{"status": "STOPPED"}
```

---

## Monitoring Checklist

### Günlük Kontrol (Daily)

- [ ] Dashboard açıp Status kontrol et (🟢 green?)
- [ ] Memory % kontrol et (< 90%?)
- [ ] Open trades var mı, kaç tane?
- [ ] Logs'ta ERROR var mı?
- [ ] Total Profit pozitif mi?

### Haftalık Kontrol (Weekly)

- [ ] Analysis sayfasında win rate kontrol et
- [ ] Best/worst trade'leri gözden geçir
- [ ] Pair performance analiz et
- [ ] Strateji hala iyi mi çalışıyor?

### Aylık Kontrol (Monthly)

- [ ] Toplam kâr/zarar hesapla
- [ ] Profit factor analiz et
- [ ] Risk düzeyini kontrol et
- [ ] Strategy parametrelerini gözden geçir

---

## Sorun Giderme

### Problem: UI açılmıyor

```bash
# SSH tunnel açık mı kontrol et
ssh -i $HOME\.ssh\id_rsa_hetzner -L 8080:localhost:8080 root@91.98.133.146

# API responding mı kontrol et
curl http://localhost:8080/api/v1/ping
```

---

### Problem: API timeout

```bash
# Bot responsive mı kontrol et
docker exec freqtrade_bot ps aux

# Container logs kontrol et
docker logs freqtrade_bot --tail 50

# Memory pressure var mı?
docker stats freqtrade_bot
```

---

### Problem: Logs çok kısa veya boş

```bash
# Docker logs'u artır
docker logs freqtrade_bot --tail 100

# Real-time logs izle
docker logs -f freqtrade_bot
```

---

## Özet

| Feature | Method | URL |
|---------|--------|-----|
| **Web UI** | SSH Tunnel | http://localhost:8080/ |
| **Health Check** | API | /api/v1/ping |
| **Bot Status** | API | /api/v1/status |
| **Trades** | UI / API | /trades veya /api/v1/trades |
| **Statistics** | UI / API | /analysis veya /api/v1/trades/statistics |
| **Logs** | UI / Docker | /logs veya docker logs |
| **Manual Trade** | API | POST /api/v1/forcebuy |
| **Manual Close** | API | POST /api/v1/forcesell |

---

**Last Updated:** 2026-02-02
**Status:** ✅ UI Ready & Responding
