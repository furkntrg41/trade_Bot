#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════════════
🎓 MASTER FEATURE VECTOR - 4 REFERANS KİTABTAN ENTEGRE AYARLARI
════════════════════════════════════════════════════════════════════════════════

Bu dosya, FreqaiExampleStrategy.py içine entegre edilen 4 ana referans kitaptan
çıkarılan ve modelin input layer'ına beslenecek kritik özellikleri dokumentedir.
"""

master_features = {
    
    # ════════════════════════════════════════════════════════════════════════
    # 1️⃣ HARRIS: TRADING AND EXCHANGES (Market Microstructure)
    # ════════════════════════════════════════════════════════════════════════
    
    "harris_microstructure": {
        "book": "Trading and Exchanges - Market Microstructure for Practitioners",
        "author": "Larry Harris",
        "pages": "113 (Practitioners Draft)",
        
        "features": {
            
            "bid_ask_spread": {
                "formula": "(High - Low) / Close, 14-period MA",
                "concept": "Likidite göstergesi. Spread açılırsa = Belirsizlik artar",
                "usage": "Feature'i modele ek olarak ver. Spread > 5% = High risk signal",
                "book_ref": "Chapter 5: Spread vs Liquidity",
                "python": "dataframe['bid_ask_spread'] = (df['high'] - df['low']) / df['close']"
            },
            
            "order_book_imbalance": {
                "formula": "Buy Volume / (Sell Volume + 1) - 14 period",
                "concept": "Emir defterinde hangi taraf daha ağırsa, fiyat o yöne gider",
                "proxy": "Hacim yönü (Uptick vs Downtick volume)",
                "usage": "Imbalance > 1.0 = LONG signal. < 1.0 = SHORT signal",
                "book_ref": "Chapter 4: Orders and Order Properties",
                "python": """
                volume_up = volume where close > open
                volume_down = volume where close <= open
                order_imbalance = volume_up / (volume_down + 1)
                """
            },
            
            "vwap_deviation": {
                "formula": "(Close - VWAP) / VWAP, 20-period VWAP",
                "concept": "Fiyat Mean Reversion göstergesi. VWAP'ten sapma = Geri dönüş olasılığı",
                "typical_price": "(High + Low + Close) / 3",
                "usage": "VWAP_Dev > +0.1% = LONG. VWAP_Dev < -0.1% = SHORT",
                "book_ref": "Chapter 7: Finding Trading Opportunities",
                "python": """
                typical = (high + low + close) / 3
                vwap = (typical * volume).rolling(20).sum() / volume.rolling(20).sum()
                deviation = (close - vwap) / vwap
                """
            },
            
            "transaction_costs": {
                "concept": "Backtest'te gerçekçi maliyetler kullan",
                "note": "Freqtrade config.json'da: trading.fee = 0.0005 (0.05% komisyon)",
                "reference": "Harris: Implementation Shortfall Formula",
                "formula_note": "Slippage = Average Half-Spread × (Order Size / Market Volume)"
            }
        },
        
        "entry_logic": {
            "long_condition": [
                "order_imbalance > 1.0  # Buy pressure",
                "vwap_deviation > +0.001  # Price above fair value (uptrend)",
                "bid_ask_spread < 0.05  # Good liquidity"
            ],
            "short_condition": [
                "order_imbalance < 1.0  # Sell pressure",
                "vwap_deviation < -0.001  # Price below fair value (downtrend)",
                "bid_ask_spread < 0.05  # Good liquidity"
            ]
        }
    },
    
    # ════════════════════════════════════════════════════════════════════════
    # 2️⃣ TSAY: ANALYSIS OF FINANCIAL TIME SERIES (Statistical Validity)
    # ════════════════════════════════════════════════════════════════════════
    
    "tsay_timeseries": {
        "book": "Analysis of Financial Time Series",
        "author": "Ruey S. Tsay",
        "pages": "638",
        
        "critical_concept": "Unit Root Problem - Modele asla ham fiyat verme!",
        "why": "Finansal seriler Unit Root içerir = Ortalaması/Varyansı zaman değişir = Non-stationary",
        
        "features": {
            
            "log_returns": {
                "formula": "log(P_t / P_t-1)",
                "why": "Unit Root'u kaldır. Serinin stationary olmasını sağla",
                "benefit": "AR/ARMA modelleri bu veriye uygulanabilir",
                "book_ref": "Chapter 1: Asset Returns",
                "python": "log_returns = np.log(df['close'] / df['close'].shift(1))",
                "importance": "⚠️ ZORUNLU - Ham fiyat kullanmayın!"
            },
            
            "garch_volatility": {
                "concept": "Kondisyonel Varyans. Büyük hareket → Büyük hareket izler",
                "formula": "GARCH(1,1) - Conditional Variance σ_t^2",
                "approximation": "Square of returns, exponentially weighted MA",
                "usage": "Model volatiliteyi 'risk' olarak öğrenir. Yüksek vol = tight stop",
                "book_ref": "Chapter 3: Volatility Modeling",
                "python": """
                returns_squared = (df['close'].pct_change()) ** 2
                garch_vol = returns_squared.rolling(14).mean() ** 0.5
                """
            },
            
            "volatility_zscore": {
                "formula": "(Current_Vol - MA) / STD, 20-period",
                "usage": "Normal vol (z < 1): Steady trend. High vol (z > 2): Consolidation risk",
                "entry_filter": "volatility_zscore < 2.0  # Avoid trading in chaos",
                "python": """
                vol_mean = garch_vol.rolling(20).mean()
                vol_std = garch_vol.rolling(20).std()
                vol_zscore = (garch_vol - vol_mean) / vol_std
                """
            },
            
            "ljung_box_autocorr": {
                "concept": "White Noise Testi - Veri tahmin edilebilir mi?",
                "formula": "Autocorrelation(returns, lag=1-20)",
                "interpretation": "ACF = 0 → White Noise (tahmin imkânsız)",
                "usage": "returns_autocorr > -0.2 → Veri tahmin edilebilir",
                "book_ref": "Chapter 2: Correlation and Dependence",
                "python": "returns.rolling(20).apply(lambda x: x.autocorr())"
            }
        },
        
        "preprocessing_rules": [
            "✅ Modele ham fiyat değil, LOG RETURNS ver",
            "✅ GARCH volatility ile risk regimes'i model öğrensin",
            "✅ Ljung-Box testi > -0.2 olan periyotlarda trade et",
            "❌ Unit Root içeren non-stationary veriyi direkt modele sokma"
        ]
    },
    
    # ════════════════════════════════════════════════════════════════════════
    # 3️⃣ JANSEN: MACHINE LEARNING FOR ALGORITHMIC TRADING (Normalized Factors)
    # ════════════════════════════════════════════════════════════════════════
    
    "jansen_ml": {
        "book": "Machine Learning for Algorithmic Trading (2nd Edition)",
        "author": "Stefan Jansen",
        "pages": "858",
        
        "central_principle": "Tüm features normalize et (Z-Score). Karşılaştırılabilir hale getir.",
        
        "features": {
            
            "rsi_zscore": {
                "formula": "(RSI - 20-MA(RSI)) / STD(RSI)",
                "benefit": "0-100 skalası yerine standardize skor. Model daha tutarlı öğrenir",
                "interpretation": "Z > 1: Overbought. Z < -1: Oversold. -1 < Z < 1: Neutral",
                "book_ref": "Chapter 5: Feature Engineering and Selection",
                "python": """
                rsi = RSI(df, 14)
                rsi_ma = rsi.rolling(20).mean()
                rsi_std = rsi.rolling(20).std()
                rsi_zscore = (rsi - rsi_ma) / rsi_std
                """
            },
            
            "momentum_zscore": {
                "formula": "(Momentum - MA) / STD, 10-period momentum",
                "concept": "Rate of change, normalized.",
                "usage": "momentum_zscore > 0 = Trend başladı. < 0 = Trend bitişi",
                "python": """
                momentum = close - close.shift(10)
                mom_zscore = (momentum - mom.rolling(20).mean()) / mom.rolling(20).std()
                """
            },
            
            "alpha_factor_combination": {
                "concept": "Tek indikatör yetmez. Faktörleri kombine et",
                "approach": "Alphalens: Information Coefficient (IC) ile etkinliğini test et",
                "factors_to_use": [
                    "Z-Score RSI (momentum)",
                    "GARCH Volatility (risk)",
                    "VWAP Deviation (mean reversion)",
                    "Order Imbalance (direction)"
                ],
                "book_ref": "Chapter 12: Evaluating Asset Pricing Factors",
                "note": "Freqtrade config.json'da LightGBM otomatik kombinasyon öğreniyor"
            },
            
            "model_selection": {
                "preference": "Tree-based > Deep Learning for Crypto",
                "why": "Financial data = very high noise. Tree models (XGBoost/LightGBM) better",
                "reasoning": "Signal-to-noise ratio too low for neural networks",
                "book_ref": "Chapter 7: Deep Learning vs Tree Models",
                "your_setup": "✅ LightGBMRegressor (config.json: freqaimodel)"
            },
            
            "cross_validation": {
                "problem": "Standard K-Fold = Look-ahead bias (future leaks to past)",
                "solution": "Purged K-Fold with Embargo",
                "concept": "Train/Test arası boşluk bırak. Oto-korelasyonu kes.",
                "book_ref": "Chapter 8: Backtesting and Walk-Forward Analysis",
                "note": "Freqtrade'de automated - Config.json: walk-forward setup"
            }
        },
        
        "entry_filters": [
            "rsi_zscore < 1.5  # Not overbought",
            "momentum_zscore > -0.5  # Positive momentum",
            "rsi_zscore_15m < 1.0  # MTF confirmation",
            "rsi_zscore_1h < 0.5  # Longer TF alignment"
        ]
    },
    
    # ════════════════════════════════════════════════════════════════════════
    # 4️⃣ PRICE ACTION TRADING (Behavioral Patterns)
    # ════════════════════════════════════════════════════════════════════════
    
    "price_action": {
        "book": "Price Action Trading",
        "concept": "Göz kararı değil, matematiksel destek/direnç tanımı",
        
        "features": {
            
            "support_resistance": {
                "definition": "Local Minima/Maxima (20-period lookback)",
                "why": "Görsel "çizgi" yerine objektif algoritma",
                "support": "Fiyatın rebond ettiği en düşük nokta",
                "resistance": "Fiyatın düştüğü en yüksek nokta",
                "usage": "Giriş, stop loss, TP belirleme",
                "python": """
                support = low.rolling(window=20, center=True).min()
                resistance = high.rolling(window=20, center=True).max()
                distance_to_support = (close - support) / close  # %
                distance_to_resistance = (resistance - close) / close  # %
                """
            },
            
            "breakout_detection": {
                "definition": "Price > 20-period high + Volume > Average × 2",
                "why": "Volume confirmation = Legitimate breakout. Fake breakout filtered",
                "formula": """
                breakout = (high > high.shift(1).rolling(20).max()) &
                           (volume > volume.rolling(20).mean() * 2)
                """,
                "book_ref": "Chapter 6: Breakouts - Pro tip: Volume Confirmation",
                "signal": "+1 = Upside breakout. -1 = Downside breakout"
            },
            
            "candlestick_patterns": {
                
                "pinbar": {
                    "definition": "Long wick / Small body > 3",
                    "formula": "(Upper_Wick + Lower_Wick) / Body > 3",
                    "meaning": "Market rejection. Tutulmayacak seviye",
                    "signal": "is_pinbar = 1 → Avoid entry (false reversal risk)",
                    "python": """
                    upper_wick = high - max(open, close)
                    lower_wick = min(open, close) - low
                    body = abs(close - open)
                    pinbar_ratio = (upper_wick + lower_wick) / (body + eps)
                    is_pinbar = pinbar_ratio > 3
                    """
                },
                
                "engulfing": {
                    "definition": "Current candle body > Previous candle body",
                    "direction": "Bullish = Green engulfs red. Bearish = Red engulfs green",
                    "meaning": "Sentiment shift. Strong reversal",
                    "usage": "Entry confirmation filter",
                    "python": """
                    current_body = abs(close - open)
                    prev_body = abs(close.shift(1) - open.shift(1))
                    engulfing = current_body > prev_body
                    """
                }
            },
            
            "entry_rules": {
                "long": [
                    "distance_to_support: 1% - 15%  (not too far, not too close)",
                    "breakout_signal: >= 0  (not breaking down)",
                    "is_pinbar: 0 OR upper_wick < lower_wick  (no strong rejection)",
                    "close < bb_middleband  (room to grow)",
                    "volume > 0  (liquidity)"
                ],
                "short": [
                    "distance_to_resistance: 1% - 15%",
                    "breakout_signal: <= 0",
                    "is_pinbar: 0 OR lower_wick < upper_wick",
                    "close > bb_middleband  (room to fall)",
                    "volume > 0"
                ]
            }
        }
    }
}

# ════════════════════════════════════════════════════════════════════════════
# 📊 MASTER FEATURE VECTOR ÖZET
# ════════════════════════════════════════════════════════════════════════════

feature_summary = {
    "microstructure": [
        "bid_ask_spread",
        "order_imbalance",
        "vwap_deviation"
    ],
    
    "time_series": [
        "log_returns",
        "garch_volatility",
        "volatility_zscore",
        "returns_autocorr"
    ],
    
    "normalized_factors": [
        "rsi_zscore",
        "rsi_zscore_15m",
        "rsi_zscore_1h",
        "momentum_zscore",
        "macd_diff",
        "bb_width_zscore"
    ],
    
    "price_action": [
        "distance_to_support",
        "distance_to_resistance",
        "breakout_signal",
        "pinbar_ratio",
        "is_pinbar",
        "engulfing"
    ]
}

total_features = sum(len(v) for v in feature_summary.values())

print(f"""
════════════════════════════════════════════════════════════════════════════════
✅ MASTER FEATURE VECTOR ENTEGRE TAMAMLANDI
════════════════════════════════════════════════════════════════════════════════

📚 Referans Kitaplar:
  1. ✅ Trading and Exchanges (Harris) - Market Microstructure
  2. ✅ Time Series Analysis (Tsay) - Statistical Validity  
  3. ✅ ML for Algorithmic Trading (Jansen) - Normalized Factors
  4. ✅ Price Action Trading - Behavioral Patterns

📊 Toplam Features: {total_features}
  • Market Microstructure: {len(feature_summary['microstructure'])}
  • Time Series: {len(feature_summary['time_series'])}
  • Normalized Factors: {len(feature_summary['normalized_factors'])}
  • Price Action: {len(feature_summary['price_action'])}

🎯 Strateji Dosyası: user_data/strategies/FreqaiExampleStrategy.py
  ├─ populate_indicators() → Master Features hesapla
  ├─ populate_entry_trend() → Kompleks logic with all 4 books
  ├─ custom_stoploss() → Risk-adjusted stops
  └─ Telemetry → Performance tracking

⚠️ KRİTİK:
  • TSAY: Log returns kullan, ham fiyat değil!
  • HARRIS: Transaction costs realistic (config.json: fee)
  • JANSEN: Z-Score normalize et, karşılaştırılabilir hale getir
  • PRICE ACTION: Matematiksel tanımlar, göz kararı değil

🚀 Sonraki Adımlar:
  1. Dry-run 1-2 hafta test et
  2. Hyperopt ile entry_threshold optimize et
  3. Logs'ta feature values'i kontrol et
  4. Paper → Live Trading
════════════════════════════════════════════════════════════════════════════════
""")
