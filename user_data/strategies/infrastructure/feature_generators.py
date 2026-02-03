"""
Infrastructure - Technical Indicator Generators (Concrete Implementations)
===========================================================================
Each class = ONE category of indicators (SRP)

Complexity Analysis:
- Most TA-Lib functions: O(n) where n = dataframe rows
- RSI: O(n) rolling window calculation
- Bollinger Bands: O(n) moving average + std
- EMA: O(n) exponential weighted average

Memory: O(m) where m = new columns (typically m << n)
"""
import logging
from typing import Dict, Any
from pandas import DataFrame
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_interfaces import IFeatureGenerator

logger = logging.getLogger(__name__)

# TA-Lib imports
try:
    import talib.abstract as ta
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    logger.warning("TA-Lib not available - technical indicators disabled")


class MomentumFeatureGenerator(IFeatureGenerator):
    """
    RSI-based momentum features (SRP: only momentum).
    
    Features:
    - RSI (14, 50 periods)
    - RSI slope (momentum change rate)
    - RSI divergence detection
    
    Time: O(n) per RSI calculation
    Space: O(n) for each new column
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.rsi_periods = self.config.get('rsi_periods', [14, 50])
    
    def generate(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate RSI-based features"""
        if not HAS_TALIB:
            return dataframe
        
        df = dataframe.copy()
        
        for period in self.rsi_periods:
            col_name = f"rsi_{period}"
            df[col_name] = ta.RSI(df, timeperiod=period)
            
            # RSI slope (momentum of momentum)
            df[f"{col_name}_slope"] = df[col_name].diff(5)
        
        # RSI divergence: price up but RSI down (bearish)
        if 'rsi_14' in df.columns:
            price_slope = df['close'].diff(5)
            rsi_slope = df['rsi_14'].diff(5)
            
            df['rsi_divergence'] = np.where(
                (price_slope > 0) & (rsi_slope < 0), -1,  # Bearish divergence
                np.where((price_slope < 0) & (rsi_slope > 0), 1, 0)  # Bullish divergence
            )
        
        return df
    
    def get_feature_names(self) -> list[str]:
        """Return list of generated features"""
        features = []
        for period in self.rsi_periods:
            features.extend([
                f"rsi_{period}",
                f"rsi_{period}_slope"
            ])
        features.append('rsi_divergence')
        return features


class VolatilityFeatureGenerator(IFeatureGenerator):
    """
    Bollinger Bands + ATR volatility features (SRP).
    
    Features:
    - Bollinger %B (position within bands)
    - Bollinger width (volatility proxy)
    - ATR (Average True Range)
    - ATR slope (volatility acceleration)
    
    Time: O(n) for moving avg calculations
    Space: O(4n) for 4 new columns
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.bb_period = self.config.get('bb_period', 20)
        self.bb_std = self.config.get('bb_std', 2.0)
        self.atr_period = self.config.get('atr_period', 14)
    
    def generate(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate volatility features"""
        if not HAS_TALIB:
            return dataframe
        
        df = dataframe.copy()
        
        # Bollinger Bands
        bollinger = ta.BBANDS(
            df,
            timeperiod=self.bb_period,
            nbdevup=self.bb_std,
            nbdevdn=self.bb_std
        )
        
        df['bb_upper'] = bollinger['upperband']
        df['bb_mid'] = bollinger['middleband']
        df['bb_lower'] = bollinger['lowerband']
        
        # %B: Position within bands (0 = lower, 1 = upper)
        df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Bollinger width: Volatility measure
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
        
        # ATR
        df['atr'] = ta.ATR(df, timeperiod=self.atr_period)
        
        # ATR slope: Is volatility increasing?
        df['atr_slope'] = df['atr'].diff(5)
        
        return df
    
    def get_feature_names(self) -> list[str]:
        return [
            'bb_upper', 'bb_mid', 'bb_lower',
            'bb_percent', 'bb_width',
            'atr', 'atr_slope'
        ]


class TrendFeatureGenerator(IFeatureGenerator):
    """
    EMA crossovers + trend strength (SRP).
    
    Features:
    - EMA (9, 21, 50, 200)
    - EMA crossovers (golden cross, death cross)
    - Trend strength (EMA alignment)
    
    Time: O(n) per EMA
    Space: O(m × n) where m = number of EMAs
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.ema_periods = self.config.get('ema_periods', [9, 21, 50, 200])
    
    def generate(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate trend features"""
        if not HAS_TALIB:
            return dataframe
        
        df = dataframe.copy()
        
        # Calculate EMAs
        for period in self.ema_periods:
            df[f'ema_{period}'] = ta.EMA(df, timeperiod=period)
        
        # Golden Cross: Fast EMA crosses above slow EMA (bullish)
        if 'ema_50' in df.columns and 'ema_200' in df.columns:
            df['golden_cross'] = (
                (df['ema_50'] > df['ema_200']) &
                (df['ema_50'].shift(1) <= df['ema_200'].shift(1))
            ).astype(int)
            
            # Death Cross: Fast EMA crosses below slow EMA (bearish)
            df['death_cross'] = (
                (df['ema_50'] < df['ema_200']) &
                (df['ema_50'].shift(1) >= df['ema_200'].shift(1))
            ).astype(int)
        
        # Trend strength: All EMAs aligned
        if len(self.ema_periods) >= 3:
            ema_cols = [f'ema_{p}' for p in sorted(self.ema_periods)[:3]]
            
            # Uptrend: ema_9 > ema_21 > ema_50
            df['trend_strength'] = 0
            if all(col in df.columns for col in ema_cols):
                uptrend = (df[ema_cols[0]] > df[ema_cols[1]]) & (df[ema_cols[1]] > df[ema_cols[2]])
                downtrend = (df[ema_cols[0]] < df[ema_cols[1]]) & (df[ema_cols[1]] < df[ema_cols[2]])
                
                df['trend_strength'] = np.where(uptrend, 1, np.where(downtrend, -1, 0))
        
        return df
    
    def get_feature_names(self) -> list[str]:
        features = [f'ema_{p}' for p in self.ema_periods]
        features.extend(['golden_cross', 'death_cross', 'trend_strength'])
        return features


class VolumeFeatureGenerator(IFeatureGenerator):
    """
    Volume-based features (SRP).
    
    Features:
    - Volume MA (moving average)
    - Volume surge detection
    - OBV (On-Balance Volume)
    
    Time: O(n) for rolling calculations
    Space: O(3n) for 3 columns
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.volume_ma_period = self.config.get('volume_ma_period', 20)
    
    def generate(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate volume features"""
        df = dataframe.copy()
        
        # Volume moving average
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        
        # Volume surge: Current > 2x average
        df['volume_surge'] = (df['volume'] > df['volume_ma'] * 2).astype(int)
        
        # OBV (On-Balance Volume): Cumulative volume flow
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        
        return df
    
    def get_feature_names(self) -> list[str]:
        return ['volume_ma', 'volume_surge', 'obv']


# =============================================================================
# AUTO-REGISTRATION (similar to providers)
# =============================================================================
from core.provider_registry import ProviderRegistry

ProviderRegistry.register("MomentumFeatureGenerator", MomentumFeatureGenerator)
ProviderRegistry.register("VolatilityFeatureGenerator", VolatilityFeatureGenerator)
ProviderRegistry.register("TrendFeatureGenerator", TrendFeatureGenerator)
ProviderRegistry.register("VolumeFeatureGenerator", VolumeFeatureGenerator)

logger.info(f"✅ Feature generators registered: Momentum, Volatility, Trend, Volume")
