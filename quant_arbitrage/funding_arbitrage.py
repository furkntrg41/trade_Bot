"""
Funding Rate Arbitrage Module
===============================
Spot + Futures market-neutral arbitrage.
Risksiz getiri: Binance'ın ödediği funding fee'si.

Author: Quant Team
Date: 2026-02-01
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class FundingStatus(Enum):
    """Funding arbitraj durumu"""
    NO_OPPORTUNITY = 0
    POSITIVE_FUNDING = 1   # Longlar ödüyor (Short fırsatı)
    NEGATIVE_FUNDING = -1  # Shortlar ödüyor (Long fırsatı)


@dataclass
class FundingArbitrage:
    """Funding arbitraj işlem detayları"""
    symbol: str
    entry_timestamp: datetime
    spot_entry_price: float
    futures_entry_price: float
    position_size: float
    
    current_spot_price: float
    current_futures_price: float
    
    cumulative_funding_paid: float
    
    @property
    def pnl(self) -> float:
        """Unrealized P&L"""
        # Delta-neutral olduğu için fiyat değişimi yoktur
        # Kâr sadece funding fee'si
        return self.cumulative_funding_paid
    
    def __str__(self) -> str:
        entry_days = (datetime.utcnow() - self.entry_timestamp).days
        return (
            f"{self.symbol} | Entry: {self.entry_timestamp} ({entry_days}d ago) | "
            f"Funding PnL: {self.pnl:.4f} | "
            f"Spot Price: {self.current_spot_price:.2f} | "
            f"Futures Price: {self.current_futures_price:.2f}"
        )


class FundingRateMonitor:
    """
    Binance Futures funding rate izleme ve arbitraj analizi.
    
    Prensip:
    --------
    Spot ve Futures piyasaları arasında fiyat farkından risksiz getiri sağlama.
    
    Senaryolar:
    1. Yüksek Pozitif Funding (>0.05%): Longlar ödüyor
       → Spot satın al, Futures short et
       → Hiçbir fiyat riski yok (delta-neutral)
       → Funding fee'si senin kârı
    
    2. Yüksek Negatif Funding (<-0.05%): Shortlar ödüyor
       → Futures long et, spot borrow + short
       → Yine delta-neutral
    """
    
    def __init__(
        self,
        annualized_funding_threshold: float = 0.05,  # %5 yıllık
        min_position_size: float = 0.1,  # Min 0.1 BTC
        max_spread_tolerance: float = 0.001,  # %0.1 spread tolerance
    ):
        """
        Args:
            annualized_funding_threshold: Entry için gerekli yıllık funding rate
            min_position_size: Minimum position size
            max_spread_tolerance: Max acceptable bid-ask spread
        """
        self.annualized_funding_threshold = annualized_funding_threshold
        self.min_position_size = min_position_size
        self.max_spread_tolerance = max_spread_tolerance
        
        self.active_positions: dict[str, FundingArbitrage] = {}
        self.funding_history: dict[str, list[tuple[datetime, float]]] = {}
    
    def check_opportunity(
        self,
        symbol: str,
        current_funding_rate: float,  # %
        spot_bid: float,
        spot_ask: float,
        futures_bid: float,
        futures_ask: float,
    ) -> FundingStatus:
        """
        Arbitraj fırsatını kontrol et.
        
        Args:
            symbol: Örn. "BTC"
            current_funding_rate: Mevcut funding rate (%)
            spot_bid/ask: Spot order book
            futures_bid/ask: Futures order book
            
        Returns:
            FundingStatus
        """
        # Funding rate'i yıllıklandır
        # Binance funding: 8 saatte bir ödendiği için
        # Yıllık = (rate) × (365 / (8/24)) × 100 = rate × 1095
        annualized = abs(current_funding_rate) * 1095
        
        logger.debug(
            f"{symbol} Funding: {current_funding_rate:.4f}% "
            f"(Annualized: {annualized:.2f}%)"
        )
        
        if annualized < self.annualized_funding_threshold:
            return FundingStatus.NO_OPPORTUNITY
        
        # Spread kontrol
        spot_mid = (spot_bid + spot_ask) / 2
        futures_mid = (futures_bid + futures_ask) / 2
        spot_spread = (spot_ask - spot_bid) / spot_mid
        futures_spread = (futures_ask - futures_bid) / futures_mid
        
        if spot_spread > self.max_spread_tolerance:
            logger.warning(f"{symbol} spot spread çok yüksek: {spot_spread:.4f}")
            return FundingStatus.NO_OPPORTUNITY
        
        if futures_spread > self.max_spread_tolerance:
            logger.warning(f"{symbol} futures spread çok yüksek: {futures_spread:.4f}")
            return FundingStatus.NO_OPPORTUNITY
        
        # Yönü belirle
        if current_funding_rate > 0:
            return FundingStatus.POSITIVE_FUNDING  # Longlar ödüyor
        else:
            return FundingStatus.NEGATIVE_FUNDING  # Shortlar ödüyor
    
    def open_position(
        self,
        symbol: str,
        spot_entry_price: float,
        futures_entry_price: float,
        position_size: float,
    ) -> bool:
        """
        Arbitraj pozisyonu aç.
        
        Args:
            symbol: Sembol
            spot_entry_price: Spot giriş fiyatı
            futures_entry_price: Futures giriş fiyatı
            position_size: Pozisyon büyüklüğü (coin cinsinden)
            
        Returns:
            Başarılı mı
        """
        if position_size < self.min_position_size:
            logger.warning(
                f"Position size çok küçük: {position_size} "
                f"< {self.min_position_size}"
            )
            return False
        
        if symbol in self.active_positions:
            logger.warning(f"{symbol} zaten aktif pozisyon var")
            return False
        
        position = FundingArbitrage(
            symbol=symbol,
            entry_timestamp=datetime.utcnow(),
            spot_entry_price=spot_entry_price,
            futures_entry_price=futures_entry_price,
            position_size=position_size,
            current_spot_price=spot_entry_price,
            current_futures_price=futures_entry_price,
            cumulative_funding_paid=0.0,
        )
        
        self.active_positions[symbol] = position
        logger.info(f"Funding arbitraj pozisyonu açıldı: {position}")
        return True
    
    def update_position(
        self,
        symbol: str,
        current_spot_price: float,
        current_futures_price: float,
        funding_payment_received: float,  # Bu candle'da alınan funding
    ) -> Optional[FundingArbitrage]:
        """
        Pozisyonu güncelle.
        
        Args:
            symbol: Sembol
            current_spot_price: Mevcut spot fiyatı
            current_futures_price: Mevcut futures fiyatı
            funding_payment_received: Received funding (usually negative if we're short)
            
        Returns:
            Güncellenmiş pozisyon veya None
        """
        if symbol not in self.active_positions:
            return None
        
        position = self.active_positions[symbol]
        position.current_spot_price = current_spot_price
        position.current_futures_price = current_futures_price
        position.cumulative_funding_paid += funding_payment_received
        
        return position
    
    def close_position(self, symbol: str, close_reason: str = "Manual") -> Optional[FundingArbitrage]:
        """
        Pozisyonu kapat.
        
        Args:
            symbol: Sembol
            close_reason: Kapanış sebebi
            
        Returns:
            Kapatılan pozisyon
        """
        if symbol not in self.active_positions:
            logger.warning(f"{symbol} pozisyonu bulunamadı")
            return None
        
        position = self.active_positions.pop(symbol)
        
        holding_days = (datetime.utcnow() - position.entry_timestamp).days
        daily_funding = (
            position.cumulative_funding_paid / max(holding_days, 1)
            if holding_days > 0 else position.cumulative_funding_paid
        )
        
        logger.info(
            f"Funding arbitraj pozisyonu kapatıldı: {symbol} | "
            f"Total Funding: {position.pnl:.4f} | "
            f"Daily Avg: {daily_funding:.4f} | "
            f"Reason: {close_reason}"
        )
        
        return position
    
    def calculate_breakeven_funding(
        self,
        spot_bid: float,
        spot_ask: float,
        futures_bid: float,
        futures_ask: float,
        borrow_fee_daily: float = 0.0001,  # %0.01 per day
        trading_fee: float = 0.0002,  # %0.02 per trade
    ) -> float:
        """
        Breakeven funding rate hesapla.
        
        Maliyetler:
        1. Trading fees (giriş/çıkış)
        2. Borrow fees (spot short için)
        3. Spread loss (entry)
        
        Args:
            spot_bid/ask: Spot order book
            futures_bid/ask: Futures order book
            borrow_fee_daily: Günlük borrowing fee (%)
            trading_fee: Trading fee (per side)
            
        Returns:
            Breakeven annualized funding rate (%)
        """
        spot_mid = (spot_bid + spot_ask) / 2
        futures_mid = (futures_bid + futures_ask) / 2
        
        # Giriş maliyeti
        entry_cost = (
            trading_fee * 2 +  # Entry + exit
            (spot_ask - futures_bid) / futures_mid  # Spread
        )
        
        # Günlük borrow fee'si
        daily_cost = borrow_fee_daily
        
        # 30 günlük holding
        total_cost = entry_cost + (daily_cost * 30)
        
        # Annualize (funding 8 saatte bir ödendiği için)
        annualized_breakeven = (total_cost / 30) * 1095 * 100
        
        logger.debug(f"Breakeven funding: {annualized_breakeven:.4f}%")
        return annualized_breakeven
    
    def get_active_pnl(self) -> dict[str, float]:
        """Tüm aktif pozisyonların PnL'sini döndür"""
        return {
            symbol: position.pnl
            for symbol, position in self.active_positions.items()
        }
    
    def get_summary(self) -> str:
        """Özet rapor"""
        if not self.active_positions:
            return "No active funding arbitrage positions"
        
        total_pnl = sum(pos.pnl for pos in self.active_positions.values())
        
        summary = f"Active Positions: {len(self.active_positions)}\n"
        summary += f"Total Funding PnL: {total_pnl:.4f}\n"
        summary += "\nPositions:\n"
        
        for symbol, position in self.active_positions.items():
            summary += f"  {position}\n"
        
        return summary
