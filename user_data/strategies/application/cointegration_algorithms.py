"""
Application - Cointegration Algorithms (Strategy Pattern)
==========================================================
Swappable cointegration methods via config (OCP).

Design:
- Each algorithm = separate class
- Interface: ICointegrationAlgorithm
- Factory: Create algorithm from config name
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Tuple
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Statsmodels imports
try:
    from statsmodels.tsa.stattools import coint, adfuller
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools.tools import add_constant
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels not available - cointegration disabled")


class ICointegrationAlgorithm(ABC):
    """
    Base interface for cointegration testing (Strategy Pattern).
    
    OCP: New algorithm = new class, no modification to existing code
    SRP: Each class = one algorithm
    LSP: All algorithms return same result structure
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.p_value_threshold = config.get('p_value_threshold', 0.05)
        self.lookback = config.get('lookback_period', 252)
    
    @abstractmethod
    def test_cointegration(
        self,
        price_x: np.ndarray,
        price_y: np.ndarray
    ) -> Dict:
        """
        Test if two price series are cointegrated.
        
        Returns:
            {
                'is_cointegrated': bool,
                'p_value': float,
                'hedge_ratio': float,
                'spread': np.ndarray,
                'z_score': float,
                'method': str
            }
        
        Time: O(n) where n = lookback period
        """
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """Return algorithm name for logging"""
        pass


class EngleGrangerCointegration(ICointegrationAlgorithm):
    """
    Engle-Granger 2-step cointegration test.
    
    Method:
    1. OLS regression: Y = α + β*X + ε
    2. ADF test on residuals
    
    Pros: Simple, fast O(n)
    Cons: Only detects ONE cointegrating relationship
    
    References:
    - Engle & Granger (1987)
    - Jansen "Machine Learning for Algorithmic Trading" Ch. 9
    """
    
    def test_cointegration(
        self,
        price_x: np.ndarray,
        price_y: np.ndarray
    ) -> Dict:
        """
        Engle-Granger test implementation.
        
        Time: O(n) where n = len(price_x)
        Space: O(n) for spread storage
        """
        if not HAS_STATSMODELS:
            return self._null_result()
        
        # Take last N observations
        price_x = price_x[-self.lookback:]
        price_y = price_y[-self.lookback:]
        
        if len(price_x) < 50 or len(price_y) < 50:
            return self._null_result()
        
        try:
            # Step 1: OLS Regression (log prices)
            log_x = np.log(price_x)
            log_y = np.log(price_y)
            
            X = add_constant(log_x)
            model = OLS(log_y, X).fit()
            hedge_ratio = model.params[1]
            
            # Step 2: Calculate spread (residuals)
            spread = log_y - hedge_ratio * log_x
            
            # Step 3: ADF test on spread
            coint_stat, p_value, _ = coint(price_y, price_x)
            is_cointegrated = p_value < self.p_value_threshold
            
            # Z-score for mean reversion signal
            spread_mean = np.mean(spread)
            spread_std = np.std(spread)
            z_score = (spread[-1] - spread_mean) / (spread_std + 1e-6)
            
            return {
                'is_cointegrated': is_cointegrated,
                'p_value': p_value,
                'hedge_ratio': hedge_ratio,
                'spread': spread,
                'z_score': z_score,
                'method': 'Engle-Granger',
                'spread_mean': spread_mean,
                'spread_std': spread_std
            }
        
        except Exception as e:
            logger.error(f"Engle-Granger test failed: {e}")
            return self._null_result()
    
    def get_algorithm_name(self) -> str:
        return "Engle-Granger (1987)"
    
    def _null_result(self) -> Dict:
        """Return null result when test fails"""
        return {
            'is_cointegrated': False,
            'p_value': 1.0,
            'hedge_ratio': 0.0,
            'spread': np.array([]),
            'z_score': 0.0,
            'method': 'Engle-Granger'
        }


class JohansenCointegration(ICointegrationAlgorithm):
    """
    Johansen cointegration test (more advanced).
    
    Method:
    - Vector Error Correction Model (VECM)
    - Can detect MULTIPLE cointegrating relationships
    
    Pros: More powerful than Engle-Granger
    Cons: More complex, slower O(n²)
    
    References:
    - Johansen (1991)
    - "Pairs Trading: Quantitative Methods and Analysis" Ch. 4
    
    TODO: Implement when statsmodels.tsa.vector_ar available
    """
    
    def test_cointegration(
        self,
        price_x: np.ndarray,
        price_y: np.ndarray
    ) -> Dict:
        """
        Johansen test (placeholder - requires vecm module).
        
        Time: O(n²) matrix operations
        """
        logger.warning("Johansen test not implemented yet - falling back to Engle-Granger")
        
        # Fallback to Engle-Granger
        eg = EngleGrangerCointegration(self.config)
        result = eg.test_cointegration(price_x, price_y)
        result['method'] = 'Johansen (fallback: EG)'
        return result
    
    def get_algorithm_name(self) -> str:
        return "Johansen (1991)"


class KalmanFilterCointegration(ICointegrationAlgorithm):
    """
    Kalman Filter for time-varying hedge ratio.
    
    Method:
    - State-space model
    - Hedge ratio adapts over time (non-stationary)
    
    Pros: Handles regime changes
    Cons: Complex, requires tuning (process noise)
    
    References:
    - "Algorithmic Trading" by Chan (2013) Ch. 3
    
    TODO: Implement using pykalman or custom implementation
    """
    
    def test_cointegration(
        self,
        price_x: np.ndarray,
        price_y: np.ndarray
    ) -> Dict:
        """
        Kalman filter hedge ratio (placeholder).
        
        Time: O(n) for sequential filtering
        """
        logger.warning("Kalman Filter not implemented yet - falling back to Engle-Granger")
        
        eg = EngleGrangerCointegration(self.config)
        result = eg.test_cointegration(price_x, price_y)
        result['method'] = 'Kalman Filter (fallback: EG)'
        return result
    
    def get_algorithm_name(self) -> str:
        return "Kalman Filter (Time-Varying)"


# =============================================================================
# FACTORY + AUTO-REGISTRATION
# =============================================================================
from core.provider_registry import ProviderRegistry

ProviderRegistry.register("EngleGrangerCointegration", EngleGrangerCointegration)
ProviderRegistry.register("JohansenCointegration", JohansenCointegration)
ProviderRegistry.register("KalmanFilterCointegration", KalmanFilterCointegration)

logger.info("✅ Cointegration algorithms registered: Engle-Granger, Johansen, Kalman")


def create_cointegration_algorithm(config: Dict) -> ICointegrationAlgorithm:
    """
    Factory function: Create algorithm from config.
    
    OCP: Add new algorithm → register in ProviderRegistry → available here
    
    Args:
        config: {
            'name': 'EngleGrangerCointegration',
            'p_value_threshold': 0.05,
            'lookback_period': 252
        }
    
    Returns:
        ICointegrationAlgorithm instance
    """
    name = config.get('name', 'EngleGrangerCointegration')
    
    try:
        algorithm_class = ProviderRegistry.get(name)
        return algorithm_class(config)
    
    except KeyError:
        logger.error(f"Algorithm '{name}' not found - using Engle-Granger")
        return EngleGrangerCointegration(config)
