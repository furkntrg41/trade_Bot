"""
Risk Management & Position Sizing
====================================
Kelly Criterion, Delta Hedging, Position Limits

Author: Quant Team
Date: 2026-02-01
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Position yönü"""
    LONG = 1
    SHORT = -1
    FLAT = 0


@dataclass
class RiskMetrics:
    """Risk metrikleri"""
    notional_value: float  # Position değeri (USDT)
    delta: float  # Spot fiyata karşı sensitivity
    vega: float  # Volatiliteye karşı sensitivity
    theta: float  # Time decay
    max_loss: float  # Stop loss kaybı
    var_95: float  # Value at Risk %95


class RiskManager:
    """
    Position sizing ve risk yönetimi.
    
    Kurallar (Strict):
    1. Single trade max loss: Account'un %1'i
    2. Total delta exposure: Limitli (neutral'e yakın)
    3. Volatilité screening: IV rank/percentile kontrol
    4. Concentration limit: Single symbol max %5
    """
    
    def __init__(
        self,
        account_equity: float,
        max_loss_per_trade: float = 0.01,  # %1
        max_total_delta: float = 0.1,  # %10
        max_concentration: float = 0.05,  # %5 per symbol
        kelly_fraction: float = 0.25,  # Fractional Kelly (safer)
    ):
        """
        Args:
            account_equity: Hesap öz sermayesi (USDT)
            max_loss_per_trade: Single trade için max loss
            max_total_delta: Portfolio delta limit
            max_concentration: Single symbol concentration limit
            kelly_fraction: Kelly criterion fraction (0.25 = quarter Kelly)
        """
        self.account_equity = account_equity
        self.max_loss_per_trade = max_loss_per_trade * account_equity
        self.max_total_delta = max_total_delta
        self.max_concentration = max_concentration
        self.kelly_fraction = kelly_fraction
        
        self.open_positions: dict[str, dict] = {}
        self.total_delta = 0.0
        
    def calculate_kelly_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> float:
        """
        Kelly Criterion ile position size hesapla.
        
        Kelly % = (bp - q) / b
        b = odds (avg_win / avg_loss)
        p = win probability
        q = 1 - p
        
        Args:
            win_rate: Kazanma olasılığı (0-1)
            avg_win: Ortalama kazanç
            avg_loss: Ortalama kayıp
            
        Returns:
            Kelly fraction (0-1 arası önerilen risk fraction)
        """
        if avg_loss <= 0:
            return 0.0
        
        q = 1 - win_rate  # Kaybetme olasılığı
        b = avg_win / avg_loss  # Odds
        
        if b * win_rate - q <= 0:
            return 0.0
        
        kelly_pct = (b * win_rate - q) / b
        
        # Fractional Kelly (daha güvenli)
        position_size = kelly_pct * self.kelly_fraction
        position_size = max(0, min(position_size, 0.25))  # Cap at 25%
        
        logger.info(
            f"Kelly: win_rate={win_rate:.1%}, kelly_pct={kelly_pct:.2%}, "
            f"position_size={position_size:.2%}"
        )
        
        return position_size
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        volatility_adjusted: bool = True,
        volatility: float = 0.3,  # 30% yıllık
    ) -> float:
        """
        Position size hesabı - Risk parity yaklaşımı.
        
        Size = MaxLoss / Distance to Stop Loss
        
        Args:
            symbol: Sembol
            entry_price: Giriş fiyatı
            stop_loss_price: Stop loss fiyatı
            volatility_adjusted: Volatiliteye göre scale et
            volatility: Yıllık volatilite
            
        Returns:
            Position size (USDT cinsinden)
        """
        # Stop loss uzaklığı
        distance_to_sl = abs(entry_price - stop_loss_price) / entry_price
        
        if distance_to_sl < 0.0001:  # Çok yakın
            logger.warning("Stop loss çok yakın")
            return 0.0
        
        # Base position size
        position_size = self.max_loss_per_trade / distance_to_sl
        
        # Volatilite adjustment (yüksek volatilite = küçük pozisyon)
        if volatility_adjusted:
            volatility_scale = 0.2 / volatility  # Normalize to 20% vol
            volatility_scale = max(0.5, min(volatility_scale, 2.0))  # Cap
            position_size *= volatility_scale
        
        # Concentration limit kontrol
        max_allowed = self.account_equity * self.max_concentration
        position_size = min(position_size, max_allowed)
        
        # Delta kontrol
        if self.total_delta >= self.max_total_delta:
            logger.warning("Delta limit aşıldı, position size sınırlandırıldı")
            position_size *= 0.5
        
        logger.info(
            f"{symbol} position size: {position_size:.2f} USDT "
            f"({position_size/self.account_equity*100:.1f}% of equity)"
        )
        
        return position_size
    
    def check_constraints(
        self,
        symbol: str,
        new_delta: float,
        new_notional: float,
    ) -> Tuple[bool, str]:
        """
        Position açılabilir mi kontrol et.
        
        Returns:
            (allowed, reason)
        """
        # Concentration check
        if new_notional / self.account_equity > self.max_concentration:
            return False, f"Concentration limit aşılır ({new_notional/self.account_equity:.1%})"
        
        # Delta check
        new_total_delta = self.total_delta + new_delta
        if abs(new_total_delta) > self.max_total_delta:
            return False, f"Delta limit aşılır ({abs(new_total_delta):.1%})"
        
        return True, "OK"
    
    def add_position(
        self,
        symbol: str,
        side: PositionSide,
        size: float,
        entry_price: float,
        delta: float = 1.0,  # Pairs trading için <1
    ) -> bool:
        """
        Pozisyonu register et.
        
        Args:
            symbol: Sembol
            side: LONG / SHORT
            size: Pozisyon büyüklüğü (USDT)
            entry_price: Giriş fiyatı
            delta: Delta sensitivity (default 1.0 = spot)
            
        Returns:
            Başarılı mı
        """
        if symbol in self.open_positions:
            logger.warning(f"{symbol} zaten açık pozisyon var")
            return False
        
        # Constraints kontrol
        notional = size
        position_delta = delta * side.value
        allowed, reason = self.check_constraints(symbol, position_delta, notional)
        
        if not allowed:
            logger.warning(f"Position açılamadı: {reason}")
            return False
        
        self.open_positions[symbol] = {
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "delta": delta,
            "notional": notional,
        }
        
        self.total_delta += position_delta
        
        logger.info(
            f"Position added: {symbol} {side.name} {size:.2f} USDT "
            f"@ {entry_price:.2f}, total_delta={self.total_delta:.2f}"
        )
        
        return True
    
    def remove_position(self, symbol: str, exit_price: float) -> Optional[dict]:
        """
        Pozisyonu kapat.
        
        Returns:
            Kapatılan pozisyon detayları veya None
        """
        if symbol not in self.open_positions:
            logger.warning(f"{symbol} pozisyonu bulunamadı")
            return None
        
        position = self.open_positions.pop(symbol)
        
        # PnL hesapla
        entry_price = position["entry_price"]
        size = position["size"]
        side = position["side"]
        
        price_change = (exit_price - entry_price) / entry_price
        pnl = size * price_change * side.value
        
        # Delta güncelle
        self.total_delta -= position["delta"] * side.value
        
        logger.info(
            f"Position closed: {symbol} | "
            f"Entry: {entry_price:.2f}, Exit: {exit_price:.2f} | "
            f"PnL: {pnl:.2f} USDT ({pnl/size*100:.2f}%)"
        )
        
        position["pnl"] = pnl
        position["exit_price"] = exit_price
        
        return position
    
    def get_portfolio_delta(self) -> float:
        """Toplam portfolio delta'sını döndür"""
        return self.total_delta
    
    def get_leverage(self) -> float:
        """Kullanılan leverage (notional / equity)"""
        total_notional = sum(pos["notional"] for pos in self.open_positions.values())
        return total_notional / self.account_equity
    
    def get_summary(self) -> str:
        """Risk yönetimi özeti"""
        total_notional = sum(pos["notional"] for pos in self.open_positions.values())
        
        summary = f"Risk Management Summary\n"
        summary += f"  Account Equity: {self.account_equity:.2f} USDT\n"
        summary += f"  Open Positions: {len(self.open_positions)}\n"
        summary += f"  Total Notional: {total_notional:.2f} USDT ({total_notional/self.account_equity:.1%})\n"
        summary += f"  Portfolio Delta: {self.total_delta:.2f}\n"
        summary += f"  Leverage: {self.get_leverage():.2f}x\n"
        summary += f"  Max Loss per Trade: {self.max_loss_per_trade:.2f} USDT\n"
        
        return summary
