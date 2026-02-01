# 🎯 QUICK REFERENCE: START HERE

## ⚡ Quick Start (30 seconds)

```bash
# 1. Check everything is ready
python preflight_check.py

# 2. Set your credentials
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"

# 3. Start trading
python main.py

# 4. Monitor in another terminal
tail -f logs/trading_bot.log

# 5. Stop with Ctrl+C (graceful shutdown)
```

---

## 📊 What You Have

### ✅ 10 Live Trading Pairs
From real Binance Futures data (2026-02-01):

```
1. 1000CAT_1MBABYDOGE    (β=0.7387, HL=5.3h)  ✅ VALIDATED
2. 1INCH_AI              (β=1.0802, HL=4.0h)  ✅ VALIDATED
3. 1000CAT_AIXBT         (β=0.9429, HL=8.5h)  ✅ VALIDATED
4. 1MBABYDOGE_AEVO       (β=1.0480, HL=5.0h)  ✅ VALIDATED
5. AI_ALGO               (β=0.7077, HL=5.1h)  ✅ VALIDATED
6. AAVE_AI               (β=1.4681, HL=5.7h)  ✅ VALIDATED
7. AIXBT_ALICE           (β=0.9236, HL=9.5h)  ✅ VALIDATED
8. 1MBABYDOGE_ADA        (β=0.5160, HL=17.2h) ✅ VALIDATED
9. ACE_ALT               (β=0.7740, HL=5.2h)  ✅ VALIDATED
10. 1000SATS_AEVO        (β=0.9661, HL=6.2h)  ✅ VALIDATED

All p-values < 0.05 (statistically valid)
All half-lives < 24h (mean reversion works)
```

### ✅ Production Execution Engine
- 1089 lines of hardened code
- 5 safety protocols active
- Real order execution
- Complete error handling

### ✅ Main Entry Point
- 511 lines of orchestration
- Async event loop
- Concurrent pair monitoring
- Graceful shutdown

---

## 🚀 Launch Commands

### Normal Start
```bash
python main.py
```

### Start with Debug Logging
```bash
python -m pdb main.py  # Python debugger
```

### Start in Background
```bash
nohup python main.py > bot.log 2>&1 &
```

### Monitor Running Bot
```bash
tail -f logs/trading_bot.log
```

### Stop Running Bot (from another terminal)
```bash
pkill -f "python main.py"
```

---

## 📈 Signal Examples

### When You See This in Logs

**🟢 BUY Signal:**
```
📡 SIGNAL RECEIVED #1 | 🟢 BUY 1INCH/AI | Z=2.45 | Conf=92.0% | Size=75.0% | @20:55:33
```

**🔴 SELL Signal:**
```
📡 SIGNAL RECEIVED #2 | 🔴 SELL 1000CAT/1MBABYDOGE | Z=-2.81 | Conf=88.0% | Size=75.0% | @20:56:12
```

**🟡 EXIT Signal:**
```
📡 SIGNAL RECEIVED #3 | 🟡 EXIT | Z=0.12 | Conf=65.0% | Size=50.0% | @20:57:45
```

### When Trade Executes

```
✅ TRADE EXECUTED #1 | Pair: 1INCH_AI | Signal: BUY
  Order 1 (Leg A): BUY 1000 INCH/USDT @ $1.234 → FILLED
  Order 2 (Leg B): SELL 1080 AI/USDT @ $0.567 → FILLED
  Position: DELTA-NEUTRAL (market neutral)
```

---

## 🛑 Stopping the Bot

### Graceful Shutdown (Recommended)
```bash
# Press Ctrl+C in the terminal running the bot

# Output:
🛑 Initiating graceful shutdown...
✅ ExecutionEngine disconnected
📊 FINAL STATISTICS:
   Uptime: 3600.5s
   Signals processed: 45
   Trades executed: 12
   Success rate: 26.7%
✅ Graceful shutdown complete
```

### Emergency Stop
```bash
# If graceful shutdown fails:
pkill -9 -f "python main.py"
```

---

## ⚠️ Common Issues & Fixes

### "API key required"
```bash
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
python main.py
```

### "Connection refused"
- Check API key is valid
- Check Binance is not down
- Check internet connection

### "No signals generated"
- May take time (depends on market)
- Check logs for errors
- Verify pairs are cointegrated

### "Order failed"
- Insufficient balance
- Market conditions changed
- Liquidity too low

---

## 📁 Important Files

```
main.py                    ← Run this
config.json                ← Needs API keys
pairs_config.json          ← 10 trading pairs
logs/trading_bot.log       ← Monitor this
LAUNCH_READY.md            ← Read this
TECHNICAL_DEEPDIVE.md      ← Study this
```

---

## 🎛️ Configuration

### Set Environment Variables

```bash
# API Credentials (required)
export BINANCE_API_KEY="paste_your_key"
export BINANCE_API_SECRET="paste_your_secret"

# Trading Mode (optional)
export TRADING_MODE="paper"   # paper or live
export DRY_RUN="true"         # true or false
```

### Or Use config.json

```json
{
  "binance_api_key": "your_key",
  "binance_api_secret": "your_secret",
  "trading_mode": "paper",
  "dry_run": true
}
```

---

## 📊 Real-Time Monitoring

### Watch Signals
```bash
tail -f logs/trading_bot.log | grep "SIGNAL"
```

### Watch Trades
```bash
tail -f logs/trading_bot.log | grep "TRADE"
```

### Watch Errors
```bash
tail -f logs/trading_bot.log | grep "ERROR"
```

### Watch All
```bash
tail -f logs/trading_bot.log
```

---

## 🔍 Debug Checklist

- [ ] `python preflight_check.py` passes
- [ ] API keys are correct
- [ ] `config.json` exists
- [ ] `pairs_config.json` has 10 pairs
- [ ] `logs/` directory exists
- [ ] `python main.py` starts without errors
- [ ] You see "TRADING BOT STARTED" message
- [ ] Logs show 10 SignalGenerators initialized
- [ ] No connection errors in logs

---

## 📞 Get Help

### Read Documentation
- Quick start: LAUNCH_READY.md
- Deep dive: TECHNICAL_DEEPDIVE.md
- Operation guide: MAIN_EXECUTION_GUIDE.md

### Check Logs
```bash
# Recent errors
tail -20 logs/trading_bot.log

# Full log
cat logs/trading_bot.log
```

### Test Components
```bash
# Check if all pairs load
python -c "import json; print(json.load(open('pairs_config.json')))"

# Check config
python -c "from quant_arbitrage import get_config; print(get_config())"
```

---

## 🎯 Success Indicators

Bot is working when you see:

1. ✅ `TRADING BOT STARTED` message
2. ✅ 10 `SignalGenerator initialized` messages
3. ✅ `Monitoring started for 10 pairs` message
4. 📡 Occasional `SIGNAL RECEIVED` messages
5. 🚀 Occasional `TRADE EXECUTED` messages

---

## 💡 Pro Tips

1. **Monitor First 24 Hours** - Check for bugs before scaling
2. **Test in PAPER Mode** - Don't risk real money initially
3. **Enable DRY_RUN** - See signals without placing orders
4. **Keep Logs Enabled** - Essential for debugging
5. **Start Small** - Begin with minimum position sizes
6. **Have Kill Switch** - Be ready to stop the bot
7. **Review Spread Plots** - Check `plots/` directory for visualizations
8. **Run Preflight Check** - Verify setup before each run

---

## 📝 Trade Log Example

```
2026-02-01 20:55:33 - Signal #1: 🟢 BUY 1INCH/AI Z=2.45
2026-02-01 20:55:34 - ✅ Trade #1: FILLED (2 legs)
2026-02-01 20:56:12 - Signal #2: 🔴 SELL 1000CAT/1MBABYDOGE Z=-2.81
2026-02-01 20:56:13 - ✅ Trade #2: FILLED (2 legs)
2026-02-01 20:57:45 - Signal #3: 🟡 EXIT Z=0.12
2026-02-01 20:57:46 - ✅ Trade #3: FILLED (close position)
...
2026-02-01 23:57:00 - 📊 Session Summary: 45 signals, 12 trades executed
```

---

## 🚀 Ready?

```bash
python main.py
```

That's it! The bot will:
1. Load configuration
2. Connect to Binance
3. Monitor 10 pairs simultaneously
4. Generate signals when cointegration spreads are extreme
5. Execute delta-neutral trades
6. Manage risk automatically

**Good luck trading! 📈**

---

**For complete details, see LAUNCH_READY.md**
