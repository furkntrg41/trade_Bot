"""
FreqAI + LightGBM Futures Strategy - SOLID Architecture
========================================================
Refactored following SOLID principles:
- SRP: Each service has single responsibility
- OCP: Open for extension (new providers via interfaces)
- LSP: Services interchangeable via interfaces
- ISP: Segregated interfaces (ISentimentProvider, IMarketDataProvider, etc.)
- DIP: Depends on abstractions, not concretions (constructor injection)

Architecture:
    /core          -> Domain interfaces
    /infrastructure -> API clients (CoinGecko, Binance, CryptoPanic)
    /application    -> Business logic services (Cointegration, Sentiment)
    FreqaiExampleStrategy -> Orchestration layer (thin controller)
"""
import logging
import time
from typing import Optional
from datetime import datetime

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter, IStrategy, merge_informative_pair
from freqtrade.persistence import Trade

# Logger first (for import-time usage)
logger = logging.getLogger(__name__)

# Dependency injection container (IoC)
# Use absolute imports for FreqTrade compatibility
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# REFACTORED: Dynamic config-driven container (OCP compliance)
from application.dynamic_service_container import DynamicServiceContainer

# Statsmodels availability check
try:
    from statsmodels.tsa.stattools import coint
    from statsmodels.api import OLS, add_constant
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels not available - cointegration features disabled")


class FreqaiExampleStrategy(IStrategy):
    """
    FreqAI LightGBM Strategy - SOLID Architecture
    
    This strategy is now a thin orchestration layer (Controller pattern).
    All business logic delegated to services via dependency injection.
    
    Services (injected via IoC container):
    - CointegrationService: Statistical arbitrage logic
    - SentimentAggregatorService: Multi-source sentiment analysis
    - MarketDataProvider: Binance funding rate, Fear & Greed
    - CacheService: In-memory caching
    
    SOLID compliance:
    - SRP: Strategy only orchestrates, doesn't implement business logic
    - OCP: New features added via new services, not modifying existing code
    - DIP: Depends on interfaces (ICointegrationAnalyzer, etc.), not implementations
    """
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        
        # REFACTORED: Dynamic config-driven container (OCP compliance)
        # Add/remove providers in YAML - NO code modification
        self._container = DynamicServiceContainer()
        
        # Injected services (DIP: depend on abstractions)
        self._cointegration_service = self._container.cointegration_service
        self._sentiment_aggregator = self._container.sentiment_aggregator
        self._market_data_provider = self._container.market_data_provider
        self._cache_service = self._container.cache_service
        
        logger.info(f"✅ Strategy initialized with providers: {self._container.get_provider_stats()}")
    
    # ROI: Fibonacci-based, momentum decay
    # Based on: Price Action candle expansion patterns
    minimal_roi = {
        "0": 0.08,      # Initial expansion target
        "36": 0.055,    # 3-hour consolidation
        "120": 0.04,    # Momentum loss threshold
        "300": 0.025    # Long-term hold (5 hours)
    }
    
    # Stoploss: ATR-based (Ref: ML Trading Risk Mgmt)
    # Tighter than before: %5.5 max loss per trade
    # With 2x leverage = ~%11 effective drawdown
    stoploss = -0.055
    
    # Trailing stoploss: Break-even + trailing logic
    # Ref: Price Action - "Hide stop behind support"
    # Ref: Market Microstructure - Limit order clustering
    trailing_stop = True
    trailing_stop_positive = 0.018  # Start trailing at +1.8% (ATR * 0.5)
    trailing_stop_positive_offset = 0.065  # Target +6.5% (ATR * 1.8)
    trailing_only_offset_is_reached = True
    
    # Timeframe
    timeframe = "5m"
    
    # Informative pairs - Multi-timeframe analiz için
    def informative_pairs(self):
        """15m ve 1h RSI için informative pairs tanımla"""
        # dp hazır değilse boş dön
        if not self.dp:
            return []
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        for pair in pairs:
            informative_pairs.append((pair, "15m"))
            informative_pairs.append((pair, "1h"))
        return informative_pairs
    
    # Futures ayarları
    can_short = True  # Short pozisyon açabilir
    
    def leverage(self, pair: str, current_time, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag,
                 side: str, **kwargs) -> float:
        """
        Dinamik leverage. Dry-run'da düşük tut, risk kontrolü için.
        Gerçek trade'de bile max 3x önerilir.
        """
        # Dry-run'da güvenli leverage
        return 2.0
    
    # FreqAI zorunlu ayarlar
    process_only_new_candles = True
    use_exit_signal = True
    
    # FreqAI prediction threshold - OPTIMIZED RANGES
    # Ref: ML Trading - Feature importance threshold optimization
    # Wider range for market microstructure sensitivity
    entry_threshold = DecimalParameter(0.02, 1.5, default=0.06, space="buy", optimize=True)
    exit_threshold = DecimalParameter(-1.5, -0.02, default=-0.06, space="sell", optimize=True)
    
    # Hyperopt parameters
    buy_rsi = IntParameter(20, 40, default=30, space="buy", optimize=True)
    sell_rsi = IntParameter(60, 80, default=70, space="sell", optimize=True)

    def _get_sentiment_data(self, pair: str) -> dict:
        """
        Orchestrates sentiment data retrieval (Delegation to services)
        SRP: Strategy only coordinates, services do the work
        """
        # Determine coin identifier
        if "BTC" in pair:
            symbol = "BTC"
            coin_id = "bitcoin"
            funding_symbol = "BTCUSDT"
        elif "ETH" in pair:
            symbol = "ETH"
            coin_id = "ethereum"
            funding_symbol = "ETHUSDT"
        else:
            return {
                'sentiment': {'positive': 0, 'negative': 0, 'neutral': 100},
                'fear_greed': {'value': 50, 'classification': 'Neutral'},
                'funding_rate': 0.0
            }
        
        # Cache check (30-min cache for API calls)
        import time
        cache_key = f"sentiment_data_{symbol}_{int(time.time() / 1800)}"
        cached = self._cache_service.get(cache_key)
        if cached:
            return cached
        
        # Delegate to services (DIP: depend on interfaces, not implementations)
        sentiment = self._sentiment_aggregator.get_aggregated_sentiment(symbol, coin_id)
        fear_greed = self._market_data_provider.get_fear_greed_index()
        funding_rate = self._market_data_provider.get_funding_rate(funding_symbol)
        
        result = {
            'sentiment': sentiment,
            'fear_greed': fear_greed,
            'funding_rate': funding_rate
        }
        
        # Cache result
        self._cache_service.set(cache_key, result)
        
        return result

    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        FreqAI için feature üretimi.
        Bu fonksiyon config'deki indicator_periods_candles değerleri için çağrılır.
        period: [10, 20, 50] -> her biri için ayrı ayrı çalışır
        """
        # RSI
        dataframe[f"%-rsi-period_{period}"] = ta.RSI(dataframe, timeperiod=period)
        
        # MFI - Money Flow Index
        dataframe[f"%-mfi-period_{period}"] = ta.MFI(dataframe, timeperiod=period)
        
        # ADX - Trend gücü
        dataframe[f"%-adx-period_{period}"] = ta.ADX(dataframe, timeperiod=period)
        
        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=period, stds=2.2
        )
        dataframe[f"%-bb_lowerband-period_{period}"] = bollinger["lower"]
        dataframe[f"%-bb_middleband-period_{period}"] = bollinger["mid"]
        dataframe[f"%-bb_upperband-period_{period}"] = bollinger["upper"]
        dataframe[f"%-bb_width-period_{period}"] = (
            (bollinger["upper"] - bollinger["lower"]) / bollinger["mid"]
        )
        
        # MACD
        macd = ta.MACD(dataframe, fastperiod=period, slowperiod=period*2, signalperiod=9)
        dataframe[f"%-macd-period_{period}"] = macd["macd"]
        dataframe[f"%-macdsignal-period_{period}"] = macd["macdsignal"]
        dataframe[f"%-macdhist-period_{period}"] = macd["macdhist"]
        
        # EMA
        dataframe[f"%-ema-period_{period}"] = ta.EMA(dataframe, timeperiod=period)
        
        # SMA
        dataframe[f"%-sma-period_{period}"] = ta.SMA(dataframe, timeperiod=period)
        
        # ATR - Volatilite
        dataframe[f"%-atr-period_{period}"] = ta.ATR(dataframe, timeperiod=period)
        
        # ROC - Rate of Change
        dataframe[f"%-roc-period_{period}"] = ta.ROC(dataframe, timeperiod=period)
        
        # Williams %R
        dataframe[f"%-willr-period_{period}"] = ta.WILLR(dataframe, timeperiod=period)
        
        # CCI
        dataframe[f"%-cci-period_{period}"] = ta.CCI(dataframe, timeperiod=period)

        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Sabit period gerektirmeyen feature'lar.
        Fiyat değişimleri, pattern'ler vs.
        """
        # Fiyat değişim oranları
        dataframe["%-pct_change"] = dataframe["close"].pct_change()
        dataframe["%-pct_change_2"] = dataframe["close"].pct_change(periods=2)
        dataframe["%-pct_change_5"] = dataframe["close"].pct_change(periods=5)
        
        # Volume değişimi
        dataframe["%-volume_pct_change"] = dataframe["volume"].pct_change()
        
        # High-Low range
        dataframe["%-hl_range"] = (dataframe["high"] - dataframe["low"]) / dataframe["close"]
        
        # Close pozisyonu (High-Low içinde nerede?)
        hl_range = dataframe["high"] - dataframe["low"]
        dataframe["%-close_position"] = np.where(
            hl_range > 0,
            (dataframe["close"] - dataframe["low"]) / hl_range,
            0.5  # Eşit high-low durumunda orta nokta
        )
        
        # VWAP - Rolling window (20 period) ile hesapla
        typical_price = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3
        vol_sum = dataframe["volume"].rolling(window=20).sum()
        dataframe["%-vwap"] = (
            (typical_price * dataframe["volume"]).rolling(window=20).sum() / 
            vol_sum.replace(0, np.nan)  # Division by zero koruması
        ).fillna(typical_price)  # NaN'ları typical_price ile doldur

        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        FreqAI'ın beklediği standart feature'lar.
        %- prefix'i FreqAI'ın bunları feature olarak algılaması için zorunlu.
        """
        # Day of week (0-6)
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        
        # Hour of day (0-23)
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour

        return dataframe

    def set_freqai_targets(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        ML modelinin tahmin edeceği hedef değişken.
        &- prefix'i zorunlu.
        
        Burada: Gelecek N mum sonraki fiyat değişimi (%)
        label_period_candles config'den gelir (24 mum = 2 saat @ 5m)
        """
        # Gelecekteki fiyat değişimi hesapla (pandas 2.1+ uyumlu)
        label_period = self.freqai_info["feature_parameters"]["label_period_candles"]
        future_close = dataframe["close"].shift(-label_period)
        dataframe["&-target"] = ((future_close - dataframe["close"]) / dataframe["close"]) * 100

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        MASTER FEATURE VECTOR - 4 Reference Books Integration
        
        Ref 1: Trading Exchanges (Harris) - Market Microstructure
                 ├─ Bid-Ask Spread
                 ├─ Order Book Imbalance
                 └─ VWAP Deviation
        
        Ref 2: Time Series Analysis (Tsay) - Statistical Validity
                 ├─ Log Returns (not raw prices)
                 ├─ GARCH Volatility
                 └─ Autocorrelation
        
        Ref 3: ML for Algorithmic Trading (Jansen) - Normalized Factors
                 ├─ Z-Score Normalized RSI
                 ├─ Normalized Momentum
                 └─ Alpha Factor Combination
        
        Ref 4: Price Action Trading - Behavioral Patterns
                 ├─ Support/Resistance Distance
                 ├─ Breakout Detection
                 └─ Candlestick Pattern Ratios
        """
        
        # FreqAI prediction
        dataframe = self.freqai.start(dataframe, metadata, self)
        
        # =============================================
        # 1. HARRIS: MARKET MICROSTRUCTURE FEATURES
        # =============================================
        
        # Bid-Ask Spread proxy (using High-Low range)
        # Ref: Harris - "Spread reflects liquidity"
        dataframe['bid_ask_spread'] = (dataframe['high'] - dataframe['low']) / dataframe['close']
        dataframe['bid_ask_spread'] = dataframe['bid_ask_spread'].rolling(14).mean()
        
        # Order Book Imbalance proxy (Volume direction)
        # Ref: Harris - "Bid vs Ask volume determines direction"
        dataframe['volume_up'] = dataframe['volume'].where(dataframe['close'] > dataframe['open'], 0)
        dataframe['volume_down'] = dataframe['volume'].where(dataframe['close'] <= dataframe['open'], 0)
        
        # Imbalance ratio: Bid volume / Ask volume
        dataframe['order_imbalance'] = (dataframe['volume_up'].rolling(14).sum() / 
                                       (dataframe['volume_down'].rolling(14).sum() + 1))
        
        # VWAP (Volume Weighted Average Price)
        # Ref: Harris - "Fiyat VWAP'ten sapma = Mean Reversion"
        typical_price = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        dataframe['vwap'] = (typical_price * dataframe['volume']).rolling(20).sum() / dataframe['volume'].rolling(20).sum()
        dataframe['vwap_deviation'] = (dataframe['close'] - dataframe['vwap']) / dataframe['vwap']
        
        # =============================================
        # 2. TSAY: TIME SERIES FEATURES
        # =============================================
        
        # Log Returns (not raw prices)
        # Ref: Tsay - "Unit Root problem: always use log returns"
        dataframe['log_returns'] = np.log(dataframe['close'] / dataframe['close'].shift(1))
        
        # Simple Returns for GARCH
        dataframe['returns'] = dataframe['close'].pct_change()
        
        # GARCH(1,1) Volatility approximation
        # Ref: Tsay - "Conditional variance shows regime changes"
        # Simple exponential variance (approximation of GARCH)
        returns_sq = dataframe['returns'] ** 2
        dataframe['garch_volatility'] = returns_sq.rolling(14).mean() ** 0.5
        
        # Normalized volatility (z-score within window)
        vol_mean = dataframe['garch_volatility'].rolling(20).mean()
        vol_std = dataframe['garch_volatility'].rolling(20).std()
        dataframe['volatility_zscore'] = (dataframe['garch_volatility'] - vol_mean) / (vol_std + 1e-6)
        
        # Autocorrelation indicator (Ljung-Box equivalent)
        # Ref: Tsay - "Check for white noise before modeling"
        dataframe['returns_autocorr'] = dataframe['returns'].rolling(20).apply(
            lambda x: x.autocorr() if len(x) > 1 else 0, raw=False
        )
        
        # =============================================
        # 3. JANSEN: NORMALIZED ALPHA FACTORS
        # =============================================
        
        # RSI 5m (entry timeframe)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        
        # Z-Score normalized RSI
        # Ref: Jansen - "Normalize all features for consistency"
        rsi_mean = dataframe['rsi'].rolling(20).mean()
        rsi_std = dataframe['rsi'].rolling(20).std()
        dataframe['rsi_zscore'] = (dataframe['rsi'] - rsi_mean) / (rsi_std + 1e-6)
        
        # MACD as Alpha Factor
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        dataframe['macd_diff'] = dataframe['macd'] - dataframe['macd_signal']
        
        # Normalized Momentum
        dataframe['momentum'] = dataframe['close'] - dataframe['close'].shift(10)
        momentum_mean = dataframe['momentum'].rolling(20).mean()
        momentum_std = dataframe['momentum'].rolling(20).std()
        dataframe['momentum_zscore'] = (dataframe['momentum'] - momentum_mean) / (momentum_std + 1e-6)
        
        # Multi-timeframe RSI
        pair = metadata.get("pair", "")
        
        if self.dp:
            # 15m RSI
            inf_15m = self.dp.get_pair_dataframe(pair=pair, timeframe="15m")
            if not inf_15m.empty and len(inf_15m) > 14:
                inf_15m["rsi"] = ta.RSI(inf_15m, timeperiod=14)
                # Normalize 15m RSI
                rsi_15m_mean = inf_15m['rsi'].rolling(20).mean()
                rsi_15m_std = inf_15m['rsi'].rolling(20).std()
                inf_15m['rsi_zscore'] = (inf_15m['rsi'] - rsi_15m_mean) / (rsi_15m_std + 1e-6)
                
                dataframe = merge_informative_pair(
                    dataframe, inf_15m[["date", "rsi", "rsi_zscore"]], 
                    self.timeframe, "15m", ffill=True
                )
                if "rsi_15m" not in dataframe.columns:
                    dataframe["rsi_15m"] = dataframe.get("rsi", 50)
                if "rsi_zscore_15m" not in dataframe.columns:
                    dataframe["rsi_zscore_15m"] = dataframe.get("rsi_zscore", 0)
            else:
                dataframe["rsi_15m"] = 50
                dataframe["rsi_zscore_15m"] = 0
            
            # 1h RSI
            inf_1h = self.dp.get_pair_dataframe(pair=pair, timeframe="1h")
            if not inf_1h.empty and len(inf_1h) > 14:
                inf_1h["rsi"] = ta.RSI(inf_1h, timeperiod=14)
                rsi_1h_mean = inf_1h['rsi'].rolling(20).mean()
                rsi_1h_std = inf_1h['rsi'].rolling(20).std()
                inf_1h['rsi_zscore'] = (inf_1h['rsi'] - rsi_1h_mean) / (rsi_1h_std + 1e-6)
                
                dataframe = merge_informative_pair(
                    dataframe, inf_1h[["date", "rsi", "rsi_zscore"]], 
                    self.timeframe, "1h", ffill=True
                )
                if "rsi_1h" not in dataframe.columns:
                    dataframe["rsi_1h"] = dataframe.get("rsi", 50)
                if "rsi_zscore_1h" not in dataframe.columns:
                    dataframe["rsi_zscore_1h"] = dataframe.get("rsi_zscore", 0)
            else:
                dataframe["rsi_1h"] = 50
                dataframe["rsi_zscore_1h"] = 0
        else:
            dataframe["rsi_15m"] = 50
            dataframe["rsi_zscore_15m"] = 0
            dataframe["rsi_1h"] = 50
            dataframe["rsi_zscore_1h"] = 0
        
        # Bollinger Bands
        bb = qtpylib.bollinger_bands(dataframe['close'], window=20, stds=2)
        dataframe['bb_lowerband'] = bb['lower']
        dataframe['bb_upperband'] = bb['upper']
        dataframe['bb_middleband'] = bb['mid']
        dataframe['bb_width_zscore'] = ((dataframe['bb_upperband'] - dataframe['bb_lowerband']) / 
                                        dataframe['bb_middleband']).rolling(14).apply(
                                            lambda x: (x.iloc[-1] - x.mean()) / (x.std() + 1e-6) if len(x) > 1 else 0
                                        )
        
        # =============================================
        # 4. PRICE ACTION: BEHAVIORAL PATTERNS
        # =============================================
        
        # Support/Resistance - Local Minima/Maxima
        # Ref: Price Action - "Göz kararı değil, matematiksel tanım"
        dataframe['local_min'] = dataframe['low'].rolling(window=20, center=True).min()
        dataframe['local_max'] = dataframe['high'].rolling(window=20, center=True).max()
        
        # Distance to Support (% away)
        dataframe['distance_to_support'] = ((dataframe['close'] - dataframe['local_min']) / 
                                           dataframe['close'])
        
        # Distance to Resistance (% away)
        dataframe['distance_to_resistance'] = ((dataframe['local_max'] - dataframe['close']) / 
                                              dataframe['close'])
        
        # Breakout Detection
        # Ref: Price Action - "Volume > Average x2 = Legitimate breakout"
        dataframe['breakout_signal'] = 0
        volume_avg = dataframe['volume'].rolling(20).mean()
        
        # Upside breakout: Price > 20-period high + volume confirmation
        dataframe.loc[
            (dataframe['high'] > dataframe['high'].shift(1).rolling(20).max()) &
            (dataframe['volume'] > volume_avg * 2),
            'breakout_signal'
        ] = 1
        
        # Downside breakout: Price < 20-period low + volume confirmation
        dataframe.loc[
            (dataframe['low'] < dataframe['low'].shift(1).rolling(20).min()) &
            (dataframe['volume'] > volume_avg * 2),
            'breakout_signal'
        ] = -1
        
        # Candlestick Pattern Recognition
        # Pinbar Pattern: Long wick / Small body > 3
        # Ref: Price Action - "Pinbar = Rejection formation"
        dataframe['upper_wick'] = dataframe['high'] - dataframe[['open', 'close']].max(axis=1)
        dataframe['lower_wick'] = dataframe[['open', 'close']].min(axis=1) - dataframe['low']
        dataframe['body'] = abs(dataframe['close'] - dataframe['open'])
        
        # Pinbar ratio
        total_wick = dataframe['upper_wick'] + dataframe['lower_wick']
        dataframe['pinbar_ratio'] = total_wick / (dataframe['body'] + 1e-6)
        
        # Pinbar signal (strong rejection)
        dataframe['is_pinbar'] = (dataframe['pinbar_ratio'] > 3).astype(int)
        
        # Engulfing Pattern: Current body > Previous body
        dataframe['engulfing'] = (
            (abs(dataframe['close'] - dataframe['open']) > 
             abs(dataframe['close'].shift(1) - dataframe['open'].shift(1)))
        ).astype(int)
        
        # =============================================
        # 5. QUANT ARBITRAGE: COINTEGRATION & PAIRS TRADING
        # =============================================
        
        # Cointegration Analysis (if we have BTC and ETH data)
        pair = metadata.get('pair', '')
        
        # Initialize cointegration features with defaults
        dataframe['coint_spread_zscore'] = 0.0
        dataframe['coint_is_cointegrated'] = 0
        dataframe['coint_hedge_ratio'] = 1.0
        dataframe['pairs_signal'] = 0  # -2: Short spread, -1: weak short, 0: none, 1: weak long, 2: Long spread
        
        # Only calculate if we have both BTC and ETH in whitelist
        if HAS_STATSMODELS and self.dp:
            try:
                whitelist = self.dp.current_whitelist()
                
                # Check if both BTC and ETH are in whitelist
                has_btc = any('BTC' in p for p in whitelist)
                has_eth = any('ETH' in p for p in whitelist)
                
                if has_btc and has_eth:
                    # Get BTC data
                    btc_pair = next((p for p in whitelist if 'BTC' in p), None)
                    eth_pair = next((p for p in whitelist if 'ETH' in p), None)
                    
                    if btc_pair and eth_pair:
                        btc_df = self.dp.get_pair_dataframe(pair=btc_pair, timeframe=self.timeframe)
                        eth_df = self.dp.get_pair_dataframe(pair=eth_pair, timeframe=self.timeframe)
                        
                        if not btc_df.empty and not eth_df.empty and len(btc_df) > 50 and len(eth_df) > 50:
                            # Align dataframes by date
                            btc_close = btc_df['close'].values
                            eth_close = eth_df['close'].values
                            
                            # Use minimum length
                            min_len = min(len(btc_close), len(eth_close))
                            btc_close = btc_close[-min_len:]
                            eth_close = eth_close[-min_len:]
                            
                            # REFACTORED: Use injected service (DIP compliance)
                            coint_result = self._cointegration_service.calculate_cointegration(
                                btc_close, eth_close, 'BTC', 'ETH'
                            )
                            
                            # Add features to current pair's dataframe
                            # Note: These are BTC-ETH relationship features, applicable to both pairs
                            dataframe['coint_spread_zscore'] = coint_result['spread_zscore']
                            dataframe['coint_is_cointegrated'] = int(coint_result['is_cointegrated'])
                            dataframe['coint_hedge_ratio'] = coint_result['hedge_ratio']
                            
                            # PAIRS TRADING SIGNAL
                            # Ref: Quant Arbitrage - Mean Reversion Strategy
                            z = coint_result['spread_zscore']
                            
                            if coint_result['is_cointegrated']:
                                # Strong signals (|z| > 2σ)
                                if z > 2.0:
                                    # Spread too wide: SHORT spread (BTC long, ETH short)
                                    dataframe['pairs_signal'] = -2
                                    if 'BTC' in pair:
                                        logger.info(f"[PAIRS] 📈 BTC LONG signal (Z={z:.2f})")
                                elif z < -2.0:
                                    # Spread too narrow: LONG spread (BTC short, ETH long)
                                    dataframe['pairs_signal'] = 2
                                    if 'ETH' in pair:
                                        logger.info(f"[PAIRS] 📈 ETH LONG signal (Z={z:.2f})")
                                # Weak signals (1σ < |z| < 2σ)
                                elif z > 1.0:
                                    dataframe['pairs_signal'] = -1
                                elif z < -1.0:
                                    dataframe['pairs_signal'] = 1
                                # Exit signals (|z| < 0.5)
                                elif abs(z) < 0.5:
                                    dataframe['pairs_signal'] = 0
                            
                            # SPREAD FEATURE for ML model
                            # Normalized spread value (useful for LightGBM)
                            dataframe['spread_normalized'] = coint_result['spread_zscore']
                            
            except Exception as e:
                logger.warning(f"Cointegration feature calculation error: {e}")
        
        # =============================================
        # TELEMETRY
        # =============================================
        self._perform_sync_check()
        self._track_model_retrain(dataframe)

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Price Action + Market Microstructure Optimized Stop Loss
        
        References:
        - Trading Exchanges (Larry Harris): "Limit order density at support/resistance"
        - ML for Algorithmic Trading: "Risk-proportional position sizing"
        - Price Action Trading: "Hide stop loss behind support"
        
        Rules:
        1. Profit-based: Move stop to lock profits at key levels
        2. Time-based: Tighten stop if trade ages (momentum decay)
        3. ATR-based: Volatility adjustment
        """
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if len(dataframe) < 2:
                return -0.055  # Default fallback
                
            current_candle = dataframe.iloc[-1]
            previous_candle = dataframe.iloc[-2]
            
            # ATR-based dynamic adjustment
            atr = current_candle.get('atr', 0) if 'atr' in current_candle else 0
            current_price = current_rate
            
            # Calculate ATR as percentage
            if atr > 0 and current_price > 0:
                atr_percent = atr / current_price
            else:
                atr_percent = 0.03  # Fallback: 3% average volatility
            
            # Trade duration (minutes)
            trade_duration = (current_time - trade.open_date_utc).total_seconds() / 60
            
            # ===== PROFIT PROTECTION (Price Action: Support/Resistance) =====
            # Lock in profits at progressively higher levels
            
            if current_profit >= 0.065:
                # +6.5% profit: Protect with tight stop at +4.5%
                # Ref: Price Action - "Resistance becomes support after breakout"
                return 0.045
            
            elif current_profit >= 0.04:
                # +4% profit: Protect with stop at +2.5%
                # Ref: Break-even with buffer
                return 0.025
            
            elif current_profit >= 0.018:
                # +1.8% profit: Tight break-even stop
                # Ref: Price Action - "Hide stop behind limit order cluster"
                return 0.005
            
            # ===== TIME DECAY (Momentum Loss) =====
            # Ref: Price Action - Contraction = Uncertainty increases
            
            elif trade_duration > 300:  # 5+ hours
                # Long positions: Momentum likely expired
                # Market has reconsolidated
                if current_profit > 0.01:
                    return 0.005  # Lock small gain
                else:
                    return -0.04  # Cut losses
            
            elif trade_duration > 120:  # 2+ hours
                # Mid-term: Contraction risk rising
                return -0.045
            
            elif trade_duration > 60:  # 1+ hour
                # Early-mid term: Normal stop
                return -0.050
            
            # ===== ATR-BASED DYNAMIC (Market Volatility) =====
            # Ref: ML Trading - Volatility adjustment of risk
            # Tight stop on low volatility, wider on high volatility
            
            if atr_percent > 0:
                # Conservative volatility multiplier (1.2x)
                volatility_adjusted_stop = -(atr_percent * 1.5)
                
                # Clamp between 3.5% and 7%
                volatility_adjusted_stop = max(min(volatility_adjusted_stop, -0.035), -0.07)
                
                return volatility_adjusted_stop
            
            # ===== DEFAULT: Initial ATR-based stop =====
            return -0.055
        
        except Exception as e:
            logger.warning(f"[STOPLOSS] Error in custom_stoploss: {e}")
            return -0.055

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Giriş sinyalleri.
        FreqAI prediction + CoinGecko sentiment + News sentiment + 
        Fear & Greed Index + Funding Rate + klasik RSI filtreleme.
        """
        # REFACTORED: Delegate to service method (SRP compliance)
        pair = metadata.get('pair', 'BTC/USDT:USDT')
        sentiment_data = self._get_sentiment_data(pair)
        
        news_sentiment = sentiment_data.get('sentiment', {'positive': 0, 'negative': 0, 'neutral': 100})
        sentiment_summary = sentiment_data.get('sentiment_label', 'neutral')  # For logging
        fear_greed = sentiment_data.get('fear_greed', {'value': 50, 'classification': 'Neutral'})
        funding_rate = sentiment_data.get('funding_rate', 0.0)
        
        # Uyarlanabilir entry threshold
        entry_threshold = self.entry_threshold.value
        exit_threshold_adj = self.exit_threshold.value
        
        # === FEAR & GREED INDEX ETKİSİ ===
        fg_value = fear_greed.get("value", 50)
        
        # Extreme Fear (< 25): LONG için threshold düşür (alım fırsatı!)
        if fg_value < 25:
            entry_threshold -= 0.05
            logger.info(f"🟢 Extreme Fear ({fg_value}): LONG boost, threshold {self.entry_threshold.value} -> {entry_threshold}")
        
        # Extreme Greed (> 75): SHORT için threshold düşür (satış fırsatı!)
        elif fg_value > 75:
            exit_threshold_adj += 0.05  # Daha az negatif = daha kolay short
            logger.info(f"🔴 Extreme Greed ({fg_value}): SHORT boost, threshold {self.exit_threshold.value} -> {exit_threshold_adj}")
        
        # === FUNDING RATE ETKİSİ ===
        # Yüksek pozitif funding (> 0.05%): Çok fazla long var, short fırsatı
        if funding_rate > 0.05:
            exit_threshold_adj += 0.03
            logger.info(f"📈 High Funding ({funding_rate:.4f}%): SHORT favored")
        
        # Yüksek negatif funding (< -0.05%): Çok fazla short var, long fırsatı
        elif funding_rate < -0.05:
            entry_threshold -= 0.03
            logger.info(f"📉 Negative Funding ({funding_rate:.4f}%): LONG favored")
        
        # === NEWS SENTIMENT ETKİSİ ===
        if news_sentiment.get("positive", 0) >= 70:
            entry_threshold -= 0.05
            logger.info(f"📰 Positive news: LONG boost")
        
        if news_sentiment.get("negative", 0) >= 70:
            exit_threshold_adj += 0.05
            logger.info(f"📰 Negative news: SHORT boost")
        
        # DEBUG: Son prediction değerlerini logla
        if len(dataframe) > 0:
            last_pred = dataframe["&-target"].iloc[-1] if "&-target" in dataframe.columns else 0
            last_di = dataframe["DI_values"].iloc[-1] if "DI_values" in dataframe.columns else 999
            last_do_predict = dataframe["do_predict"].iloc[-1] if "do_predict" in dataframe.columns else 0
            last_rsi = dataframe["rsi"].iloc[-1] if "rsi" in dataframe.columns else 50
            last_rsi_15m = dataframe["rsi_15m"].iloc[-1] if "rsi_15m" in dataframe.columns else 50
            last_rsi_1h = dataframe["rsi_1h"].iloc[-1] if "rsi_1h" in dataframe.columns else 50
            
            # === TELEMETRY: Enhanced Strategy Logging ===
            # Calculate LightGBM confidence (based on DI_values - lower is better)
            confidence_score = max(0, min(100, 100 - (last_di * 10)))  # DI < 4 → confidence > 60%
            
            # Cointegration health proxy (using prediction variance)
            # Lower variance = better cointegration
            coint_health_proxy = "STRONG" if last_di < 2 else "MODERATE" if last_di < 4 else "WEAK"
            
            logger.info(f"[STRATEGY] 📊 {pair} | Pred: {last_pred:.4f} | Confidence: {confidence_score:.1f}% | Coint: {coint_health_proxy} | do_predict: {last_do_predict}")
            logger.info(f"[STRATEGY] 📊 RSI: {last_rsi:.1f}/{last_rsi_15m:.1f}/{last_rsi_1h:.1f} | Sentiment: {sentiment_summary}")
            logger.info(f"[STRATEGY] 📊 Thresholds | LONG > {entry_threshold:.2f} | SHORT < {exit_threshold_adj:.2f}")

        # LONG giriş - MASTER FEATURE VECTOR
        # Ref: Harris + Tsay + Jansen + Price Action
        dataframe.loc[
            (
                # ===== FREQAI PREDICTION (Jansen: ML Model) =====
                # Model tahmin geçerli
                (dataframe["do_predict"] == 1)
                &
                # FreqAI pozitif tahmin
                (dataframe["&-target"] > entry_threshold)
                &
                # Model güvenilirliği (DI < 4)
                (dataframe["DI_values"] < 4)
                &
                # ===== HARRIS: MARKET MICROSTRUCTURE =====
                # Order Imbalance: Buy pressure > Sell pressure
                (dataframe["order_imbalance"] > 1.0)
                &
                # VWAP Deviation: Fiyat VWAP'ten +% sapmış (Uptrend)
                (dataframe["vwap_deviation"] > 0.001)
                &
                # Bid-Ask Spread normal (likidite var)
                (dataframe["bid_ask_spread"] < 0.05)
                &
                # ===== TSAY: TIME SERIES =====
                # Volatility acceptable (not extreme)
                (dataframe["volatility_zscore"] < 2.0)
                &
                # No white noise (returns correlated)
                (dataframe["returns_autocorr"] > -0.2)
                &
                # ===== JANSEN: NORMALIZED FACTORS =====
                # RSI not overbought (z-score normalized)
                (dataframe["rsi_zscore"] < 1.5)
                &
                # Momentum positive (z-score)
                (dataframe["momentum_zscore"] > -0.5)
                &
                # Multi-timeframe confirmation
                (dataframe["rsi_zscore_15m"] < 1.0)
                &
                (dataframe["rsi_zscore_1h"] < 0.5)
                &
                # ===== PRICE ACTION: BEHAVIORAL PATTERNS =====
                # Support proximity: Close near support but with room
                (dataframe["distance_to_support"] > 0.01)
                &
                (dataframe["distance_to_support"] < 0.15)
                &
                # Breakout confirmation
                (dataframe["breakout_signal"] >= 0)  # Not breaking down
                &
                # Candlestick pattern: Not strong rejection (pinbar)
                (dataframe["is_pinbar"] == 0) | (dataframe["upper_wick"] < dataframe["lower_wick"])
                &
                # Bollinger Bands: Price in lower half (room to grow)
                (dataframe["close"] < dataframe["bb_middleband"])
                &
                # Volume confirmation
                (dataframe["volume"] > 0)
                &
                # ===== QUANT ARBITRAGE: COINTEGRATION BOOST =====
                # If pairs are cointegrated AND signal is positive for this pair, boost entry
                # Signal logic: BTC gets signal=-2 when Z>2 (BTC long), ETH gets signal=2 when Z<-2 (ETH long)
                (
                    (dataframe["coint_is_cointegrated"] == 0)  # No cointegration, normal entry
                    |
                    (  # Cointegration exists, check pairs signal
                        (dataframe["coint_is_cointegrated"] == 1)
                        &
                        (  # Pairs signal supports LONG for this asset
                            (dataframe["pairs_signal"] >= 0)  # Neutral or positive
                        )
                    )
                )
            ),
            "enter_long"
        ] = 1

        # SHORT giriş - MASTER FEATURE VECTOR
        dataframe.loc[
            (
                # ===== FREQAI PREDICTION =====
                (dataframe["do_predict"] == 1)
                &
                (dataframe["&-target"] < exit_threshold_adj)
                &
                (dataframe["DI_values"] < 4)
                &
                # ===== HARRIS: MARKET MICROSTRUCTURE =====
                # Order Imbalance: Sell pressure > Buy pressure
                (dataframe["order_imbalance"] < 1.0)
                &
                # VWAP Deviation: Fiyat VWAP'ten -% sapmış (Downtrend)
                (dataframe["vwap_deviation"] < -0.001)
                &
                # Bid-Ask Spread normal
                (dataframe["bid_ask_spread"] < 0.05)
                &
                # ===== TSAY: TIME SERIES =====
                # Volatility acceptable
                (dataframe["volatility_zscore"] < 2.0)
                &
                # No white noise
                (dataframe["returns_autocorr"] > -0.2)
                &
                # ===== JANSEN: NORMALIZED FACTORS =====
                # RSI not oversold
                (dataframe["rsi_zscore"] > -1.5)
                &
                # Momentum negative
                (dataframe["momentum_zscore"] < 0.5)
                &
                # Multi-timeframe confirmation
                (dataframe["rsi_zscore_15m"] > -1.0)
                &
                (dataframe["rsi_zscore_1h"] > -0.5)
                &
                # ===== PRICE ACTION: BEHAVIORAL PATTERNS =====
                # Resistance proximity: Close near resistance
                (dataframe["distance_to_resistance"] > 0.01)
                &
                (dataframe["distance_to_resistance"] < 0.15)
                &
                # Breakout confirmation (downside)
                (dataframe["breakout_signal"] <= 0)  # Not breaking up
                &
                # Candlestick pattern: Not strong rejection upside
                (dataframe["is_pinbar"] == 0) | (dataframe["lower_wick"] < dataframe["upper_wick"])
                &
                # Bollinger Bands: Price in upper half (room to fall)
                (dataframe["close"] > dataframe["bb_middleband"])
                &
                # Volume confirmation
                (dataframe["volume"] > 0)
                &
                # ===== QUANT ARBITRAGE: COINTEGRATION BOOST =====
                (
                    (dataframe["coint_is_cointegrated"] == 0)  # No cointegration, normal entry
                    |
                    (  # Cointegration exists, check pairs signal
                        (dataframe["coint_is_cointegrated"] == 1)
                        &
                        (  # Pairs signal supports SHORT for this asset
                            (dataframe["pairs_signal"] <= 0)  # Neutral or negative
                        )
                    )
                )
            ),
            "enter_short"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Çıkış sinyalleri - Model tahminlerine göre.
        Partial TP için ROI kullan (minimal_roi tanımı).
        """
        # News sentiment kontrol - pair'e göre cache key
        pair = metadata.get('pair', 'BTC/USDT:USDT')
        news_sentiment = {"positive": 0, "negative": 0, "neutral": 100}
        
        current_hour = int(time.time() / 3600)
        
        # Pair'e göre symbol belirle
        if pair == "BTC/USDT:USDT":
            symbol = "BTC"
        elif pair == "ETH/USDT:USDT":
            symbol = "ETH"
        else:
            symbol = None
        
        if symbol:
            cache_key = f"api_calls_{symbol}_{current_hour}"
            if cache_key in self.sentiment_cache:
                news_sentiment = self.sentiment_cache[cache_key].get("news", news_sentiment)
        
        # LONG çıkış - OR koşulu ile daha güvenli
        dataframe.loc[
            (
                # Model güçlü negatif hale geldi VEYA RSI overbought
                (dataframe["&-target"] < -0.15)
                |
                # RSI çok overbought
                (dataframe["rsi"] > 80)
            ),
            "exit_long"
        ] = 1

        # SHORT çıkış - OR koşulu ile daha güvenli
        dataframe.loc[
            (
                # Model güçlü pozitif hale geldi VEYA RSI oversold
                (dataframe["&-target"] > 0.15)
                |
                # RSI çok oversold
                (dataframe["rsi"] < 20)
            ),
            "exit_short"
        ] = 1

        return dataframe
