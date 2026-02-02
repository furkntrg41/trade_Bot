# 🚀 AKTIF TEKNOLOJI STACKı - DETAYLI ANALİZ (2026)

**Tarih**: 2 Şubat 2026  
**Proje**: Freqtrade Bot + Quant Arbitrage Engine  
**Durum**: PRODUCTION READY

---

## 📊 TEKNOLOJİ HARITASI

```
┌──────────────────────────────────────────────────────────────┐
│                   RUNTIME & ORCHESTRATION                     │
├──────────────────────────────────────────────────────────────┤
│ ✅ Python 3.9+              → Bot kodu ve core logic          │
│ ✅ AsyncIO                  → Asynchronous event loop          │
│ ✅ Docker & Docker Compose  → VPS deployment & containerization│
│ ✅ Hetzner VPS (CPX22)      → Production server (4GB RAM)     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              DATA PROCESSING & COMPUTATION                    │
├──────────────────────────────────────────────────────────────┤
│ ✅ NumPy 1.24+              → Numerik hesaplamalar            │
│ ✅ Pandas 2.0+              → Time-series DataFrame işlemleri  │
│ ✅ SciPy 1.10+              → Statistical tests (ADF, Coint)   │
│ ✅ Statsmodels 0.13+        → Cointegration tests             │
│ ✅ Scikit-learn 1.3+        → ML preprocessing & pipelines    │
│ ✅ TA-Lib 0.4+              → Technical indicators (RSI, MACD) │
│ ✅ QTPyLib                  → BBands, VWAP hesaplamaları     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              MACHINE LEARNING (OPTIONAL)                      │
├──────────────────────────────────────────────────────────────┤
│ ⏸️  LightGBM 4.0+             → Freqtrade/FreqAI ML model      │
│     (Opsiyonel: config'de aktif değil, ama Freqtrade         │
│      tarafından desteklenebilir)                             │
│                                                              │
│ ⏸️  Freqtrade FreqAI          → ML framework (destekli)       │
│     (Opsiyonel: strategy'de tanımlanmış ama                  │
│      main.py'de doğrudan kullanılmıyor)                      │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              EXCHANGE API & REAL-TIME DATA                    │
├──────────────────────────────────────────────────────────────┤
│ ✅ CCXT 2.0+                 → Binance Futures API client      │
│ ✅ WebSockets 11.0+          → Real-time Binance stream        │
│ ✅ aiohttp 3.8+              → Async HTTP (REST API)          │
│ ✅ asyncio.gather()          → Concurrent stream subscription  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              EXTERNAL DATA SOURCES (OPTIONAL)                 │
├──────────────────────────────────────────────────────────────┤
│ ⏸️  CoinGecko API             → Sentiment data (opsiyonel)     │
│     (FreqAI strategy'de tanımlanmış, ama                     │
│      main.py bot'ta aktif değil)                            │
│                                                              │
│ ⏸️  Alternative.me            → Fear & Greed Index            │
│ ⏸️  CryptoPanic               → News sentiment               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              FRAMEWORK (Freqtrade)                            │
├──────────────────────────────────────────────────────────────┤
│ ⏸️  Freqtrade 2026.2+         → Trading bot framework          │
│     (Strategy'de tanımlanmış ama, main.py'de                 │
│      tamamen independent QUANT_ARBITRAGE motoru              │
│      kullanıyor)                                             │
│                                                              │
│ ⏸️  Freqtrade IStrategy       → Abstract base class           │
│ ⏸️  Freqtrade FreqAI          → ML integration               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              UTILITIES & HELPERS                              │
├──────────────────────────────────────────────────────────────┤
│ ✅ json                       → Config parsing                 │
│ ✅ logging                    → Structured logging (3 cat.)    │
│ ✅ asyncio.Lock()             → Concurrency control            │
│ ✅ dataclasses                → Type-safe data structures      │
│ ✅ pathlib.Path               → File operations               │
│ ✅ datetime                   → Time handling                 │
│ ✅ typing                     → Type hints                    │
│ ✅ signal (POSIX)             → Graceful shutdown             │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔴 GERÇEKTEN AKTIF OLAN TEKNOLOJİLER

### **TIER 1: CORE RUNTIME (SİSTEME ALTYAPI)**

#### **1. Python 3.9+** ✅
- **Nerede**: Tüm .py dosyaları
- **Kullanım**: Bot core logic, quant module, strategies
- **Kritik**: Evet
- **İmport**: 
  ```python
  # main.py, execution_engine.py, vb.
  import asyncio
  import json
  import logging
  from pathlib import Path
  from typing import Dict, List, Optional
  from datetime import datetime
  from dataclasses import dataclass
  from enum import Enum
  ```

#### **2. AsyncIO** ✅
- **Nerede**: main.py, execution_engine.py, websocket_provider.py
- **Kullanım**: Concurrent task management, non-blocking I/O
- **Kritik**: Evet (real-time tick processing)
- **Örnekler**:
  ```python
  async def initialize_components() -> bool:
      await self.execution_engine.connect()
      
  async def watch_pair(self, pair_id: str):
      tasks = [...]
      await asyncio.gather(*tasks)
      
  asyncio.Lock()  # Concurrency control
  ```

#### **3. Docker + Docker Compose** ✅
- **Nerede**: `Dockerfile`, `docker-compose.yml`, `docker-compose.production.yml`
- **Kullanım**: 
  - Hetzner VPS'de bot'ü containerize ve çalıştırma
  - Reproducible environment
  - Automated health checks
- **Kritik**: Evet (VPS deployment)
- **Konfigürasyon**:
  ```dockerfile
  FROM freqtradeorg/freqtrade:develop_freqai
  ENV TZ=UTC
  HEALTHCHECK --interval=60s CMD curl -f http://localhost:8080/api/v1/ping
  ```

---

### **TIER 2: DATA PROCESSING & COMPUTATION**

#### **1. NumPy 1.24+** ✅
- **Nerede**: 
  - `cointegration_analyzer.py` (ADF, regression)
  - `spread_calculator.py` (Z-Score, rolling stats)
  - Tests (test_zscore_*.py)
- **Kullanım**:
  ```python
  import numpy as np
  
  # Z-Score calculation
  spread = np.log(price_y) - np.log(price_x)
  z_score = (spread - np.mean(spread)) / np.std(spread)
  
  # Rolling windows
  rolling_mean = np.convolve(spread, np.ones(20)/20, mode='valid')
  ```
- **Kritik**: Evet (core math)

#### **2. Pandas 2.0+** ✅
- **Nerede**:
  - `cointegration_analyzer.py` (DataFrame işlemleri)
  - `FreqaiExampleStrategy.py` (technical indicators)
  - `spread_calculator.py` (time-series)
- **Kullanım**:
  ```python
  import pandas as pd
  from pandas import DataFrame
  
  # DataFrame işlemleri
  df['rolling_mean'] = df['price'].rolling(window=20).mean()
  df['z_score'] = (df['spread'] - df['rolling_mean']) / df['rolling_std']
  ```
- **Kritik**: Evet (time-series management)

#### **3. SciPy 1.10+** ✅
- **Nerede**:
  - `cointegration_analyzer.py` (stats)
  - `spread_calculator.py` (signal processing)
- **Kullanım**:
  ```python
  from scipy import stats, signal
  
  # Statistical tests
  adf_stat, adf_pval, _, _, _, _ = adfuller(residuals)
  
  # Signal processing (filtering)
  filtered = signal.lfilter(b, a, spread)
  ```
- **Kritik**: Evet (cointegration tests)

#### **4. Statsmodels 0.13+** ✅
- **Nerede**: `cointegration_analyzer.py`
- **Kullanım**: 
  ```python
  from statsmodels.tsa.stattools import adfuller, coint
  from statsmodels.regression.linear_model import OLS
  
  # ADF test for stationarity
  adf_stat, adf_pval, _, _ = adfuller(prices, maxlag=20)
  
  # Cointegration test (Johansen)
  coint_stat, coint_pval, _ = coint(y, x)
  
  # OLS regression for hedge ratio
  model = OLS(prices_y, add_constant(prices_x))
  results = model.fit()
  hedge_ratio = results.params[1]
  ```
- **Kritik**: Evet (kointegrasyon tespiti)

#### **5. TA-Lib 0.4+** ✅
- **Nerede**: `FreqaiExampleStrategy.py`
- **Kullanım**:
  ```python
  import talib.abstract as ta
  
  # Technical indicators for FreqAI model features
  rsi = ta.RSI(dataframe['close'], timeperiod=14)
  macd = ta.MACD(dataframe['close'])
  bb_upper, bb_middle, bb_lower = ta.BBANDS(dataframe['close'])
  ```
- **Kritik**: Medium (FreqAI ML features)

#### **6. Scikit-learn 1.3+** ✅ (OPSIYONEL)
- **Nerede**: Potansiyel olarak `FreqaiExampleStrategy.py` preprocessing
- **Kullanım**: Feature scaling, preprocessing pipelines
- **Kritik**: Low (Direct use'a gerek yok, LightGBM kendi handle ediyor)

#### **7. QTPyLib** ✅
- **Nerede**: `FreqaiExampleStrategy.py`
- **Kullanım**: 
  ```python
  from technical import qtpylib
  
  # Technical analysis helpers
  bb = qtpylib.bollinger_bands(dataframe['close'])
  ```
- **Kritik**: Low-Medium (Freqtrade integration)

---

### **TIER 3: EXCHANGE & REAL-TIME DATA**

#### **1. CCXT 2.0+** ✅
- **Nerede**:
  - `execution_engine.py` (order placement)
  - `cointegration_scanner.py` (market data)
  - `scripts/state_recovery.py` (crash recovery)
  - `websocket_provider.py` (backup REST fallback)
- **Kullanım**:
  ```python
  import ccxt.async_support as ccxt
  
  # Binance Futures connection
  exchange = ccxt.binance({
      'apiKey': api_key,
      'secret': api_secret,
      'enableRateLimit': True,
      'options': {'defaultType': 'future'}
  })
  
  # Order operations
  order = await exchange.create_order(
      symbol='BTC/USDT:USDT',
      type='limit',
      side='buy',
      amount=0.1,
      price=50000
  )
  
  # Market data
  ticker = await exchange.fetch_ticker('BTC/USDT:USDT')
  positions = await exchange.fetch_positions()
  ```
- **Kritik**: Evet (Binance bağlantısı)

#### **2. WebSockets 11.0+** ✅
- **Nerede**: `websocket_provider.py`, `signal_generator.py`
- **Kullanım**:
  ```python
  import websockets
  import asyncio
  
  async def subscribe_stream(self, symbol: str):
      uri = f"wss://fstream.binance.com/ws/{symbol.lower()}@aggTrade"
      async with websockets.connect(uri) as websocket:
          while True:
              data = await websocket.recv()
              await self.on_tick(json.loads(data))
  ```
- **Kritik**: Evet (real-time tick data)

#### **3. aiohttp 3.8+** ✅
- **Nerede**: `websocket_provider.py` (backup), potential REST calls
- **Kullanım**:
  ```python
  import aiohttp
  
  async def fetch_data(self, url):
      async with aiohttp.ClientSession() as session:
          async with session.get(url) as resp:
              return await resp.json()
  ```
- **Kritik**: Medium (Async HTTP requests)

---

### **TIER 4: OPSİYONEL/COMPLEMENTARY TEKNOLOJILER**

#### **1. LightGBM 4.0+** ⏸️ (PASSIVE)
- **Nerede**: `FreqaiExampleStrategy.py` (Freqtrade tarafından yönetilir)
- **Durumu**: 
  - Config'de `"identifier": "freqai_lightgbm_futures"` olarak tanımlanmış
  - Ama main.py bot'ta direkt olarak kullanılmıyor
  - Freqtrade'in FreqAI modülü tarafından arka planda eğitilir
  - `user_data/models/` klasöründe saklanır
- **Kullanım** (eğer aktif olursa):
  ```python
  # LightGBM modeli Freqtrade tarafından yönetilir
  # FreqAI veri pipelinesi:
  # 1. 45 gün veri toplayıp train et
  # 2. 10 gün backtest et
  # 3. Live predictions için 2 saatte retrain et
  ```
- **Kritik**: Low (main.py bot'ta kullanılmıyor)

#### **2. Freqtrade Framework** ⏸️ (PARTIAL)
- **Nerede**: `user_data/strategies/FreqaiExampleStrategy.py`
- **Durumu**:
  - Strategy tanımlandı ama main.py'de kullanılmıyor
  - main.py kendi independent QUANT_ARBITRAGE bot'unu çalıştırıyor
  - Freqtrade config'de tanımlanmış (dry_run, leverage, vb.)
  - Docker-compose'ta `--strategy FreqaiExampleStrategy` argümanı var
- **Nasıl çalışır**:
  ```
  main.py (AKTIF) → Quant Arbitrage Engine (Cointegration Trading)
            ↓
  user_data/strategies/FreqaiExampleStrategy.py (PASSIVE) → Freqtrade framework
  ```
- **Kritik**: Low (dual deployment mümkün ama şu anda main.py aktif)

#### **3. External Sentiment APIs** ⏸️ (OPTIONAL)
- **CoinGecko API**: Opsiyonel sentiment data
  ```python
  # FreqaiExampleStrategy.py'de tanımlanmış
  def _get_coingecko_data(self, coin_id: str) -> dict:
      url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
      # Rate limit tasarrufu için
  ```
- **Alternative.me**: Fear & Greed Index
- **CryptoPanic**: News sentiment
- **Durumu**: Opsiyonel, main.py bot'ta kullanılmıyor

---

## 🎯 AKTIF TEKNOLOJI ÖZET TABLOSU

| Teknoloji | Sürüm | Aktif? | Kritik? | Dosya |
|-----------|-------|--------|--------|-------|
| **Python** | 3.9+ | ✅ | 🔴 | Tüm |
| **AsyncIO** | Built-in | ✅ | 🔴 | main.py, execution_engine.py |
| **Docker** | Latest | ✅ | 🔴 | Dockerfile, docker-compose.yml |
| **NumPy** | 1.24+ | ✅ | 🔴 | cointegration_analyzer.py, spread_calculator.py |
| **Pandas** | 2.0+ | ✅ | 🔴 | cointegration_analyzer.py, FreqaiExampleStrategy.py |
| **SciPy** | 1.10+ | ✅ | 🔴 | cointegration_analyzer.py, spread_calculator.py |
| **Statsmodels** | 0.13+ | ✅ | 🔴 | cointegration_analyzer.py |
| **CCXT** | 2.0+ | ✅ | 🔴 | execution_engine.py, cointegration_scanner.py |
| **WebSockets** | 11.0+ | ✅ | 🔴 | websocket_provider.py |
| **aiohttp** | 3.8+ | ✅ | 🟡 | websocket_provider.py |
| **TA-Lib** | 0.4+ | ✅ | 🟡 | FreqaiExampleStrategy.py |
| **QTPyLib** | Latest | ✅ | 🟡 | FreqaiExampleStrategy.py |
| **LightGBM** | 4.0+ | ⏸️ | 🟡 | FreqaiExampleStrategy.py (passive) |
| **Freqtrade** | 2026.2+ | ⏸️ | 🟢 | Strategy only |
| **Scikit-learn** | 1.3+ | ⏸️ | 🟢 | Optional preprocessing |

**Açıklamalar:**
- 🔴 **Kritik**: Olmadan bot çalışmaz
- 🟡 **Önemli**: Feature'lar için gerekli
- 🟢 **Opsiyonel**: Olmadan bot çalışır ama sınırlı

---

## 📂 KOD MAKETASı - TEKNOLOJİ DAĞILIMI

```
c:\Users\furka\Desktop\freqtrade_bot
├── main.py (511 satır)
│   ├── Python 3.9, AsyncIO, dataclasses
│   ├── Config loading (JSON)
│   ├── Quant Arbitrage Engine (AKTIF MOTOR)
│   └── WebSocket orchestration
│
├── quant_arbitrage/ (Ana motor)
│   ├── config.py (257 satır)
│   │   └── Python, dataclasses, enum
│   │
│   ├── execution_engine.py (1046 satır) ⭐
│   │   ├── CCXT (Binance Futures API)
│   │   ├── asyncio.Lock (concurrency)
│   │   ├── dataclasses, enum
│   │   └── Type hints
│   │
│   ├── signal_generator.py (462 satır)
│   │   ├── WebSockets (real-time data)
│   │   ├── NumPy, Pandas
│   │   ├── asyncio
│   │   └── Data structures
│   │
│   ├── cointegration_analyzer.py (344 satır) ⭐
│   │   ├── NumPy (numeric computation)
│   │   ├── Pandas (DataFrame)
│   │   ├── SciPy (stats)
│   │   ├── Statsmodels (ADF, Coint tests)
│   │   └── OLS regression
│   │
│   ├── spread_calculator.py (366 satır)
│   │   ├── NumPy (Z-Score, rolling stats)
│   │   ├── SciPy (signal processing)
│   │   ├── Pandas
│   │   └── Mean reversion logic
│   │
│   ├── risk_manager.py (303 satır)
│   │   ├── NumPy (Kelly Criterion)
│   │   └── Position sizing
│   │
│   ├── websocket_provider.py (402 satır)
│   │   ├── WebSockets 11.0+
│   │   ├── aiohttp 3.8+
│   │   ├── asyncio
│   │   └── CCXT (fallback)
│   │
│   ├── cointegration_scanner.py (500+ satır)
│   │   ├── CCXT (Binance data)
│   │   ├── NumPy, Pandas
│   │   ├── Statsmodels
│   │   ├── Matplotlib (plots - optional)
│   │   └── Async operations
│   │
│   ├── funding_arbitrage.py
│   │   └── Optional funding rate arbitrage
│   │
│   └── __init__.py
│
├── user_data/strategies/
│   └── FreqaiExampleStrategy.py (792 satır) ⏸️
│       ├── Freqtrade framework (passive)
│       ├── LightGBM (via Freqtrade/FreqAI)
│       ├── TA-Lib (technical indicators)
│       ├── Pandas, NumPy
│       ├── External APIs (CoinGecko - optional)
│       └── 2x Leverage futures
│
├── tests/ (10 test dosyası)
│   ├── test_zscore_simple.py (232 satır)
│   │   └── NumPy, unittest
│   ├── test_crash_recovery.py (382 satır)
│   │   └── unittest, mock, asyncio
│   ├── test_execution_sabotage.py (235 satır)
│   │   └── unittest, mock, asyncio
│   └── [7 daha...]
│
├── scripts/
│   ├── logging_config.py (171 satır)
│   │   └── logging, pathlib
│   └── state_recovery.py (372 satır)
│       ├── CCXT
│       ├── asyncio
│       ├── JSON
│       └── Crash recovery
│
├── config.json
│   └── Freqtrade + API configuration
│
├── pairs_config.json
│   └── Cointegrated pairs (Quant Arbitrage)
│
├── Dockerfile
│   └── Docker (freqtradeorg/freqtrade:develop_freqai base)
│
├── docker-compose.yml
│   └── Dev environment (3 GB RAM)
│
└── docker-compose.production.yml
    └── Hetzner CPX22 (3.5 GB limit)
```

---

## 🔥 EN KRITIK 5 TEKNOLOJİ (BOT ÇALIŞMASI İÇİN GEREKLI)

### **1. CCXT (Crypto exchange API)**
```
WHY: Binance Futures'a bağlantı, order placement, position tracking
WHERE: execution_engine.py, cointegration_scanner.py, state_recovery.py
CRITICAL: 🔴 WITHOUT IT, NO TRADING
USAGE: 
  - Ticker data fetch
  - Order creation/cancellation
  - Position management
  - Funding rates
```

### **2. WebSockets (Real-time data)**
```
WHY: Aggravated trade ticks (1ms latency vs 1s REST polling)
WHERE: websocket_provider.py, signal_generator.py
CRITICAL: 🔴 WITHOUT IT, SIGNALS DELAYED 1000x
USAGE:
  - Subscribe to BTC/USDT:USDT@aggTrade
  - Stream 100s of ticks/second
  - Feed to Z-Score calculator
```

### **3. NumPy + Pandas + SciPy**
```
WHY: Core math - Z-Score, hedge ratios, cointegration tests
WHERE: cointegration_analyzer.py, spread_calculator.py
CRITICAL: 🔴 WITHOUT IT, NO SIGNAL GENERATION
USAGE:
  - ADF test (stationarity)
  - Johansen cointegration test
  - Rolling mean/std (Z-Score)
  - OLS regression (hedge ratio)
```

### **4. Statsmodels**
```
WHY: Statistical tests for pair detection
WHERE: cointegration_analyzer.py
CRITICAL: 🔴 CORE QUANT LOGIC
USAGE:
  - adfuller() → ADF test
  - coint() → Johansen test
  - OLS → Hedge ratio estimation
```

### **5. AsyncIO**
```
WHY: Concurrent execution of multiple pair streams
WHERE: main.py, execution_engine.py, signal_generator.py
CRITICAL: 🔴 WITHOUT IT, SINGLE-PAIR BOTTLENECK
USAGE:
  - asyncio.gather() → Parallel streams
  - asyncio.Lock() → Race condition prevention
  - async/await → Non-blocking I/O
```

---

## 🚫 OLMAYAN/PASIF TEKNOLOJİLER

| Teknoloji | Neden Pasif? | Durum |
|-----------|-------------|-------|
| **LightGBM** | main.py bot'ta kullanılmıyor, sadece Freqtrade framework'te | Opsiyonel |
| **Freqtrade** | Strategy tanımlanmış ama bot main.py ile çalışıyor | Dual deployment |
| **CoinGecko API** | FreqaiExampleStrategy'de tanımlanmış ama aktif değil | Opsiyonel |
| **Matplotlib** | Scanner'da plots için var ama mainbot'ta yok | Debugging only |
| **Scikit-learn** | LightGBM'in kendi preprocessing'i var | Redundant |
| **TensorFlow** | Hiç yüklü değil | Yok |
| **PyTorch** | Hiç yüklü değil | Yok |

---

## 💾 REQUIREMENTS.TXT (ACTUAL)

```
# Core
statsmodels>=0.13.5      ✅ AKTIF (ADF, Coint tests)
pandas>=2.0.0            ✅ AKTIF (DataFrame)
numpy>=1.24.0            ✅ AKTIF (Numeric)
scipy>=1.10.0            ✅ AKTIF (Stats)

# Exchange & Real-time
websockets>=11.0         ✅ AKTIF (WebSocket streams)
aiohttp>=3.8.0           ✅ AKTIF (Async HTTP)
ccxt>=2.0.0              ✅ AKTIF (Binance API)

# Utilities
python-dotenv>=0.21.0    ✅ AKTIF (Env vars)

# Optional (Freqtrade ecosystem)
python-talib            ⏸️  (FreqaiExampleStrategy only)
freqtrade              ⏸️  (Strategy framework)
lightgbm               ⏸️  (FreqAI model, opsiyonel)
```

---

## 🎯 ÖZET - PROJE NEYİ KULLANIYOR?

### **QUANTITATIVE ARBITRAGE ENGINE (Main Bot)**
Şu teknolojileri AKTIF olarak kullanıyor:

```python
# 1. Data Processing
NumPy, Pandas, SciPy, Statsmodels
    ↓
# 2. Pair Detection
Cointegration Tests (ADF, Johansen)
    ↓
# 3. Signal Generation
Z-Score Calculation
    ↓
# 4. Exchange Connection
CCXT (Binance Futures)
    ↓
# 5. Real-time Streams
WebSockets (aggTrade@stream)
    ↓
# 6. Order Execution
CCXT async API
    ↓
# 7. Concurrency
AsyncIO + asyncio.Lock()
```

### **FREQTRADE STRATEGY (Passive)**
Freqtrade ekosistemindeki alternatif strategy:
- LightGBM ML model
- TA-Lib technical indicators
- CoinGecko sentiment (optional)

---

## 🚀 BOTTOM LINE

**Proje 2 şekilde çalışabilir:**

1. **AKTIF (main.py)**: 
   - Quant Arbitrage Engine
   - Cointegration-based trading
   - Real-time WebSocket'ler
   - Pure Python + NumPy/Pandas/Statsmodels
   - Docker'da çalışıyor şu anda

2. **PASIF (Freqtrade)**: 
   - FreqaiExampleStrategy.py
   - LightGBM ML predictions
   - Technical indicators
   - Freqtrade framework tarafından yönetilir
   - Opsiyonel, docker-compose'ta tanımlanmış

**Şu anda AKTIF olan**: main.py + quant_arbitrage module (statistical arbitrage)

---

**Son Update**: 2 Şubat 2026 - Hetzner VPS'de çalışıyor ✅
