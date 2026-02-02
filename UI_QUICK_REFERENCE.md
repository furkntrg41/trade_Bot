# 📋 UI QUICK REFERENCE - HIZLI BAŞVURU KARTI

## 🚀 BAŞLAMAK (30 saniye)

### Terminal 1: SSH Tunnel Aç
```powershell
ssh -i $HOME\.ssh\id_rsa_hetzner -L 8080:localhost:8080 root@91.98.133.146
```

### Terminal 2: Browser Aç
```powershell
start http://localhost:8080/
```

✅ **DONE!** UI açılmış olur.

---

## 📍 UI SAYFALAR HARİTASI

```
http://localhost:8080/
│
├─ Dashboard (/)
│  └─ Status, Memory, Uptime, Profit
│
├─ Trades (/trades)
│  └─ Open/Closed trades, History
│
├─ Analysis (/analysis)
│  └─ Statistics, Win rate, Pair performance
│
├─ Logs (/logs)
│  └─ Real-time [STRATEGY], [EXECUTION], [SAFETY]
│
├─ Settings (/settings)
│  └─ Bot start/stop, Pair config, Risk params
│
└─ RPC (/rpc)
   └─ Forcebuy, Forcesell, Manual commands
```

---

## 💾 DASHBOARD GÖSTERGELER

| Gösterge | Normal | Uyarı | Tehlike |
|----------|--------|-------|---------|
| Status | 🟢 RUNNING | 🟡 STARTING | 🔴 STOPPED |
| Memory | < 80% | 80-90% | > 90% |
| Open Trades | 0-2 | 2+ | N/A |
| Win Rate | > 50% | 40-50% | < 40% |
| Profit | + | ± | - |
| CPU | 20-60% | 60-80% | > 80% |

---

## 📊 TRADES SAYFASI - İŞLEM TÜRLERI

### Açık İşlem (OPEN)
```
Status: 🟢 OPEN (Hala açık, P&L hesaplanıyor)
P&L: Real-time (unrealized)
Örnek: +50 USDT (henüz kapanmamış)
```

### Kapalı İşlem - KÂR (WIN)
```
Status: ✅ CLOSED / PROFIT (Başarılı)
P&L: +541.75 USDT (realized)
ROI: +2.1%
Duration: 15 min
```

### Kapalı İşlem - ZARAR (LOSS)
```
Status: ❌ CLOSED / LOSS (Başarısız)
P&L: -45.50 USDT (realized)
ROI: -0.8%
Duration: 22 min
```

### Kapalı İşlem - STOP-LOSS
```
Status: 🛑 CLOSED / STOP-LOSS (Koruma)
P&L: -200 USDT (stop-loss tetiklenmiş)
ROI: -1.5%
Reason: Safety threshold exceeded
```

---

## 📈 ANALYSIS - TEMEL METRİKLER

```
Total Trades:      Kaç işlem yapıldı (1)
Wins:              Kazanılan işlemler (1)
Losses:            Kaybedilen işlemler (0)
Win Rate:          % kazanma oranı (100%)
Profit Factor:     (gross_profit / gross_loss) = Infinite
Best Trade:        En iyi işlem (+541.75 USDT)
Worst Trade:       En kötü işlem (N/A)
Avg Profit:        Ortalama kâr (2.1%)
Avg Duration:      Ortalama süre (15 min)
```

---

## 🔍 LOGS - OKUNUŞ TARIFİ

### [STRATEGY] Logs
```
[STRATEGY] Signal PAIR_001 | Z-Score: -2.345 | Action: OPEN
└─ Anlam: BTC/ETH pair'ında negatif Z-Score, LONG al sinyali
```

### [EXECUTION] Logs
```
[EXECUTION] Order Placed | BTC/USDT | LONG | 0.5 @ 42510.50
└─ Anlam: BTC emir gönderildi, 0.5 BTC, 42510.50 fiyatında

[EXECUTION] Order Filled | BTC | Status: SUCCESS
└─ Anlam: Emir Binance'de dolduruldu, başarılı

[EXECUTION] Hedging Update | ETH SHORT | 8.3 @ 2249.75
└─ Anlam: Hedge emir (ETH SHORT) gönderildi

[EXECUTION] Trade Update | P&L: +50 USDT
└─ Anlam: Şu an işlem +50 USDT kazançta
```

### [SAFETY] Logs
```
[SAFETY] Hedging Status | Delta: 0.00 | BALANCED
└─ Anlam: Net delta 0, fiyat riski korunmuş

[SAFETY] Stop-Loss Triggered | Z-Score: -4.5
└─ Anlam: Aşırı kayma, stop-loss activated (tehlike!)

[SAFETY] Trade Rollback | Reason: Position Imbalance
└─ Anlam: Imbalans, trade geriye alındı (manual check gerekli)
```

---

## 🔌 API QUICK COMMANDS

### Health & Status
```bash
# Health
curl http://localhost:8080/api/v1/ping

# Bot Status
curl http://localhost:8080/api/v1/status

# Locks (kilitli pair'lar)
curl http://localhost:8080/api/v1/locks
```

### Trades
```bash
# Tüm işlemler
curl http://localhost:8080/api/v1/trades

# Son 10 işlem
curl http://localhost:8080/api/v1/trades?limit=10

# Sadece açık işlemler
curl http://localhost:8080/api/v1/trades?status=open

# İstatistikler
curl http://localhost:8080/api/v1/trades/statistics
```

### Bot Control
```bash
# Bot başlat
curl -X POST http://localhost:8080/api/v1/start

# Bot durdur
curl -X POST http://localhost:8080/api/v1/stop

# Config yeniden yükle
curl -X POST http://localhost:8080/api/v1/reload_config
```

### Manual Trading
```bash
# Manuel trade aç
curl -X POST http://localhost:8080/api/v1/forcebuy \
  -H "Content-Type: application/json" \
  -d '{"pair": "BTC/USDT:USDT"}'

# Manuel trade kapat
curl -X POST http://localhost:8080/api/v1/forcesell \
  -H "Content-Type: application/json" \
  -d '{"tradeid": 1}'
```

---

## ⚠️ UYARI IŞARETLERI (KONTROL LİSTESİ)

### 🔴 HEMEN KONTROL ET
- [ ] 🔴 Status: STOPPED (Bot çalışmıyor!)
- [ ] 🔴 Memory > 90% (memory leak?)
- [ ] 🔴 ERROR logs var (ne oldu?)
- [ ] 🔴 P&L çok negatif (strateji bozuk mu?)
- [ ] 🔴 Win rate < 40% (kayıplar fazla)

### 🟡 İZLE
- [ ] 🟡 Memory 80-90% arası (growing?)
- [ ] 🟡 CPU > 80% (pressure var?)
- [ ] 🟡 WARNING logs (tekrarlı mı?)
- [ ] 🟡 Open trades > 2 (risk yüksek?)
- [ ] 🟡 Recent trades kaybediyor mu?

### 🟢 NORMAL
- [ ] ✅ Status: RUNNING (yeşil)
- [ ] ✅ Memory < 80% (stabil)
- [ ] ✅ No ERROR logs (temiz)
- [ ] ✅ Win rate > 50% (iyi)
- [ ] ✅ P&L pozitif (kârlı)

---

## 🛠️ SORUN GIDERME

### Problem: UI açılmıyor

```bash
# 1. Tunnel açık mı?
ssh -i $HOME\.ssh\id_rsa_hetzner -L 8080:localhost:8080 root@91.98.133.146

# 2. API responsive mı?
curl http://localhost:8080/api/v1/ping
# Beklenen: {"status": "pong"}

# 3. Container çalışıyor mu?
docker ps | grep freqtrade_bot
```

### Problem: Logs boş/çok az

```bash
# Real-time logs
docker logs -f freqtrade_bot

# Son 100 satır
docker logs freqtrade_bot --tail 100

# Specific log filter
docker logs freqtrade_bot | grep "\[EXECUTION\]"
```

### Problem: API timeout

```bash
# Bot responsive mı?
curl -m 5 http://localhost:8080/api/v1/status

# Memory check
docker stats freqtrade_bot

# Container restart
docker-compose -f docker-compose.production.yml restart
```

---

## 📱 MOBILE UI (SSH Tunnel ile)

SSH tunnel açık iken, network'teki diğer cihazlardan:
```
http://[your-computer-ip]:8080/
```

Örnek:
```
http://192.168.1.100:8080/
```

⚠️ **NOT:** Sadece local network içi, public erişim değil.

---

## 📅 GÜNLÜK KONTROL RUTINI

### Morning (5 min)
```
1. Dashboard aç
2. Status: 🟢 RUNNING?
3. Memory < 90%?
4. Yesterday's profit?
```

### During Day (on demand)
```
1. Trades sayfasından open trades izle
2. P&L tracked?
3. Logs'ta ERROR yok?
```

### Evening (5 min)
```
1. Analysis: Today's stats?
2. Win rate?
3. Total profit?
4. Any warnings/errors?
```

---

## 🎓 KAYNAKLAR

- **Full Guide:** [UI_ARAYUZ_REHBERI.md](UI_ARAYUZ_REHBERI.md)
- **System Architecture:** [SISTEM_MIMARISI_DETAYLICA.md](SISTEM_MIMARISI_DETAYLICA.md)
- **Commands Reference:** [COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md)
- **Learning Guide:** [OKUMA_REHBERI.md](OKUMA_REHBERI.md)

---

**Last Updated:** 2026-02-02
**Status:** ✅ UI Ready & Responding
**API Status:** ✅ Healthy (responding to /ping)
