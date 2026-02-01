# 🤖 Furkan'ın Borsa Botu - Tam Teknoloji Stack'i

## 📋 İçindekiler
1. [Sistem Mimarisi](#sistem-mimarisi)
2. [Kullanılan Teknolojiler](#kullanılan-teknolojiler)
3. [ML Algoritmaları](#ml-algoritmaları)
4. [Feature Engineering](#feature-engineering)
5. [Entry/Exit Stratejileri](#entryexit-stratejileri)
6. [Veri Kaynakları](#veri-kaynakları)
7. [Konfigürasyon](#konfigürasyon)
8. [Trade Akışı](#trade-akışı)

---

## 🏗️ Sistem Mimarisi

```
┌─────────────────────────────────────────────────────┐
│         FREQAI MACHINE LEARNING FRAMEWORK           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐      ┌──────────────┐            │
│  │ Data Layer   │      │ Model Layer  │            │
│  ├──────────────┤      ├──────────────┤            │
│  │ • Binance    │      │ • LightGBM   │            │
│  │   Futures    │      │ • Regression │            │
│  │ • Historical │      │ • AutoML     │            │
│  │   Data       │      │                           │
│  └──────────────┘      └──────────────┘            │
│         │                      │                    │
│         └──────────────────────┘                    │
│                │                                    │
│         ┌──────────────┐                            │
│         │ FreqAI Core  │                            │
│         │ Data Kitchen │                            │
│         └──────────────┘                            │
│                │                                    │
│  ┌────────────────────────────────────┐            │
│  │   Feature Engineering Pipeline     │            │
│  │  (Technical Indicators + Sentiment)│            │
│  └────────────────────────────────────┘            │
└─────────────────────────────────────────────────────┘
         │
         └──────────────────────────────────────┐
                                                │
                    ┌───────────────────────────┴───┐
                    │                               │
        ┌─────────────────────────┐   ┌──────────────────────┐
        │  SENTIMENT DATA LAYER   │   │  TECHNICAL LAYER     │
        ├─────────────────────────┤   ├──────────────────────┤
        │ • CoinGecko API         │   │ • RSI, MACD, BB      │
        │ • CryptoPanic News      │   │ • EMA, SMA           │
        │ • Fear & Greed Index    │   │ • ATR, ROC, CCI      │
        │ • Binance Funding Rate  │   │ • Multi-Timeframe    │
        └─────────────────────────┘   └──────────────────────┘
                    │                               │
                    └───────────────────┬───────────┘
                                        │
                    ┌───────────────────────────────┐
                    │   ENTRY/EXIT DECISION LOGIC   │
                    │   (Adaptive Thresholds)       │
                    └───────────────────────────────┘
                                        │
                    ┌───────────────────────────────┐
                    │  ORDER MANAGEMENT             │
                    │  (Entry/Exit/TP/SL)           │
                    └───────────────────────────────┘
                                        │
                    ┌───────────────────────────────┐
                    │  BINANCE FUTURES (2x Leverage)│
                    │  • Dry-Run / Live Trading     │
                    └───────────────────────────────┘
```

---

## 🔧 Kullanılan Teknolojiler

### 🐍 Ana Framework'ler
| Teknoloji | Sürüm | Kullanım |
|-----------|-------|---------|
| **Freqtrade** | 2026.2-dev | Ana trading bot framework |
| **FreqAI** | Built-in | Machine Learning integrasyonu |
| **Python** | 3.14+ | Programlama dili |
| **Docker** | Latest | VPS'de containerization |

### 📊 Data Processing & ML
| Teknoloji | Sürüm | Kullanım |
|-----------|-------|---------|
| **Pandas** | 2.1+ | DataFrame işlemleri |
| **NumPy** | 1.24+ | Numerik hesaplamalar |
| **LightGBM** | 4.0+ | Gradient Boosting ML Model |
| **Scikit-learn** | 1.3+ | Preprocessing & Pipelines |
| **TA-Lib** | 0.4+ | Technical Analysis (RSI, MACD, vb) |
| **QTPyLib** | Latest | Bollinger Bands, VWAP hesaplamaları |

### 🌐 API & Data Kaynakları
| Kaynak | Endpoint | Kullanım |
|--------|----------|---------|
| **Binance** | CCXT | Futures trading, price data, funding rates |
| **CoinGecko** | REST API | 7d sentiment, price changes, events |
| **CryptoPanic** | REST API | News sentiment, market events |
| **Alternative.me** | REST API | Fear & Greed Index |

### 🚀 Deployment & Infrastructure
| Teknoloji | Özel Ayar | Kullanım |
|-----------|-----------|---------|
| **Hetzner VPS** | CPX22 (2vCPU, 3.7GB RAM) | Bot çalıştırma |
| **Docker Compose** | 3.8 | Multi-container orchestration |
| **Nginx** | Reverse proxy | API endpoint'leri (optional) |
| **FreqUI** | Web Interface | Dashboard & monitoring |

---

## 🧠 ML Algoritmaları

### 1. **LightGBM (Light Gradient Boosting Machine)**

**Nedir?** Microsoft tarafından geliştirilen, hızlı ve hafif gradient boosting framework'ü.

**Neden kullanıldı?**
- ✅ Düşük latency (trading için kritik)
- ✅ Düşük RAM kullanımı (VPS'de important)
- ✅ Paralel işleme (2 job ile eğitim ~30-40 saniye)
- ✅ Feature importance gösterimi

**Modeliniz ayarları:**
```json
{
  "n_estimators": 600,        // 600 karar ağacı
  "learning_rate": 0.01,       // Yavaş öğrenme (overfitting önleme)
  "max_depth": 8,              // Ağaç derinliği (basit tutmak için)
  "num_leaves": 48,            // Yaprak sayısı
  "min_child_samples": 30,     // Min örnek sayısı (noise'tan koruma)
  "n_jobs": 2,                 // 2 CPU core paralel işleme
  "verbosity": -1              // Log kapatma
}
```

**Nasıl çalışır?**
1. 45 gün geçmiş veri (training) + 10 gün (backtest) ile eğitilir
2. 25% test seti ile doğrulanır
3. **Target**: Gelecek 20 mum (2 saat) sonraki fiyat değişimi (%)
4. **Çıktı**: `-3 ile +3` arasında bir değer
   - Negatif: Fiyat düşecek (SHORT)
   - Pozitif: Fiyat yükselecek (LONG)

### 2. **Model Retraining**

**Canlı Retraining:**
```
live_retrain_hours: 2  // Her 2 saatte bir yeniden eğit
```

**Döngü:**
- Bot eski modelle trade ediyor
- Arkaplanda 2 saatte bir yeni veri indir → eğit
- Yeni model hazır olunca otomatik switch
- Eski model dosyaları temizle (purge_old_models: 2)

---

## 📐 Feature Engineering

### **Teknik Göstergeler (Technical Indicators)**

Her indicator için **4 farklı period** hesaplanır: **[10, 20, 40, 100]**

#### 1. **RSI (Relative Strength Index)**
- **Period:** 10, 20, 40, 100
- **Formül:** RSI = 100 - (100 / (1 + RS)) burada RS = Avg Gain / Avg Loss
- **Kullanım:** Overbought (>70) / Oversold (<30) tespiti
- **Kardinalite:** 4 feature

#### 2. **MACD (Moving Average Convergence Divergence)**
- **Periodi:** 
  - Fast EMA: period
  - Slow EMA: period * 2
  - Signal: 9
- **Features:** MACD line, Signal line, Histogram (3 × 4 period = 12 feature)
- **Kullanım:** Trend değişikliği tespiti

#### 3. **Bollinger Bands**
- **Period:** 10, 20, 40, 100
- **Formül:** 
  - Orta band = SMA(period)
  - Üst band = Orta + (StdDev × 2.2)
  - Alt band = Orta - (StdDev × 2.2)
  - BB Width = (Upper - Lower) / Middle
- **Features:** Upper, Middle, Lower, Width (4 × 4 = 16 feature)

#### 4. **MFI (Money Flow Index)**
- **Period:** 10, 20, 40, 100
- **Formül:** MFI = 100 - (100 / (1 + Money Flow Ratio))
- **Kullanım:** Hisse devri şiddeti + fiyat
- **Kardinalite:** 4 feature

#### 5. **ADX (Average Directional Index)**
- **Period:** 10, 20, 40, 100
- **Formül:** 
  - +DI = (+DM / TR) × 100
  - -DI = (-DM / TR) × 100
  - ADX = SMA(|+DI - -DI| / (+DI + -DI|))
- **Kullanım:** Trend gücü (0-100 arası, >25 güçlü trend)
- **Kardinalite:** 4 feature

#### 6. **EMA (Exponential Moving Average)**
- **Period:** 10, 20, 40, 100
- **Formül:** EMA_t = Close_t × α + EMA_(t-1) × (1 - α)
- **Kardinalite:** 4 feature

#### 7. **SMA (Simple Moving Average)**
- **Period:** 10, 20, 40, 100
- **Formül:** SMA = Sum(Close, N) / N
- **Kardinalite:** 4 feature

#### 8. **ATR (Average True Range)**
- **Period:** 10, 20, 40, 100
- **Formül:** 
  - TR = max(High - Low, |High - Close_prev|, |Low - Close_prev|)
  - ATR = SMA(TR)
- **Kullanım:** Volatilite ölçümü
- **Kardinalite:** 4 feature

#### 9. **ROC (Rate of Change)**
- **Period:** 10, 20, 40, 100
- **Formül:** ROC = ((Close - Close_N_period_ago) / Close_N_period_ago) × 100
- **Kullanım:** Momentum
- **Kardinalite:** 4 feature

#### 10. **Williams %R**
- **Period:** 10, 20, 40, 100
- **Formül:** %R = ((Highest High - Close) / (Highest High - Lowest Low)) × -100
- **Kullanım:** Overbought/Oversold
- **Kardinalite:** 4 feature

#### 11. **CCI (Commodity Channel Index)**
- **Period:** 10, 20, 40, 100
- **Formül:** CCI = (Typical Price - SMA(TP)) / (0.015 × Mean Deviation)
- **Kullanım:** Cycle tespiti
- **Kardinalite:** 4 feature

### **Sabit Features (Tek sefer hesaplanan)**

#### 1. **Fiyat Değişim Oranları**
- `%-pct_change`: 1 mum öncekinden % değişim
- `%-pct_change_2`: 2 mum öncekinden % değişim
- `%-pct_change_5`: 5 mum öncekinden % değişim
- **Kardinalite:** 3 feature

#### 2. **Volume Analiz**
- `%-volume_pct_change`: Volume % değişimi
- **Kardinalite:** 1 feature

#### 3. **Price Position**
- `%-hl_range`: (High - Low) / Close ratio
- `%-close_position`: Close'un High-Low içindeki yeri (0-1)
- **Kardinalite:** 2 feature

#### 4. **VWAP (Volume Weighted Average Price)**
- **Formül:** VWAP = Σ(Typical Price × Volume) / Σ(Volume)
- **Period:** 20 mum rolling
- **Kardinalite:** 1 feature

#### 5. **Zamansal Features**
- `%-day_of_week`: 0-6 (Pazartesi-Pazar)
- `%-hour_of_day`: 0-23 (Saatlik)
- **Kardinalite:** 2 feature

### **Toplam Feature Sayısı Hesaplaması**

```
Technical Indicators (4 period × 11 gösterge):  44
Sabit Features:                                  8
Zamansal Features:                               2
──────────────────────────────────────────────
Toplam Features:                                54
```

**Config dosyasındaki ayar:**
```json
"include_shifted_candles": 3,  // Her feature'ın 3 dönem geçmişi
```

Bu demek ki: **54 × 3 = 162 input feature** model için!

### **Target Variable (Tahmin Hedefi)**

```python
def set_freqai_targets(dataframe):
    label_period = 20  # 20 mum (5m × 20 = 100 dakika ≈ 2 saat)
    future_close = dataframe["close"].shift(-20)
    dataframe["&-target"] = ((future_close - close) / close) × 100
```

**Çıkış:** `-3 ile +3` arasında (nadir olarak daha dış değerler)
- `-3`: Fiyat %3 düşecek
- `+3`: Fiyat %3 yükselecek

---

## 🚪 Entry/Exit Stratejileri

### **LONG Girişi (Satın Alma Sinyali)**

```python
enter_long = (
    # 1. ML Model Filtresi
    (do_predict == 1)                    # Model geçerli
    AND (&-target > 0.08)                # Model %0.08+ pozitif tahmin
    AND (DI_values < 4)                  # Model % güven > 80
    
    # 2. Technical Filters
    AND (RSI[5m] < 70)                   # Oversold değil
    AND (RSI[15m] < 65 OR RSI[1h] < 60)  # Multi-timeframe confluence
    
    # 3. Volume Filter
    AND (volume > 0)
)
```

**Uyarlanabilir Threshold:**
```
Base threshold = 0.08

DÜŞÜRÜLECEK (LONG'u teşvik et):
- Fear & Greed < 25 (Extreme Fear)  → threshold - 0.05
- News positive > 70%               → threshold - 0.05
- Funding rate < -0.05% (negatiflı) → threshold - 0.03

YÜKSELTILECEK (LONG'u caydır):
- Hiçbir ayarla etkilenmez
```

### **SHORT Girişi (Satış Sinyali)**

```python
enter_short = (
    # 1. ML Model Filtresi
    (do_predict == 1)                     # Model geçerli
    AND (&-target < -0.08)                # Model %-0.08- negatif tahmin
    AND (DI_values < 4)                   # Model % güven > 80
    
    # 2. Technical Filters
    AND (RSI[5m] > 30)                    # Oversold değil
    AND (RSI[15m] > 35 OR RSI[1h] > 40)   # Multi-timeframe confluence
    
    # 3. Volume Filter
    AND (volume > 0)
)
```

**Uyarlanabilir Threshold:**
```
Base threshold = -0.08

YÜKSELTILECEK (SHORT'u caydır → daha az negatif):
- Extreme Greed (> 75)  → threshold + 0.05
- News negative > 70%   → threshold + 0.05
- Funding rate > 0.05%  → threshold + 0.03
```

### **LONG Çıkışı (Satış Sinyali)**

```python
exit_long = (
    (&-target < -0.15)  # Model güçlü bearish döndü
    OR (RSI[5m] > 80)   # Extreme overbought
)
```

**Kar Alma (Trailing Stops + ROI):**
```json
{
  "trailing_stop": true,
  "trailing_stop_positive": 0.02,        // %2 kâr aldıktan sonra
  "trailing_stop_positive_offset": 0.03, // %3 yastık
  
  "minimal_roi": {
    "0": 0.15,      // İlk 0 dakikada %15 kâr → kapanır
    "120": 0.075,   // 2 saat sonra %7.5'e düşer
    "360": 0.025,   // 6 saat sonra %2.5'e düşer
    "1440": 0       // 24 saat sonra %0 (breakeven)
  },
  
  "stoploss": -0.10   // %10 zarar → force kapanış
}
```

### **SHORT Çıkışı (Satın Alma Sinyali)**

```python
exit_short = (
    (&-target > 0.15)   # Model güçlü bullish döndü
    OR (RSI[5m] < 20)   # Extreme oversold
)
```

---

## 📡 Veri Kaynakları

### 1. **Binance Futures (Primary)**
- **Timeframes:** 5m (ana), 15m, 1h (informative)
- **Veri:** OHLCV (Open, High, Low, Close, Volume)
- **Pair'ler:** BTC/USDT:USDT, ETH/USDT:USDT
- **Data History:** 45 gün eğitim + 10 gün backtest

### 2. **CoinGecko (Sentiment)**
- **Endpoint:** `/coins/{coin_id}`
- **Veriler:**
  - 7 günlük fiyat değişimi (7d sentiment)
  - Yaklaşan etkinlikler (events)
  - Community verisi
- **Rate Limit:** Unlimited (free API)
- **Cache:** 1 saat

### 3. **CryptoPanic (News Sentiment)**
- **Endpoint:** `/posts/?currencies={coin}&filter=hot`
- **Veriler:**
  - Son 24 saat haber'ler
  - Voting (positive/negative)
  - Sentiment tags
- **Rate Limit:** 100 req/ay (developer plan)
- **Cache:** 12 saat

### 4. **Alternative.me (Fear & Greed)**
- **Endpoint:** `/fng/?limit=1`
- **Veriler:**
  - Fear & Greed Index (0-100)
  - Sınıflandırma
- **Rate Limit:** Unlimited
- **Cache:** 2 saat

### 5. **Binance REST API (Funding Rate)**
- **Endpoint:** `/fapi/v1/fundingRate?symbol=BTCUSDT`
- **Veriler:**
  - Mevcut funding rate %
  - Timing bilgisi (8h cycles)
- **Rate Limit:** 1200/min
- **Cache:** 30 dakika

---

## ⚙️ Konfigürasyon

### **config.json - Critical Parameters**

```json
{
  // === TRADING MODE ===
  "trading_mode": "futures",           // Binance Futures
  "margin_mode": "isolated",           // Her trade ayrı teminat
  
  // === STAKE & RISK ===
  "max_open_trades": 2,                // Max 2 eş zamanlı trade
  "max_stake_amount": 150,             // Max 150 USDT per trade
  "stake_currency": "USDT",
  "dry_run": true,                     // Simülasyon modu
  "dry_run_wallet": 1000,              // Başlangıç bakiyesi
  
  // === FREQAI MACHINE LEARNING ===
  "freqai": {
    "train_period_days": 45,           // 45 gün geçmiş veri
    "backtest_period_days": 10,        // 10 gün test seti
    "live_retrain_hours": 2,           // 2 saatte bir yeniden eğit
    "label_period_candles": 20,        // 20 × 5m = 2 saat gelecek
    "include_shifted_candles": 3,      // 3 mum geçmişi
    "DI_threshold": 8,                 // Model güven > 80%
    
    // === LightGBM Hiperparametreler ===
    "model_training_parameters": {
      "n_estimators": 600,             // 600 karar ağacı
      "learning_rate": 0.01,           // Yavaş öğrenme
      "max_depth": 8,                  // Ağaç derinliği
      "num_leaves": 48,                // Yaprak sayısı
      "min_child_samples": 30,         // Min örnek
      "n_jobs": 2                      // 2 CPU paralel
    }
  }
}
```

### **Strateji Parametreleri (FreqaiExampleStrategy.py)**

```python
# === ROI (Return on Investment) ===
minimal_roi = {
  "0": 0.15,      # Anında kapat, %15 kâr
  "120": 0.075,   # 2 saat: %7.5 hedefe düşür
  "360": 0.025,   # 6 saat: %2.5 hedefe düşür
  "1440": 0       # 24 saat: breakeven
}

# === STOPLOSS ===
stoploss = -0.10              # %10 zarar stoploss

# === TRAILING STOP ===
trailing_stop = True
trailing_stop_positive = 0.02        # %2 kâr olunca aktif
trailing_stop_positive_offset = 0.03 # %3 yastık

# === ENTRY THRESHOLD ===
entry_threshold = 0.08  # Model > 0.08 (uyarlanabilir)

# === RISK/REWARD ===
leverage = 2.0x         # 2× kaldıraç (güvenli seviye)
timeframe = "5m"        # 5 dakika candle
```

---

## 📊 Trade Akışı (Step-by-Step)

### **1. DATA FETCHING (5 dakikada bir)**

```
Binance API
    ↓
5m OHLCV verileri
    ↓
Pandas DataFrame olarak yükle
    ↓
45 gün eğitim + 10 gün test verisi
    ↓
Teknik gösterge hesaplanması
```

### **2. FEATURE ENGINEERING**

```
A. Teknik İndikatörler (54 base feature)
   ├─ RSI (4 period)
   ├─ MACD (12 feature)
   ├─ Bollinger Bands (16 feature)
   ├─ MFI, ADX, EMA, SMA, ATR, ROC, Williams %R, CCI (40 feature)
   └─ Price Changes, Volume, VWAP, Zamansal (8 feature)
   
B. Shifted Candles (3 dönem geçmiş)
   → 54 × 3 = 162 input feature
   
C. Sentiment Verileri
   ├─ CoinGecko 7d sentiment
   ├─ CryptoPanic news sentiment
   ├─ Fear & Greed Index
   └─ Binance Funding Rate
   
D. Target Variable
   └─ Gelecek 20 mum fiyat değişimi %
```

### **3. MODEL TRAINING (Her 2 saatte)**

```
Historical Data (45 gün)
    ↓
LightGBM Regressor eğit
├─ Train set: 75% (45 gün × 75% = 33.75 gün)
├─ Test set: 25% (45 gün × 25% = 11.25 gün)
└─ 600 decision tree iter, learning_rate 0.01
    ↓
Model doğrulama (R², MAE, RMSE)
    ↓
Performans OK ise → Üretim modeline geç
Performans BAD ise → Eski modelle devam et
```

### **4. PREDICTION GENERATION (Her 5 dakikada)**

```
Şimdiki candle
    ↓
162 feature hesapla
    ↓
LightGBM modele ver
    ↓
Tahmin: -3 ile +3 arasında değer
    ↓
DI (Dissimilarity Index) hesapla
├─ DI < 4: Modele güvenilir (do_predict=1) ✅
└─ DI ≥ 4: Model şüpheli (do_predict=0) ❌
```

### **5. ENTRY DECISION**

```
do_predict == 1 ?
    ↓
    ├─ YES → Tahmin değerini kontrol et
    │   ├─ &-target > entry_threshold (0.08)
    │   │   └─ RSI[5m] < 70 & Multi-TF confluence
    │   │       └─ LONG ENTER
    │   │
    │   └─ &-target < exit_threshold (-0.08)
    │       └─ RSI[5m] > 30 & Multi-TF confluence
    │           └─ SHORT ENTER
    │
    └─ NO → Skip (model geçersiz)
```

### **6. POSITION MANAGEMENT**

```
Trade açıldı
    ↓
Trailing Stop + ROI takibi
├─ %2 kâr → Trailing başla (%3 yastık)
├─ 2 saat → %7.5 ROI hedefi
├─ 6 saat → %2.5 ROI hedefi
└─ 24 saat → Kaç (breakeven)
    ↓
Stoploss Kontrolü
├─ -%10 zarar → Force kapanış ✅
    ↓
Model Çıkış Sinyali
├─ &-target direction flip
└─ RSI extreme (>80 veya <20)
```

### **7. TELEGRAM NOTIFICATIONS**

```
Trade açıldı
    ↓
Telegram Mesajı:
├─ Pair
├─ Direction (LONG/SHORT)
├─ Entry Price
├─ Stop Loss
├─ Entry Reason
└─ Duration
    ↓
Trade kapatıldı
    ↓
Telegram Mesajı:
├─ Profit %
├─ Exit Reason
├─ Duration
└─ Trade Stats
```

---

## 🔄 Bot Yaşam Döngüsü

```
BOT START
    ↓
1️⃣ Config oku
    ├─ Binance futures ayarları
    ├─ FreqAI parametreleri
    ├─ Strateji parametreleri
    └─ Telegram token'ı
    ↓
2️⃣ Veri İndir
    ├─ 45 gün geçmiş veri (BTC, ETH)
    ├─ 15m ve 1h informative data
    └─ Funding rate, Fear & Greed
    ↓
3️⃣ İlk Model Eğit
    ├─ Feature engineering
    ├─ LightGBM fit
    ├─ Validation
    └─ Model dosyaları save
    ↓
4️⃣ MAIN LOOP (Her 5 dakika)
    ├─ Yeni candle'ı al
    ├─ Prediction yap
    ├─ Entry sinyali kontrol
    ├─ Açık trade'leri yönet
    ├─ Exit sinyali kontrol
    └─ Telegram bildirim gönder
    ↓
5️⃣ BACKGROUND: Her 2 Saatte Model Retrain
    ├─ Yeni veri indir
    ├─ Yeniden eğit
    ├─ Model switch
    └─ Eski model temizle
    ↓
6️⃣ BACKGROUND: Sentiment Cache Update
    ├─ CoinGecko sorgu (1h cache)
    ├─ CryptoPanic sorgu (12h cache)
    ├─ Fear & Greed sorgu (2h cache)
    └─ Funding rate sorgu (30m cache)
    ↓
🔁 LOOP devam et (Bot kapatılana kadar)
```

---

## 📈 Örnek Trade Senaryosu

### **Senaryo: BTC SHORT Trade**

**Zaman:** 2026-02-01 07:10 UTC

**1. Veri Hazırlığı**
```
Binance → 5m BTC/USDT:USDT
Close: 78,213.10
RSI[5m]: 32.5
RSI[15m]: 32.1
RSI[1h]: 28.8
Volume: Yüksek
Sentiment: Negative
Funding: +0.0145% (hafif long bias)
Fear & Greed: 35 (Fear)
```

**2. Feature Calculation**
```
162 feature hesaplanır:
- RSI(10)=32, RSI(20)=35, RSI(40)=38, RSI(100)=42
- MACD components
- BB position ve width
- Price momentum (+0.5%)
- Volume change (+15%)
- ... (150+ daha)
```

**3. Model Prediction**
```
LightGBM Output: &-target = -0.8947
DI_values = 2.03

Sonuç:
- Tahmin: Fiyat %-0.8947 düşecek
- Güven: DI 2.03 < 4 → do_predict = 1 ✅
- Short uyarı: Base threshold (-0.08) < -0.8947
```

**4. Entry Decision**
```
Kontroller:
✅ do_predict == 1
✅ &-target (-0.8947) < -0.08 (threshold)
✅ DI_values (2.03) < 4
✅ RSI[5m] (32.5) > 30 (not oversold)
✅ RSI[15m] (32.1) > 35 (confluence OK)
✅ Volume > 0

SONUÇ: SHORT ENTER ✅
```

**5. Order Placement**
```
Order Type: Limit
Amount: 469.28 USDT
Leverage: 2x
Actual Position: 938.56 USDT
Entry Price: 78,213.10
Stop Loss: 78,213.10 × 1.10 = 86,034.41
```

**6. Telegram Alert**
```
✳️ Binance (dry): Entering BTC/USDT:USDT (#1)
Direction: Short (2x)
Amount: 0.012
Stake amount: 469 USDT
Open Rate: 78213.1 USDT
Current Rate: 78213.1 USDT
```

**7. Trade Management**
```
5m sonra:
→ Fiyat 77,800'e düştü (-413 USDT fark)
→ Unrealized Profit: +0.86%
→ Trailing Stop aktif değil (henüz %2 kâr yok)

445 dakika (7h25m) sonra:
→ Model `exit_signal` döndü
→ &-target pozitif hale geldi
→ Trade KAPANDI

SONUÇ:
Profit: +1.62% (+7.583 USDT)
Duration: 7:25:01
Exit Reason: exit_signal
```

---

## 🎯 Özet

### **Teknoloji Stack:**
- **Framework:** Freqtrade + FreqAI
- **ML Model:** LightGBM (600 trees, learning_rate 0.01)
- **Features:** 162 input (teknik + sentiment + zamansal)
- **Target:** 20 mum gelecek fiyat değişimi %
- **Sentiment:** CoinGecko + CryptoPanic + Fear & Greed + Funding Rate

### **Trading Logic:**
- **Entry:** ML prediction > threshold + RSI confluence + Volume
- **Exit:** Model flip + ROI targets + Trailing stop
- **Risk:** 2x leverage, -10% stoploss, max 2 concurrent trades

### **Deployment:**
- **VPS:** Hetzner CPX22
- **Containerization:** Docker
- **Interface:** FreqUI
- **Monitoring:** Telegram

### **Performance (Initial):**
- 3 trade'den 2'si kârlı
- +12.74 USDT net profit (1.27%)
- 1 trade zararda (-18.14 USDT)

---

**Bot aktif olarak çalışıyor ve 7/24 piyasa fırsatlarını yakalıyor! 🚀**
