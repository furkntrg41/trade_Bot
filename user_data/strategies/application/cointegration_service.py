"""
Application Layer - Cointegration Service
==========================================
Business logic for statistical arbitrage (SRP)
"""
import logging
import numpy as np
from typing import Dict, Optional

from ..core.interfaces import ICointegrationAnalyzer

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.stattools import coint, adfuller
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools.tools import add_constant
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels not available. Cointegration disabled.")


class CointegrationService(ICointegrationAnalyzer):
    """
    Engle-Granger cointegration analysis service (SRP)
    No external dependencies except cache (DIP via constructor injection)
    """
    
    def __init__(self, cache_service=None, max_spread_history: int = 252):
        self.cache = cache_service
        self.spread_history: Dict[str, list] = {}
        self._max_spread_history = max_spread_history
    
    def calculate_cointegration(
        self, 
        price_x: np.ndarray, 
        price_y: np.ndarray, 
        pair_x: str, 
        pair_y: str
    ) -> Dict:
        """
        Implementation of ICointegrationAnalyzer
        
        Returns:
            {
                'is_cointegrated': bool,
                'hedge_ratio': float,
                'spread_current': float,
                'spread_zscore': float,
                'coint_pvalue': float,
                'correlation': float
            }
        """
        if not HAS_STATSMODELS:
            return self._empty_result()
        
        if len(price_x) < 50 or len(price_y) < 50:
            return self._empty_result()
        
        try:
            # Use last 252 candles
            lookback = min(252, len(price_x), len(price_y))
            price_x = price_x[-lookback:]
            price_y = price_y[-lookback:]
            
            # 1. Calculate hedge ratio (OLS regression)
            hedge_ratio = self._calculate_hedge_ratio(price_x, price_y)
            
            # 2. Calculate spread
            spread = self._calculate_spread(price_x, price_y, hedge_ratio)
            
            # 3. Cointegration test
            coint_stat, coint_pvalue, _ = coint(price_y, price_x)
            is_cointegrated = coint_pvalue < 0.05
            
            # 4. Z-score for mean reversion signal
            spread_mean = np.mean(spread)
            spread_std = np.std(spread)
            spread_current = spread[-1]
            spread_zscore = (spread_current - spread_mean) / (spread_std + 1e-6)
            
            # 5. Cache spread history
            pair_key = f"{pair_x}_{pair_y}"
            if pair_key not in self.spread_history:
                self.spread_history[pair_key] = []
            
            self.spread_history[pair_key].append(spread_current)
            if len(self.spread_history[pair_key]) > self._max_spread_history:
                self.spread_history[pair_key] = self.spread_history[pair_key][-self._max_spread_history:]
            
            result = {
                'is_cointegrated': is_cointegrated,
                'hedge_ratio': hedge_ratio,
                'spread_current': spread_current,
                'spread_zscore': spread_zscore,
                'coint_pvalue': coint_pvalue,
                'correlation': np.corrcoef(price_x, price_y)[0, 1]
            }
            
            if is_cointegrated:
                logger.info(
                    f"[COINTEGRATION] ✅ {pair_x} vs {pair_y} | "
                    f"Hedge: {hedge_ratio:.4f} | Z-Score: {spread_zscore:.2f} | "
                    f"p-value: {coint_pvalue:.4f}"
                )
            
            return result
            
        except Exception as e:
            logger.warning(f"Cointegration calculation error: {e}")
            return self._empty_result()
    
    def _calculate_hedge_ratio(self, price_x: np.ndarray, price_y: np.ndarray) -> float:
        """OLS regression: log(Y) = α + β*log(X) + ε"""
        log_x = np.log(price_x)
        log_y = np.log(price_y)
        
        X = add_constant(log_x)
        model = OLS(log_y, X).fit()
        
        return model.params[1]  # β coefficient
    
    def _calculate_spread(
        self, 
        price_x: np.ndarray, 
        price_y: np.ndarray, 
        hedge_ratio: float
    ) -> np.ndarray:
        """Spread = log(Y) - β*log(X)"""
        log_x = np.log(price_x)
        log_y = np.log(price_y)
        
        return log_y - hedge_ratio * log_x
    
    def _empty_result(self) -> Dict:
        """Return empty result when cointegration unavailable"""
        return {
            'is_cointegrated': False,
            'hedge_ratio': 0.0,
            'spread_current': 0.0,
            'spread_zscore': 0.0,
            'coint_pvalue': 1.0,
            'correlation': 0.0
        }
