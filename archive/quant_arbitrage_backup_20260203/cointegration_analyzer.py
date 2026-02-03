"""
Kointegrasyon Analiz Modülü
============================
Engle-Granger Kointegrasyon Testi ve Kalman Filtresi tabanlı Hedge Ratio Dinamiği
İstatistiksel arbitraj için pairwise kointegrasyon taraması yapılır.

Author: Quant Team
Date: 2026-02-01
"""

import logging
from dataclasses import dataclass
from typing import Tuple, Dict, Optional, List
import numpy as np
import pandas as pd
from scipy import stats

try:
    from statsmodels.tsa.stattools import adfuller, coint
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools.tools import add_constant
except ImportError:
    raise ImportError("statsmodels kütüphanesi gereklidir. Kurulum: pip install statsmodels")


logger = logging.getLogger(__name__)


@dataclass
class CointegrationResult:
    """Kointegrasyon test sonuçları"""
    pair_x: str
    pair_y: str
    correlation: float
    hedge_ratio: float  # β (beta)
    adf_statistic: float
    adf_pvalue: float
    coint_statistic: float
    coint_pvalue: float
    is_cointegrated: bool  # p_value < 0.05
    half_life: float  # Mean reversion half-life in periods
    
    def __str__(self) -> str:
        status = "✅ CO-INT" if self.is_cointegrated else "❌ NO"
        return (
            f"{self.pair_x} vs {self.pair_y} | Hedge: {self.hedge_ratio:.4f} | "
            f"ADF p: {self.adf_pvalue:.4f} | Coint p: {self.coint_pvalue:.4f} | "
            f"{status} | Half-life: {self.half_life:.1f}"
        )


class CointegrationAnalyzer:
    """
    İstatistiksel arbitraj için kointegrasyon analizi.
    
    Prensip:
    --------
    İki hisse senedi X ve Y'nin fiyat serileri I(1) (integrated of order 1) olsa bile,
    eğer kointegre edebilirse (co-integrated), aralarındaki spread I(0) (stationary) olur.
    
    Spread = log(Y) - β*log(X)  olur ve mean-reverting olur.
    """
    
    def __init__(
        self,
        lookback_window: int = 1440,  # 60 days * 24 hours = 1440 hourly candles
        adf_pvalue_threshold: float = 0.05,
        coint_pvalue_threshold: float = 0.05,
        min_correlation: float = 0.5,
    ):
        """
        Args:
            lookback_window: Kointegrasyon testi için geçmiş veri dönem sayısı (1h candles)
            adf_pvalue_threshold: ADF testinde stationarity için p-value threshold
            coint_pvalue_threshold: Johansen testinde kointegrasyon threshold
            min_correlation: Ön-filtre: En azından bu kadar korelasyonlu olmalı
        """
        self.lookback_window = lookback_window
        self.adf_pvalue_threshold = adf_pvalue_threshold
        self.coint_pvalue_threshold = coint_pvalue_threshold
        self.min_correlation = min_correlation
        
    def calculate_hedge_ratio(self, price_x: np.ndarray, price_y: np.ndarray) -> float:
        """
        OLS Regresyon ile Hedge Ratio (β) hesapla.
        
        Modeli: log(Y) = α + β*log(X) + ε
        
        Args:
            price_x: X'in kapanış fiyatları (log-ı alınacak)
            price_y: Y'nin kapanış fiyatları (log-ı alınacak)
            
        Returns:
            Hedge ratio β
        """
        if len(price_x) < 2 or len(price_y) < 2:
            raise ValueError("En azından 2 gözlem gereklidir")
        
        # Log-lar
        log_x = np.log(price_x)
        log_y = np.log(price_y)
        
        # OLS Regresyon
        X = add_constant(log_x)
        model = OLS(log_y, X).fit()
        
        # β katsayısı
        beta = model.params[1]
        
        logger.debug(f"Hedge ratio calculation: β={beta:.4f}, R²={model.rsquared:.4f}")
        return beta
    
    def calculate_spread(
        self, price_x: np.ndarray, price_y: np.ndarray, hedge_ratio: float
    ) -> np.ndarray:
        """
        Spread hesabı: Z_t = log(Y_t) - β*log(X_t)
        
        Args:
            price_x: X fiyatları
            price_y: Y fiyatları
            hedge_ratio: Ağırlık oranı β
            
        Returns:
            Spread serisi
        """
        log_x = np.log(price_x)
        log_y = np.log(price_y)
        spread = log_y - hedge_ratio * log_x
        return spread
    
    def test_stationarity(self, series: np.ndarray, name: str = "Series") -> Tuple[float, float]:
        """
        Augmented Dickey-Fuller (ADF) Stationarity Testi
        
        H₀: Seri unit root'u var (non-stationary)
        H₁: Seri stationary
        
        Args:
            series: Test edilecek seri
            name: Loglama için ad
            
        Returns:
            (test_statistic, p_value)
        """
        if len(series) < 4:
            logger.warning(f"ADF testi için çok az veri: {len(series)} obs")
            return np.nan, np.nan
        
        try:
            result = adfuller(series, autolag="AIC")
            adf_stat = result[0]
            p_value = result[1]
            
            is_stationary = p_value < self.adf_pvalue_threshold
            status = "✅ Stationary" if is_stationary else "❌ Non-Stationary"
            logger.debug(
                f"ADF Test ({name}): stat={adf_stat:.4f}, p-value={p_value:.4f} {status}"
            )
            
            return adf_stat, p_value
        except Exception as e:
            logger.error(f"ADF test hatası: {e}")
            return np.nan, np.nan
    
    def test_cointegration(
        self, price_x: np.ndarray, price_y: np.ndarray
    ) -> CointegrationResult:
        """
        Engle-Granger Kointegrasyon Testi
        
        H₀: X ve Y kointegre değildir
        H₁: X ve Y kointegre edilir
        
        Args:
            price_x: X fiyat serisi
            price_y: Y fiyat serisi
            
        Returns:
            CointegrationResult dataclass
        """
        pair_x, pair_y = "X", "Y"  # Placeholder
        
        if len(price_x) < self.lookback_window:
            logger.warning(
                f"Yeterli veri yok: {len(price_x)} < {self.lookback_window}"
            )
            return CointegrationResult(
                pair_x=pair_x, pair_y=pair_y,
                correlation=0.0, hedge_ratio=0.0,
                adf_statistic=np.nan, adf_pvalue=1.0,
                coint_statistic=np.nan, coint_pvalue=1.0,
                is_cointegrated=False, half_life=np.inf
            )
        
        # Lookback window'a kırp
        price_x = price_x[-self.lookback_window:]
        price_y = price_y[-self.lookback_window:]
        
        try:
            # 1. Pearson Korelasyonu (ön-filtre)
            correlation = np.corrcoef(price_x, price_y)[0, 1]
            if correlation < self.min_correlation:
                logger.debug(f"Düşük korelasyon: {correlation:.4f} < {self.min_correlation}")
                return CointegrationResult(
                    pair_x=pair_x, pair_y=pair_y,
                    correlation=correlation, hedge_ratio=0.0,
                    adf_statistic=np.nan, adf_pvalue=1.0,
                    coint_statistic=np.nan, coint_pvalue=1.0,
                    is_cointegrated=False, half_life=np.inf
                )
            
            # 2. Hedge Ratio hesapla
            hedge_ratio = self.calculate_hedge_ratio(price_x, price_y)
            
            # 3. Spread hesapla
            spread = self.calculate_spread(price_x, price_y, hedge_ratio)
            
            # 4. ADF testi (spread'in stationarity'si)
            adf_stat, adf_pvalue = self.test_stationarity(spread, "Spread")
            
            # 5. Cointegration testi (statsmodels)
            coint_stat, coint_pvalue, _ = coint(price_y, price_x)
            
            # 6. Half-life hesabı (mean reversion hızı)
            half_life = self._calculate_half_life(spread)
            
            is_cointegrated = (
                adf_pvalue < self.adf_pvalue_threshold and
                coint_pvalue < self.coint_pvalue_threshold
            )
            
            result = CointegrationResult(
                pair_x=pair_x,
                pair_y=pair_y,
                correlation=correlation,
                hedge_ratio=hedge_ratio,
                adf_statistic=adf_stat,
                adf_pvalue=adf_pvalue,
                coint_statistic=coint_stat,
                coint_pvalue=coint_pvalue,
                is_cointegrated=is_cointegrated,
                half_life=half_life
            )
            
            logger.info(f"Cointegration Test: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Kointegrasyon testi hatası: {e}")
            return CointegrationResult(
                pair_x=pair_x, pair_y=pair_y,
                correlation=0.0, hedge_ratio=0.0,
                adf_statistic=np.nan, adf_pvalue=1.0,
                coint_statistic=np.nan, coint_pvalue=1.0,
                is_cointegrated=False, half_life=np.inf
            )
    
    @staticmethod
    def _calculate_half_life(series: np.ndarray, min_periods: int = 10) -> float:
        """
        Mean Reversion Half-Life hesabı.
        Spread mean'ine geri dönüş ne kadar sürer?
        
        Formula: Δy_t = λ * (mean - y_{t-1}) + ε_t
        Half-life = -ln(2) / ln(1 + λ)
        
        Args:
            series: Spread serisi
            min_periods: Minimum gözlem sayısı
            
        Returns:
            Half-life (hourly candles cinsinden - e.g., 12 = 12 hours)
        """
        if len(series) < min_periods:
            return np.inf
        
        try:
            # Farklar
            delta_y = np.diff(series)
            y_lag = series[:-1]
            
            # Regresyon: Δy = λ*y + const + error
            X = add_constant(y_lag)
            model = OLS(delta_y, X).fit()
            lambda_param = model.params[1]
            
            if lambda_param >= 0:
                return np.inf  # Mean reversion yok
            
            half_life = -np.log(2) / np.log(1 + lambda_param)
            return max(half_life, 1.0)  # Min 1 dönem
            
        except Exception as e:
            logger.warning(f"Half-life hesabı hatası: {e}")
            return np.inf
    
    def scan_universe(
        self, price_data: Dict[str, np.ndarray], top_n: int = 10
    ) -> List[CointegrationResult]:
        """
        Varlık evreni taraması: Tüm pair kombinasyonlarını test et.
        
        Args:
            price_data: {ticker: price_array}
            top_n: En iyi kaç sonuç döndürülsün
            
        Returns:
            Kointegre çiftleri score'a göre sıralı liste
        """
        if len(price_data) < 2:
            logger.warning("En azından 2 varlık gereklidir")
            return []
        
        results: List[CointegrationResult] = []
        tickers = list(price_data.keys())
        n_pairs = len(tickers) * (len(tickers) - 1) // 2
        
        logger.info(f"Tarama başlatılıyor: {len(tickers)} varlık, {n_pairs} çift")
        
        for i, ticker_x in enumerate(tickers):
            for ticker_y in tickers[i+1:]:
                price_x = price_data[ticker_x]
                price_y = price_data[ticker_y]
                
                result = self.test_cointegration(price_x, price_y)
                result.pair_x = ticker_x
                result.pair_y = ticker_y
                
                if result.is_cointegrated:
                    results.append(result)
        
        # Score'a göre sırala (düşük pvalue ve yüksek half-life olmayan)
        results.sort(
            key=lambda x: (x.coint_pvalue, x.half_life),
            reverse=False
        )
        
        logger.info(f"Bulundu: {len(results)} kointegre çift")
        for i, res in enumerate(results[:top_n], 1):
            logger.info(f"  {i}. {res}")
        
        return results[:top_n]
