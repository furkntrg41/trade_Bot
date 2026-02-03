"""
Pairs Trading Sinyal Üretim Modülü
====================================
Z-Score hesabı ve Mean Reversion sinyalleri.
Canlı spread verisi üzerinde çalışır.

Author: Quant Team
Date: 2026-02-01
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional
import numpy as np
from scipy import signal


logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Sinyal türleri"""
    NO_SIGNAL = 0
    LONG_SPREAD = 1        # Y long, X short (Z < -2)
    SHORT_SPREAD = -1      # Y short, X long (Z > 2)
    EXIT_LONG = 2          # Long spread pozisyonundan çık
    EXIT_SHORT = -2        # Short spread pozisyonundan çık


@dataclass
class SpreadSignal:
    """Spread sinyal çıktısı"""
    timestamp: int
    z_score: float
    spread_value: float
    signal: SignalType
    confidence: float  # 0-1 arası
    
    def __str__(self) -> str:
        signal_name = {
            SignalType.NO_SIGNAL: "NONE",
            SignalType.LONG_SPREAD: "LONG_SPREAD",
            SignalType.SHORT_SPREAD: "SHORT_SPREAD",
            SignalType.EXIT_LONG: "EXIT_LONG",
            SignalType.EXIT_SHORT: "EXIT_SHORT",
        }.get(self.signal, "UNKNOWN")
        
        return (
            f"t={self.timestamp} | Spread={self.spread_value:.6f} | "
            f"Z={self.z_score:.2f} | Signal={signal_name} | "
            f"Confidence={self.confidence:.2f}"
        )


class PairsSpreadCalculator:
    """
    Canlı Pairs Trading Spread ve Z-Score hesaplayıcısı.
    
    Prensip:
    --------
    Spread_t = log(Y_t) - β*log(X_t)
    Z_t = (Spread_t - μ_rolling) / σ_rolling
    
    Entry Sinyalleri:
    - Z > +2σ: Spread çok açıldı, mean'e dönecek → X'i long, Y'yi short et (SHORT_SPREAD)
    - Z < -2σ: Spread çok kapandı → X'i short, Y'yi long et (LONG_SPREAD)
    
    Exit Sinyalleri:
    - Z → 0: Mean reversion tamamlandı
    """
    
    def __init__(
        self,
        hedge_ratio: float,
        lookback_periods: int = 252,  # ~1 yıl 5m candle
        z_score_threshold: float = 2.0,
        z_score_exit: float = 0.5,  # Exit threshold
        min_samples: int = 20,
    ):
        """
        Args:
            hedge_ratio: Hedge ratio β (kointegrasyon analizinden)
            lookback_periods: Rolling istatistikleri hesaplamak için geçmiş dönem
            z_score_threshold: Entry triggerı için threshold (σ cinsinden)
            z_score_exit: Exit triggerı için threshold
            min_samples: Z-score hesabı için minimum örnek sayısı
        """
        self.hedge_ratio = hedge_ratio
        self.lookback_periods = lookback_periods
        self.z_score_threshold = z_score_threshold
        self.z_score_exit = z_score_exit
        self.min_samples = min_samples
        
        # Circular buffer (memory efficient)
        self.spread_buffer = np.zeros(lookback_periods)
        self.buffer_idx = 0
        self.buffer_full = False
        self.spread_count = 0
        
        self._previous_signal: Optional[SignalType] = None
        self._entry_z_score: Optional[float] = None
        
    def add_prices(self, price_x: float, price_y: float) -> SpreadSignal:
        """
        Yeni fiyat verisi ekle ve sinyal üret.
        
        Args:
            price_x: Varlık X'in cari fiyatı
            price_y: Varlık Y'nin cari fiyatı
            
        Returns:
            SpreadSignal
        """
        # Spread hesapla
        log_x = np.log(price_x)
        log_y = np.log(price_y)
        spread = log_y - self.hedge_ratio * log_x
        
        # Buffer'a ekle
        self.spread_buffer[self.buffer_idx] = spread
        self.buffer_idx = (self.buffer_idx + 1) % self.lookback_periods
        
        if not self.buffer_full and self.buffer_idx == 0:
            self.buffer_full = True
        
        self.spread_count += 1
        timestamp = int(self.spread_count)
        
        # Z-score hesapla
        z_score, spread_mean, spread_std = self._calculate_z_score()
        
        if z_score is None:
            return SpreadSignal(
                timestamp=timestamp,
                z_score=np.nan,
                spread_value=spread,
                signal=SignalType.NO_SIGNAL,
                confidence=0.0
            )
        
        # Sinyal üret
        signal_type, confidence = self._generate_signal(z_score, spread_mean, spread_std)
        
        # Logging
        logger.debug(
            f"Spread calc: spread={spread:.6f}, Z={z_score:.2f}, "
            f"μ={spread_mean:.6f}, σ={spread_std:.6f}"
        )
        
        return SpreadSignal(
            timestamp=timestamp,
            z_score=z_score,
            spread_value=spread,
            signal=signal_type,
            confidence=confidence
        )
    
    def _calculate_z_score(self) -> Tuple[Optional[float], float, float]:
        """
        Z-score hesapla: Z = (x - μ) / σ
        
        Returns:
            (z_score, mean, std)
        """
        # Dolu mu kontrol
        if self.buffer_full:
            data = self.spread_buffer
        else:
            data = self.spread_buffer[:self.buffer_idx]
        
        if len(data) < self.min_samples:
            return None, 0.0, 1.0
        
        mean = np.mean(data)
        std = np.std(data)
        
        if std < 1e-8:  # Sabit spread?
            return None, mean, 1.0
        
        current_spread = self.spread_buffer[(self.buffer_idx - 1) % self.lookback_periods]
        z_score = (current_spread - mean) / std
        
        return z_score, mean, std
    
    def _generate_signal(
        self, z_score: float, spread_mean: float, spread_std: float
    ) -> Tuple[SignalType, float]:
        """
        Z-score'a göre sinyal üret.
        
        Entry:
        - Z > +2: Short spread (Y short, X long)
        - Z < -2: Long spread (Y long, X short)
        
        Exit:
        - Mean reverting (Z → 0)
        
        Args:
            z_score: Z-score değeri
            spread_mean: Rolling mean
            spread_std: Rolling std
            
        Returns:
            (SignalType, confidence)
        """
        confidence = min(abs(z_score) / self.z_score_threshold, 1.0)
        
        # Exit sinyalleri (pozisyon varsa)
        if self._previous_signal == SignalType.LONG_SPREAD:
            if z_score > self.z_score_exit:
                self._previous_signal = None
                self._entry_z_score = None
                return SignalType.EXIT_LONG, confidence
        
        elif self._previous_signal == SignalType.SHORT_SPREAD:
            if z_score < -self.z_score_exit:
                self._previous_signal = None
                self._entry_z_score = None
                return SignalType.EXIT_SHORT, confidence
        
        # Entry sinyalleri (pozisyon yoksa)
        if self._previous_signal is None:
            if z_score > self.z_score_threshold:
                self._previous_signal = SignalType.SHORT_SPREAD
                self._entry_z_score = z_score
                return SignalType.SHORT_SPREAD, confidence
            
            elif z_score < -self.z_score_threshold:
                self._previous_signal = SignalType.LONG_SPREAD
                self._entry_z_score = z_score
                return SignalType.LONG_SPREAD, confidence
        
        return SignalType.NO_SIGNAL, 0.0
    
    def reset(self) -> None:
        """Hesaplayıcıyı sıfırla"""
        self.spread_buffer.fill(0)
        self.buffer_idx = 0
        self.buffer_full = False
        self.spread_count = 0
        self._previous_signal = None
        self._entry_z_score = None
        logger.info("Spread calculator reset")


class KalmanFilterHedgeRatio:
    """
    Kalman Filtresi ile dinamik Hedge Ratio güncelleme.
    
    Prensip: Hedge ratio zaman içinde değişir. OLS yerine Kalman Filtresi
    kullanarak daha responsive bir tahmin elde ederiz.
    """
    
    def __init__(
        self,
        initial_hedge_ratio: float,
        process_noise: float = 1e-5,
        measurement_noise: float = 1e-4,
    ):
        """
        Args:
            initial_hedge_ratio: Başlangıç β değeri (OLS'den)
            process_noise: Q matrisi (model belirsizliği)
            measurement_noise: R matrisi (ölçüm belirsizliği)
        """
        self.beta = initial_hedge_ratio
        self.P = 1.0  # Tahmin hatasının kovaryansı
        self.Q = process_noise
        self.R = measurement_noise
    
    def update(self, log_price_x: float, log_price_y: float) -> float:
        """
        Yeni ölçüm ile Kalman filterini güncelle.
        
        Ölçüm modeli: log(Y) = β*log(X) + noise
        
        Args:
            log_price_x: X'in log fiyatı
            log_price_y: Y'nin log fiyatı
            
        Returns:
            Güncellenmiş hedge ratio
        """
        # Prediction step
        beta_pred = self.beta
        P_pred = self.P + self.Q
        
        # Measurement step
        innovation = log_price_y - beta_pred * log_price_x
        innovation_var = P_pred * (log_price_x ** 2) + self.R
        
        if innovation_var < 1e-10:
            return self.beta
        
        # Kalman gain
        K = P_pred * log_price_x / innovation_var
        
        # Update
        self.beta = beta_pred + K * innovation
        self.P = (1 - K * log_price_x) * P_pred
        
        return self.beta


class MultiPairManager:
    """
    Çoklu pairs trading yönetimi.
    Her pair için ayrı SpreadCalculator instance'ı tutacak.
    """
    
    def __init__(self):
        self.pairs: dict[str, PairsSpreadCalculator] = {}
        self.kalman_filters: dict[str, KalmanFilterHedgeRatio] = {}
    
    def register_pair(
        self,
        pair_id: str,
        hedge_ratio: float,
        lookback_periods: int = 252,
    ) -> None:
        """Yeni pair kaydet"""
        self.pairs[pair_id] = PairsSpreadCalculator(
            hedge_ratio=hedge_ratio,
            lookback_periods=lookback_periods
        )
        self.kalman_filters[pair_id] = KalmanFilterHedgeRatio(
            initial_hedge_ratio=hedge_ratio
        )
        logger.info(f"Pair registered: {pair_id}, β={hedge_ratio:.4f}")
    
    def update_pair(
        self, pair_id: str, price_x: float, price_y: float
    ) -> Optional[SpreadSignal]:
        """Pair'i güncelle"""
        if pair_id not in self.pairs:
            logger.warning(f"Unknown pair: {pair_id}")
            return None
        
        # Kalman filter ile hedge ratio güncelle
        log_x = np.log(price_x)
        log_y = np.log(price_y)
        updated_beta = self.kalman_filters[pair_id].update(log_x, log_y)
        
        # Spread calculator'ı güncelle
        self.pairs[pair_id].hedge_ratio = updated_beta
        signal = self.pairs[pair_id].add_prices(price_x, price_y)
        
        return signal
    
    def get_all_signals(
        self
    ) -> dict[str, SpreadSignal]:
        """Tüm pair'ler için son sinyalleri dön"""
        # Her pair'in buffer'ının son değerini al
        signals = {}
        for pair_id, calculator in self.pairs.items():
            if calculator.spread_count > 0:
                last_spread = calculator.spread_buffer[
                    (calculator.buffer_idx - 1) % calculator.lookback_periods
                ]
                z_score, _, _ = calculator._calculate_z_score()
                if z_score is not None:
                    signals[pair_id] = z_score
        return signals
