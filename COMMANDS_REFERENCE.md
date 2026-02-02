# 🎯 PRODUCTION DEPLOYMENT COMMAND REFERENCE
# ==========================================
# Exact terminal commands for 24/7 trading bot deployment
# Server: Hetzner 91.98.133.146 (CPX22)
# Date: 2026-02-01

---

## ✅ DEPLOYMENT FILES READY

All production infrastructure files are now on the server:

```
/root/freqtrade_bot/
├── docker-compose.production.yml    ← Production compose file
├── .env.production.template         ← Template (fill with API keys)
├── deploy_production.sh             ← Automated deployment script
├── scripts/
│   ├── state_recovery.py           ← Crash recovery engine
│   └── logging_config.py           ← Structured logging
└── [existing files...]
```

---

## 🚀 DEPLOYMENT COMMAND SEQUENCE

### Command 1: Connect to Server

```bash
ssh -i ~/.ssh/id_rsa_hetzner root@91.98.133.146
```

**Expected output:**
```
root@ubuntu-4gb-nbg1-1:~#
```

---

### Command 2: Navigate to Bot Directory

```bash
cd /root/freqtrade_bot
pwd
```

**Expected output:**
```
/root/freqtrade_bot
```

---

### Command 3: Verify Files Are Present

```bash
ls -lh docker-compose.production.yml scripts/state_recovery.py deploy_production.sh
```

**Expected output:**
```
-rwxr-xr-x ... deploy_production.sh
-rw-rw-rw- ... docker-compose.production.yml
-rw-r--r-- ... state_recovery.py
```

---

### Command 4: Create .env.production File

```bash
cp .env.production.template .env.production
```

**Expected output:**
```
(no output = success)
```

---

### Command 5: Edit API Keys (CRITICAL!)

```bash
nano .env.production
```

**Inside nano editor, fill in:**

```bash
# Copy your Binance Futures API key and secret
# Find at: https://www.binance.com/en/account/api-management

BINANCE_API_KEY=your_actual_api_key_here
BINANCE_API_SECRET=your_actual_api_secret_here

# Enable live trading
DRY_RUN=false
TRADING_MODE=futures
```

**Save and exit:**
- Press `Ctrl+O` (WriteOut)
- Press `Enter` (confirm filename)
- Press `Ctrl+X` (exit)

**Verify file was saved:**

```bash
cat .env.production | grep BINANCE_API_KEY
```

**Expected output:**
```
BINANCE_API_KEY=your_actual_api_key_here
```

---

### Command 6: Secure the File

```bash
chmod 600 .env.production
```

**Verify permissions:**

```bash
ls -lh .env.production
```

**Expected output:**
```
-rw------- 1 root root ... .env.production
```

---

### Command 7: RUN AUTOMATED DEPLOYMENT

```bash
bash deploy_production.sh
```

**The script will:**

1. ✅ Verify all production files
2. ✅ Stop current bot (if running)
3. ✅ Rebuild Docker image (may take 2-3 min)
4. ✅ Run state recovery on Binance
5. ✅ Start bot with all enhancements
6. ✅ Monitor for 30 seconds

**Expected output during script:**

```
========================================
🚀 PRODUCTION DEPLOYMENT SCRIPT
========================================

[1/7] 📋 Verifying files...
✅ Production compose file found

[2/7] 🛑 Stopping current bot...
✅ Bot stopped

[3/7] 🔐 Checking .env.production...
✅ .env.production found and secured

[4/7] 🔨 Rebuilding Docker image...
    This may take 2-3 minutes...
✅ Docker image rebuilt

[5/7] ✔️  Verifying configuration...
    Pairs found: 10
✅ Configuration verified

[6/7] 🚀 Starting bot with state recovery...
✅ Bot started

[7/7] 📊 Monitoring startup (30 seconds)...
[STATE RECOVERY] Starting reconciliation...
[STATE RECOVERY] Checking for orphaned positions...
[LAUNCH] Starting FreqTrade bot...
✅ Bot is HEALTHY!

========================================
🎉 DEPLOYMENT SUCCESSFUL
========================================
```

---

## 📊 MONITORING COMMANDS (After Deployment)

### Command 8: Watch Real-Time Logs

```bash
docker logs -f freqtrade_bot
```

**Expected output (STRATEGY signals):**
```
[STRATEGY] Signal #PAIR_001    | Z-Score: -2.345 | Threshold:  2.00 | Type: CLOSE
[STRATEGY] Cointegration       | Stat:    -4.234 | P-value: 0.000123
```

**Expected output (EXECUTION events):**
```
[EXECUTION] Order Placed | BTC/USDT:USDT | LONG  | Amount:   100.0000 @ 42500.00
[EXECUTION] Order Fill   | ETH/USDT:USDT | SHORT | Amount:  1500.0000 @ 2250.00 | Fill: 100.0%
```

**Expected output (SAFETY events):**
```
[SAFETY] Safety Trigger | Position Loss | Loss exceeds threshold
```

**To exit logs:**
- Press `Ctrl+C`

---

### Command 9: Check Bot Health

```bash
docker ps | grep freqtrade_bot
```

**Expected output:**
```
738e18d908c7   freqtrade_bot_freqtrade ... Up 5 minutes (healthy) ... 8080->8080
```

**Key indicators:**
- `Up X minutes` → Container is running
- `(healthy)` → Health check passed
- `8080->8080` → API is accessible

---

### Command 10: Test REST API

```bash
curl -s http://localhost:8080/api/v1/ping | jq .
```

**Expected output:**
```json
{
  "status": "pong"
}
```

---

### Command 11: View Recovery Report

```bash
cat user_data/logs/recovery_report.json | jq .
```

**Expected output (clean startup):**
```json
{
  "timestamp": "2026-02-01T22:30:00.000000",
  "status": "clean",
  "orphaned_positions_count": 0,
  "orphaned_orders_count": 0,
  "orphaned_positions": [],
  "orphaned_orders": [],
  "recommendations": [
    "✅ All clear - no orphaned positions or orders found"
  ]
}
```

**If orphaned positions detected:**
```json
{
  "status": "recovery_needed",
  "orphaned_positions_count": 1,
  "orphaned_positions": [
    {
      "symbol": "BTC/USDT:USDT",
      "contracts": 0.01,
      "side": "long"
    }
  ],
  "recommendations": [
    "⚠️ MANUAL ACTION REQUIRED: Orphaned positions detected..."
  ]
}
```

---

### Command 12: Get Current Trades

```bash
curl -s http://localhost:8080/api/v1/trades | jq .
```

**Expected output (if trades exist):**
```json
[
  {
    "pair": "BTC/USDT:USDT",
    "stake_amount": 1000.0,
    "amount": 0.02345,
    "open_rate": 42500.0,
    "close_rate": null,
    "trade_duration": 145
  }
]
```

---

### Command 13: Get Account Balance

```bash
curl -s http://localhost:8080/api/v1/balance | jq .
```

**Expected output:**
```json
{
  "free": {"USDT": 5000.0},
  "used": {"USDT": 2000.0},
  "total": {"USDT": 7000.0}
}
```

---

### Command 14: Filter Logs by Category

```bash
# Only STRATEGY signals
docker logs -f freqtrade_bot | grep "\[STRATEGY\]"

# Only EXECUTION events
docker logs -f freqtrade_bot | grep "\[EXECUTION\]"

# Only SAFETY events
docker logs -f freqtrade_bot | grep "\[SAFETY\]"
```

---

### Command 15: Check System Resources

```bash
docker stats --no-stream freqtrade_bot
```

**Expected output:**
```
CONTAINER ID    MEM USAGE / LIMIT    MEM %
738e18d908c7    2.8GB / 3.5GB        80%
```

**Healthy ranges:**
- Memory: < 3.5GB ✅
- CPU: 30-60% ✅

---

## 🔄 RECOVERY COMMANDS (If Bot Crashes)

### Restart Bot (Triggers Recovery)

```bash
docker-compose -f docker-compose.production.yml restart freqtrade_bot
```

**What happens:**
1. Bot stops gracefully (30s timeout)
2. State recovery runs
3. Bot restarts with reconciled state

---

### View Recent Trades After Crash

```bash
cat user_data/logs/recent_trades.json | jq '.[] | {symbol, side, amount, price}' | head -20
```

---

### Check Logs for Errors

```bash
docker logs freqtrade_bot | grep -i "error\|exception" | tail -20
```

---

## 🛑 STOP COMMANDS

### Graceful Stop (Recommended)

```bash
docker-compose -f docker-compose.production.yml stop freqtrade_bot
```

**Time taken:** ~30 seconds (completes pending trades)

**Verify it stopped:**
```bash
docker ps | grep freqtrade_bot
```

**Expected output:** (empty = stopped successfully)

---

### Force Stop (Emergency Only)

```bash
docker-compose -f docker-compose.production.yml kill freqtrade_bot
```

**Time taken:** Immediate

---

### Full Shutdown (Remove container)

```bash
docker-compose -f docker-compose.production.yml down
```

---

## 📁 LOG FILE LOCATIONS

```bash
# Main logs
tail -f /root/freqtrade_bot/user_data/logs/freqtrade.log

# Strategy logs
tail -f /root/freqtrade_bot/user_data/logs/strategy.log

# Execution logs
tail -f /root/freqtrade_bot/user_data/logs/execution.log

# Safety logs
tail -f /root/freqtrade_bot/user_data/logs/safety.log

# State recovery log
cat /root/freqtrade_bot/user_data/logs/state_recovery.log

# Recovery report
cat /root/freqtrade_bot/user_data/logs/recovery_report.json
```

---

## 💾 BACKUP & MAINTENANCE

### Daily Backup

```bash
# Backup database
cp /root/freqtrade_bot/user_data/tradesv3.db \
   /root/freqtrade_bot/user_data/backups/tradesv3.$(date +%Y%m%d_%H%M%S).db

# Backup logs
tar -czf /root/freqtrade_bot/user_data/backups/logs_$(date +%Y%m%d).tar.gz \
  /root/freqtrade_bot/user_data/logs/
```

### Clean Old Logs (Keep 7 days)

```bash
find /root/freqtrade_bot/user_data/logs -name "*.log" -mtime +7 -delete
```

---

## ✅ COMPLETE DEPLOYMENT CHECKLIST

After running all commands above, verify:

```bash
# 1. Container healthy
docker ps | grep freqtrade_bot | grep healthy

# 2. API responding
curl -s http://localhost:8080/api/v1/ping | jq .status

# 3. No startup errors
docker logs freqtrade_bot | grep -i "error" | wc -l

# 4. Recovery report clean
cat user_data/logs/recovery_report.json | jq .status

# 5. Pairs loaded
docker logs freqtrade_bot | grep "Pair\|monitoring" | head -5

# 6. Resources OK
docker stats --no-stream freqtrade_bot | grep -E "MEM|CPU"
```

**All checks should pass (✅ status = "clean", 0 errors, healthy container)**

---

## 🎯 FINAL SUMMARY

### You Now Have:
✅ Production-grade Docker deployment  
✅ Automatic crash recovery  
✅ State reconciliation with Binance  
✅ Structured logging (STRATEGY/EXECUTION/SAFETY)  
✅ Health monitoring & auto-restart  
✅ REST API for monitoring  
✅ Security-hardened configuration  

### Bot is 24/7 Production Ready:
✅ Auto-recovery from crashes  
✅ State synchronization on startup  
✅ Real-time signal logging  
✅ Execution tracking  
✅ Safety protection alerts  

### Next: LAUNCH! 🚀

```bash
# Final command to go live
bash deploy_production.sh
```

---

**Deployment Complete**  
Date: 2026-02-01  
Server: Hetzner CPX22 (91.98.133.146)  
Bot: Market-Neutral Statistical Arbitrage  
Status: 🟢 PRODUCTION READY
