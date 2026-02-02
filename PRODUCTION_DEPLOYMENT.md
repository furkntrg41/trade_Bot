# PRODUCTION DEPLOYMENT GUIDE
# ============================
# Market-Neutral Statistical Arbitrage Bot
# Hetzner VPS Deployment (Ubuntu 22.04)

## 📋 PRE-DEPLOYMENT CHECKLIST

### 1. Server Prerequisites
- [ ] Ubuntu 22.04 LTS
- [ ] 4GB+ RAM (Hetzner CPX22)
- [ ] 2+ vCPU
- [ ] 50GB+ storage
- [ ] Docker + Docker Compose installed
- [ ] SSH key-based auth configured

### 2. Application Readiness
- [ ] `config.json` - Freqtrade config (dry-run mode for testing)
- [ ] `pairs_config.json` - Cointegrated pairs list (10 validated pairs)
- [ ] `docker-compose.production.yml` - Production compose file
- [ ] `.env.production` - API keys (DO NOT commit)
- [ ] `scripts/state_recovery.py` - Crash recovery engine
- [ ] All source code files in `quant_arbitrage/`

### 3. Security Hardening
- [ ] API keys loaded only from `.env.production`
- [ ] `.env.production` has `chmod 600` permissions
- [ ] `.gitignore` includes `.env.production`
- [ ] No API keys in config.json
- [ ] Firewall configured (only SSH + HTTP/8080 if needed)

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Connect to Server

```bash
# SSH into Hetzner VPS
ssh -i ~/.ssh/id_rsa_hetzner root@91.98.133.146

# Verify system
uname -a                    # Should show: Linux ... GNU/Linux
docker --version            # Should show: Docker version 29.x+
docker-compose --version    # Should show: docker-compose version 1.29+
```

### Step 2: Navigate to Bot Directory

```bash
cd /root/freqtrade_bot

# Verify files
ls -la
# Should show: config.json, docker-compose.production.yml, Dockerfile, etc.
```

### Step 3: Configure Production Environment

```bash
# Copy template to production file
cp .env.production.template .env.production

# Edit with your Binance API keys
nano .env.production
# Fill in:
#   BINANCE_API_KEY=<your_key>
#   BINANCE_API_SECRET=<your_secret>
#   TRADING_MODE=futures
#   DRY_RUN=false

# Secure the file
chmod 600 .env.production
```

### Step 4: Verify Configuration Files

```bash
# Check pairs_config.json
cat pairs_config.json | head -20

# Verify config.json
cat config.json | grep -A2 "pair_whitelist\|stake_currency\|trading_mode"

# Expected output should show:
# - trading_mode: "futures"
# - stake_currency: "USDT"
# - Your 10 cointegrated pairs
```

### Step 5: Build and Deploy

```bash
# Build Docker image (first time only)
docker-compose -f docker-compose.production.yml build

# Pull latest base image
docker pull freqtradeorg/freqtrade:develop_freqai

# Rebuild with latest
docker-compose -f docker-compose.production.yml build --no-cache
```

### Step 6: Start the Bot

```bash
# Start in foreground (to monitor initial startup)
docker-compose -f docker-compose.production.yml up

# You should see:
# [STATE RECOVERY] Starting reconciliation...
# [STATE RECOVERY] Checking for orphaned positions...
# [LAUNCH] Starting FreqTrade bot...
# ✅ Bot heartbeat messages every 60s
```

### Step 7: Detach and Run in Background

```bash
# Press Ctrl+C to exit foreground monitoring

# Start as daemon (background)
docker-compose -f docker-compose.production.yml up -d

# Verify it's running
docker ps -a
# Should show: freqtrade_bot (Status: Up, healthy)
```

---

## 📊 MONITORING & OPERATIONS

### View Real-Time Logs

```bash
# All logs
docker logs -f freqtrade_bot

# Last 50 lines
docker logs --tail 50 freqtrade_bot

# Follow STRATEGY logs only
docker logs -f freqtrade_bot | grep "\[STRATEGY\]"

# Follow EXECUTION logs only
docker logs -f freqtrade_bot | grep "\[EXECUTION\]"

# Follow SAFETY logs only
docker logs -f freqtrade_bot | grep "\[SAFETY\]"
```

### Check Health Status

```bash
# Container status
docker ps | grep freqtrade_bot

# Health check result
docker inspect freqtrade_bot | grep -A5 "Health"

# Expected: "Status": "healthy"
```

### Access REST API

```bash
# Check API endpoint
curl -s http://localhost:8080/api/v1/ping

# Expected response: {"status":"pong"}

# Get bot status
curl -s http://localhost:8080/api/v1/status | jq .

# Get all open trades
curl -s http://localhost:8080/api/v1/trades | jq .

# Get account balance
curl -s http://localhost:8080/api/v1/balance | jq .
```

### Monitor from Recovery Report

```bash
# Check if orphaned positions were found on startup
cat /root/freqtrade_bot/user_data/logs/recovery_report.json | jq .

# Example clean output:
# {
#   "status": "clean",
#   "orphaned_positions_count": 0,
#   "orphaned_orders_count": 0,
#   "recommendations": ["✅ All clear - no orphaned positions or orders found"]
# }
```

---

## 🔄 AUTO-RECOVERY & CRASH HANDLING

### What Happens on Crash

1. **Container Exits**: Bot crashes or receives SIGTERM
2. **Docker Restarts**: `restart: unless-stopped` policy kicks in
3. **State Recovery**: `state_recovery.py` runs first
   - Checks Binance for orphaned positions
   - Verifies open orders
   - Queries last 24h of trades
   - Writes `recovery_report.json`
4. **Bot Restarts**: FreqTrade boots with reconciled state

### Manual Restart

```bash
# Restart container (triggers recovery)
docker-compose -f docker-compose.production.yml restart freqtrade_bot

# Stop container
docker-compose -f docker-compose.production.yml stop freqtrade_bot

# Start container
docker-compose -f docker-compose.production.yml start freqtrade_bot
```

---

## 🛑 GRACEFUL SHUTDOWN

```bash
# Stop bot cleanly (30s grace period)
docker-compose -f docker-compose.production.yml stop freqtrade_bot

# Force stop (kills immediately)
docker-compose -f docker-compose.production.yml kill freqtrade_bot

# Shutdown everything
docker-compose -f docker-compose.production.yml down
```

---

## 📈 SYSTEM MONITORING

### CPU & Memory Usage

```bash
# Real-time stats
docker stats freqtrade_bot

# Expected for CPX22:
# - Memory: ~2.5GB-3GB (within limits)
# - CPU: 40-60% during trading
```

### Disk Usage

```bash
# Check logs directory
du -sh /root/freqtrade_bot/user_data/logs/

# Clean old logs (keep last 7 days)
find /root/freqtrade_bot/user_data/logs -name "*.log" -mtime +7 -delete
```

### Database Size

```bash
# Check SQLite database
ls -lh /root/freqtrade_bot/user_data/tradesv3*.db

# Maintain database
sqlite3 /root/freqtrade_bot/user_data/tradesv3.db "VACUUM;"
```

---

## 🔐 SECURITY BEST PRACTICES

### 1. API Key Rotation

```bash
# Every 30-90 days:
# 1. Generate new API key on Binance
# 2. Update .env.production
# 3. Restart bot
# 4. Delete old API key from Binance

nano .env.production
docker-compose -f docker-compose.production.yml restart freqtrade_bot
```

### 2. Firewall Configuration

```bash
# Allow SSH only from your IP
ufw allow from <your_ip> to any port 22

# If using REST API externally, use reverse proxy with auth
# DO NOT expose port 8080 directly without authentication
```

### 3. Backup State

```bash
# Backup database daily
cp /root/freqtrade_bot/user_data/tradesv3.db \
   /root/freqtrade_bot/user_data/backups/tradesv3.$(date +%Y%m%d_%H%M%S).db

# Backup logs
tar -czf /root/freqtrade_bot/logs_backup_$(date +%Y%m%d).tar.gz \
  /root/freqtrade_bot/user_data/logs/
```

---

## 🚨 TROUBLESHOOTING

### Bot won't start

```bash
# Check logs
docker logs freqtrade_bot | tail -100

# Verify config files
docker run --rm -v $PWD:/freqtrade freqtradeorg/freqtrade:develop_freqai \
  validate-config -c /freqtrade/config.json

# Check permissions
ls -la config.json pairs_config.json .env.production
```

### High CPU/Memory Usage

```bash
# Check what's consuming resources
docker stats --no-stream freqtrade_bot

# Reduce log level if needed
# Edit config.json: set "verbosity": 0
docker-compose -f docker-compose.production.yml restart freqtrade_bot
```

### API Connection Issues

```bash
# Check Binance connectivity
curl -s https://api.binance.com/api/v3/ping

# Check REST API health
curl -v http://localhost:8080/api/v1/ping

# View exchange connection logs
docker logs freqtrade_bot | grep -i "exchange\|binance"
```

### Orphaned Positions Detected

```bash
# Check recovery report
cat user_data/logs/recovery_report.json | jq .

# Manual action: Close positions via Binance if unwanted
# OR let bot manage them (recommended)

# Restart bot to re-run recovery
docker-compose -f docker-compose.production.yml restart freqtrade_bot
```

---

## 📞 SUPPORT RESOURCES

- **Freqtrade Docs**: https://www.freqtrade.io/
- **Binance Futures API**: https://binance-docs.github.io/apidocs/
- **Hetzner Support**: https://support.hetzner.com/
- **Docker Docs**: https://docs.docker.com/

---

## ✅ DEPLOYMENT VERIFICATION

After deployment, verify:

```bash
# 1. Container running and healthy
docker ps | grep freqtrade_bot | grep "healthy"

# 2. API responding
curl -s http://localhost:8080/api/v1/ping | jq .

# 3. Strategy loaded
docker logs freqtrade_bot | grep -i "strategy\|loaded"

# 4. No errors in recovery
docker logs freqtrade_bot | grep -i "error" | head -5

# 5. Monitoring pairs
docker logs freqtrade_bot | grep -i "starting\|monitoring"
```

**Expected output for all checks: ✅ Pass**

---

## 🎯 NEXT STEPS

1. **Monitor for 24 hours**: Observe signals, execution, performance
2. **Enable Telegram alerts** (optional): Add TELEGRAM_TOKEN to .env.production
3. **Review recovery logs**: Check for any orphaned positions
4. **Gradual transition**: Consider small position sizes first
5. **Set up cron backup**: `crontab -e` to backup daily

---

**Version**: 1.0 Production Ready  
**Date**: 2026-02-01  
**Deployed to**: Hetzner CPX22 (91.98.133.146)
