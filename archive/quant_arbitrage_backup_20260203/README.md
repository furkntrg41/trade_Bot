# 🤖 Quant Arbitrage Bot - Proje Pivot Dokümantasyonu

## 📌 Genel Bakış

Bu proje, **Freqtrade + LightGBM** kullanan yön tahmini (directional) stratejisinden **Delta-Neutral Quantitative Arbitrage** yaklaşımına geçiş yapıyor.

**Eski Strateji:** RSI/MACD → ML prediction → Position (riskit)  
**Yeni Strateji:** Statistical Arbitrage + Funding Rate Arb → Market Neutral (risksiz/düşük risk)

---

## 🎯 Yeni Mimarinin 3 Ana Bileşeni

### 1️⃣ **Pairs Trading (Statistical Arbitrage)**

**Prensip:** İki varlığın kointegre olan fiyat serilerini kullanarak mean-reversion işlemleri yapma.

**Matematiksel Temel:**
```
Kointegrasyon: log(Y_t) ~ log(X_t)
Spread: Z_t = log(Y_t) - β*log(X_t)  (β = Hedge Ratio)
Z-Score: z = (Z_t - μ) / σ

Entry Signals:
- z > +2σ  → Spread açıldı → SHORT SPREAD (Y short, X long)
- z < -2σ  → Spread kapandı → LONG SPREAD (Y long, X short)

Exit:
- z → 0 (Mean reversion tamamlandı)
```

**Kullanılan Teknikler:**
- **Engle-Granger Kointegrasyon Testi** (statsmodels)
- **ADF (Augmented Dickey-Fuller)** Stationarity Testi
- **OLS Regresyon** Hedge Ratio hesabı
- **Kalman Filter** Dinamik β güncelleme
- **Z-Score** Sinyal üretimi

**Fayda:**
- ✅ Market yönünden bağımsız (delta-neutral)
- ✅ Fiyat trend'i önemli değil, spread mean-reversion'ı önemli
- ✅ Volatiliteden zararlı değil (kâr mean-reversion'dan gelir)

---

### 2️⃣ **Funding Rate Arbitrage (Cash & Carry)**

**Prensip:** Spot ve Futures arasındaki fiyat farkını ve funding fee'sini risksiz olarak kârlı hale getirme.

**Matematiksel Model:**
```
Spot Price: P_spot
Futures Price: P_fut
Funding Rate: r (per 8 hours)

Arbitrage:
- BUY Spot: 1 BTC @ P_spot
- SHORT Futures: 1 BTC @ P_fut
- Hold: 8 saat
- Collect Funding: r × notional

Total PnL = (P_spot - P_fut) + Funding - Costs
Costs = Trading fees + Borrow fee (spot short için)

Yıllıklandırılmış Funding = r × 365 × 3 (8h funding 3× per day)
```

**Delta-Neutral:** Fiyat hiç değişse bile, funding fee'si alıyorsun.

---

### 3️⃣ **Risk Management (Strict Rules)**

**Kelly Criterion + Position Sizing:**
```
Kelly % = (bp - q) / b
Fractional Kelly = Kelly % × 0.25 (safer)

p = Win Rate
q = 1 - p
b = Avg Win / Avg Loss

Position Size ∝ Max Loss / Distance to Stop Loss
```

**Constraints:**
- Max loss per trade: %1 of account
- Total delta exposure: <%10 (market neutral)
- Single symbol concentration: <%5
- Leverage: Dynamic (default 1-2x)

---

## 📁 Proje Yapısı

```
quant_arbitrage/
├── __init__.py                          # Package exports
├── requirements.txt                     # Dependencies
│
├── cointegration_analyzer.py            # Kointegrasyon testi & taraması
│   └── CointegrationAnalyzer
│       ├── test_cointegration()         # Engle-Granger testi
│       ├── calculate_hedge_ratio()      # OLS via statsmodels
│       ├── scan_universe()              # Tüm pairs'ı tara
│       └── _calculate_half_life()       # Mean reversion hızı
│
├── spread_calculator.py                 # Canlı Z-Score hesabı
│   ├── PairsSpreadCalculator            # Single pair için
│   │   ├── add_prices()                 # Yeni fiyat ekle
│   │   ├── _calculate_z_score()         # Rolling mean/std
│   │   └── _generate_signal()           # Entry/Exit sinyalleri
│   ├── KalmanFilterHedgeRatio           # Dinamik β güncelleme
│   └── MultiPairManager                 # Çoklu pairs yönetimi
│
├── websocket_provider.py                # Async WebSocket (low-latency)
│   └── BinanceWebSocketProvider         
│       ├── connect()                    # WSS bağlantı
│       ├── subscribe_ticker()           # aggTrade stream
│       ├── subscribe_book_ticker()      # Order book stream
│       ├── listen()                     # Async message loop
│       └── register_callback()          # Event-driven triggers
│
├── funding_arbitrage.py                 # Funding rate arb
│   ├── FundingRateMonitor               
│   │   ├── check_opportunity()          # Arb fırsatı tespiti
│   │   ├── open_position()              # Pozisyon aç
│   │   └── calculate_breakeven_funding()# Break-even threshold
│   └── FundingArbitrage (dataclass)    # Position tracking
│
├── risk_manager.py                      # Position sizing & constraints
│   ├── RiskManager
│   │   ├── calculate_kelly_size()       # Kelly criterion
│   │   ├── calculate_position_size()    # Risk parity sizing
│   │   ├── check_constraints()          # Delta/concentration checks
│   │   ├── add_position()               # Position register
│   │   └── remove_position()            # Position close
│   └── PositionSide (enum)             # LONG / SHORT
│
└── main_bot.py                          # Main orchestrator
    └── QuantArbitrageBot
        ├── initialize()
        ├── scan_cointegration()         # Offline scanning
        ├── run()                        # Main event loop
        ├── _process_pairs_signals()     # Pairs trading logic
        └── _check_funding_opportunity() # Funding arb logic
```

---

## 🚀 Kullanım Örneği

### 1. Kointegrasyon Taraması (One-time Offline)

```python
import numpy as np
from quant_arbitrage import CointegrationAnalyzer

# Geçmiş veriyi yükle
historical_data = {
    "BTC": np.array([...]),  # 252 daily prices
    "ETH": np.array([...]),
    "SOL": np.array([...]),
    # ...
}

# Tarama
analyzer = CointegrationAnalyzer(
    lookback_window=252,
    adf_pvalue_threshold=0.05,
    coint_pvalue_threshold=0.05,
)

top_pairs = analyzer.scan_universe(historical_data, top_n=10)

for result in top_pairs:
    print(result)
    # Output:
    # BTC vs ETH | Hedge: 14.2340 | ADF p: 0.0123 | Coint p: 0.0089 | ✅ CO-INT | Half-life: 5.3
```

### 2. Canlı Pairs Trading

```python
from quant_arbitrage import PairsSpreadCalculator, SignalType

# Hedge ratio'yu al (kointegrasyon testinden)
calc = PairsSpreadCalculator(
    hedge_ratio=14.2340,
    lookback_periods=252,
    z_score_threshold=2.0,
)

# Her yeni candle'da
while True:
    btc_price = get_price("BTCUSDT")
    eth_price = get_price("ETHUSDT")
    
    signal = calc.add_prices(btc_price, eth_price)
    
    if signal.signal == SignalType.LONG_SPREAD:
        # Y long, X short
        print(f"LONG SPREAD: Z={signal.z_score:.2f}")
    
    elif signal.signal == SignalType.SHORT_SPREAD:
        # Y short, X long
        print(f"SHORT SPREAD: Z={signal.z_score:.2f}")
    
    elif signal.signal == SignalType.EXIT_LONG:
        print("Close position")
```

### 3. WebSocket Real-time Data

```python
import asyncio
from quant_arbitrage import BinanceWebSocketProvider

provider = BinanceWebSocketProvider(use_testnet=False)

async def on_trade(data):
    symbol = data["symbol"]
    price = data["price"]
    print(f"{symbol} traded @ {price}")

async def on_book(data):
    symbol = data["symbol"]
    bid = data["bid"]
    ask = data["ask"]
    print(f"{symbol}: bid={bid}, ask={ask}")

provider.register_callback("agg_trade", on_trade)
provider.register_callback("book_ticker", on_book)

# Run
await provider.run(["BTCUSDT", "ETHUSDT"])
```

### 4. Funding Rate Arbitrage

```python
from quant_arbitrage import FundingRateMonitor

monitor = FundingRateMonitor(
    annualized_funding_threshold=0.05,  # %5 yıllık
)

# Fırsatı kontrol et
opportunity = monitor.check_opportunity(
    symbol="BTC",
    current_funding_rate=0.00045,  # +0.045%
    spot_bid=78100, spot_ask=78110,
    futures_bid=78150, futures_ask=78160,
)

if opportunity == FundingStatus.POSITIVE_FUNDING:
    # Spot al, Futures short
    monitor.open_position("BTC", 78105, 78155, 0.1)
    print("✅ Arbitrage açıldı")
```

### 5. Risk Management

```python
from quant_arbitrage import RiskManager, PositionSide

rm = RiskManager(
    account_equity=10000,
    max_loss_per_trade=0.01,  # %1
)

# Position size hesapla
size = rm.calculate_position_size(
    symbol="BTC_ETH",
    entry_price=78200,
    stop_loss_price=79604,  # 2% away
    volatility=0.30,  # 30% annual
)

# Position ekle
rm.add_position(
    symbol="BTC_ETH",
    side=PositionSide.LONG,
    size=size,
    entry_price=78200,
    delta=0.8,  # Pairs trading daha düşük
)

print(rm.get_summary())
```

---

## 🔑 Key Features

| Feature | Implementation | Benefit |
|---------|----------------|---------|
| **Kointegrasyon** | Engle-Granger + ADF | İstatistiksel olarak geçerli pair'ler |
| **Hedge Ratio** | OLS Regresyon | Optimal spread ağırlığı |
| **Kalman Filter** | Adaptive β | Changing market conditions'a uyum |
| **Z-Score** | Rolling mean/std | Mean reversion sinyalleri |
| **WebSocket** | Async/Await | Low-latency real-time data |
| **Kelly Criterion** | Fractional (0.25) | Optimal position sizing |
| **Delta Hedging** | Portfolio tracking | Market neutral exposure |
| **Funding Arb** | REST API integration | Risksiz getiri |

---

## ⚠️ Risk Disclaimers

1. **Backtesting vs Live:** Historical kointegrasyon gelecekte garanti değildir
2. **Execution Risk:** Entry/exit latency spread tahminini etkiler
3. **Liquidity:** Binance dışı exchange'lerde problem olabilir
4. **Regulatory:** Marjin trading ve short'lar bölgeye göre kısıtlı olabilir
5. **Black Swan:** Extreme market stress'te model başarısız olabilir

---

## 📊 Performance Beklentileri

**Pairs Trading:**
- Win Rate: %55-65% (mean reversion stable)
- Avg Win: %0.5-2%
- Avg Loss: -%0.5-2%
- Expected Return: %10-20% annually (net fees)

**Funding Arbitrage:**
- Annual Funding: %5-15% (funding rate'e bağlı)
- Risk-Free: Evet (delta-neutral)
- Limitation: Capital tied up

---

## 🛠️ Installation

```bash
# Clone repo
git clone https://github.com/furkntrg41/trade_Bot.git
cd trade_Bot/quant_arbitrage

# Install dependencies
pip install -r requirements.txt

# Run examples
python main_bot.py
```

---

## 📝 Next Steps (Implementation Roadmap)

- [ ] REST API Funding Rate fetcher
- [ ] Order placement integration (Binance API)
- [ ] Database logging (trade history)
- [ ] Backtesting engine
- [ ] Performance monitoring dashboard
- [ ] Machine learning for pair selection
- [ ] Cross-exchange arbitrage

---

**Status:** Prototype / Research  
**Author:** Quant Team  
**Last Updated:** 2026-02-01
