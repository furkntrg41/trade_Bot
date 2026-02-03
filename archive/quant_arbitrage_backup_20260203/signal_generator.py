"""
Signal Generator - WebSocket'ten Real-time Z-Score Sinyalleri Üret
===================================================================
Canlı Binance WebSocket'ten aggTrade verisi alarak,
kointegre edilmiş pair'ler için Z-score hesaplayan
ve BUY/SELL sinyalleri üreten generator.

Event-driven, async/await, type-safe architecture.

Author: Quant Team
Date: 2026-02-01
"""

import asyncio
import logging
from typing import Dict, List, Callable, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

import numpy as np
import pandas as pd

from .websocket_provider import BinanceWebSocketProvider, TickData
from .spread_calculator import PairsSpreadCalculator, SpreadSignal, SignalType
from .config import get_config, Config


logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    """Signal gücü"""
    WEAK = 0.5
    NORMAL = 1.0
    STRONG = 1.5
    EXTREME = 2.0


@dataclass
class TradingSignal:
    """
    Trading sinyali dataclass
    
    Attributes:
        timestamp: İşlem zamanı
        pair_x: Base pair (BTC)
        pair_y: Quote pair (ETH)
        signal_type: BUY/SELL/NEUTRAL
        z_score: Standart sapma sayısı
        confidence: 0-1 arası güven
        strength: Signal gücü multiplier
        suggested_position_size: Önerilen position boyutu (%)
        stop_loss_z: Stop loss Z-score seviyesi
        take_profit_z: Take profit Z-score seviyesi
    """
    timestamp: datetime
    pair_x: str
    pair_y: str
    signal_type: SignalType
    z_score: float
    confidence: float
    strength: SignalStrength
    suggested_position_size: float
    stop_loss_z: float
    take_profit_z: float
    
    def __str__(self) -> str:
        """Readable string representation"""
        emoji = {
            SignalType.BUY: "🟢",
            SignalType.SELL: "🔴",
            SignalType.EXIT: "🟡",
        }.get(self.signal_type, "⚪")
        
        return (
            f"{emoji} {self.signal_type.name} {self.pair_x}/{self.pair_y} | "
            f"Z={self.z_score:.2f} | "
            f"Conf={self.confidence:.1%} | "
            f"Size={self.suggested_position_size:.1%} | "
            f"@{self.timestamp.strftime('%H:%M:%S')}"
        )


class SignalGenerator:
    """
    Real-time trading signals üreten generator.
    
    Workflow:
    1. WebSocket'ten tick verisi al
    2. Kointegre pair'ler için Z-score hesapla
    3. Threshold'u geçerse signal üret
    4. Registered callback'leri çağır
    
    Type-safe, async, error-handled.
    """
    
    def __init__(
        self,
        pair_x: str,
        pair_y: str,
        hedge_ratio: float,
        config: Optional[Config] = None,
    ):
        """
        Args:
            pair_x: İlk pair sembolü (BTC)
            pair_y: İkinci pair sembolü (ETH)
            hedge_ratio: Regression β coefficienti
            config: Configuration (default: get_config())
        """
        self.config = config or get_config()
        self.pair_x = pair_x
        self.pair_y = pair_y
        self.hedge_ratio = hedge_ratio
        
        # Spread calculator (Z-score için)
        self.spread_calc = PairsSpreadCalculator(
            lookback_window=self.config.signal.lookback_bars,
            hedge_ratio=hedge_ratio,
        )
        
        # WebSocket provider
        self.ws_provider = BinanceWebSocketProvider(
            exchange=self.config.data.exchange,
            enable_order_book=self.config.signal.use_order_book,
        )
        
        # Signal callbacks
        self.signal_callbacks: List[Callable[[TradingSignal], None]] = []
        
        # Price history (debugging, monitoring)
        self.price_history: Dict[str, List[float]] = {
            self.pair_x: [],
            self.pair_y: [],
        }
        
        # Last signal (duplicate detection)
        self.last_signal: Optional[TradingSignal] = None
        self.last_signal_time = datetime.utcnow()
        
    def register_signal_callback(
        self,
        callback: Callable[[TradingSignal], None],
    ) -> None:
        """
        Signal callback'i register et.
        
        Args:
            callback: async def callback(signal: TradingSignal) -> None
        """
        self.signal_callbacks.append(callback)
        logger.info(f"✅ Signal callback registered: {callback.__name__}")
    
    async def on_price_update(self, tick: TickData) -> None:
        """
        WebSocket'ten price update gelirse çalış.
        
        Args:
            tick: Tick verisi
        """
        try:
            # Pair'i belirle
            if tick.symbol == self.pair_x:
                pair = self.pair_x
            elif tick.symbol == self.pair_y:
                pair = self.pair_y
            else:
                return  # İlgilendiğimiz pair değil
            
            # Use mid price (average of bid/ask)
            price = tick.mid
            
            # Price history'e ekle
            self.price_history[pair].append(price)
            if len(self.price_history[pair]) > 10000:
                self.price_history[pair].pop(0)  # Memory leak prevention
            
            # Z-score hesapla
            spread_signal = self.spread_calc.add_prices(
                price if pair == self.pair_x else None,
                price if pair == self.pair_y else None,
            )
            
            if spread_signal is None:
                return  # Henüz yeterli veri yok
            
            # Signal oluştur
            signal = self._create_signal(
                spread_signal=spread_signal,
                timestamp=tick.timestamp,
            )
            
            if signal is None:
                return  # No actionable signal
            
            # Duplicate detection
            if self._is_duplicate_signal(signal):
                logger.debug(f"⏭️ Duplicate signal suppressed")
                return
            
            # Signal'ı kayıt et
            self.last_signal = signal
            self.last_signal_time = datetime.utcnow()
            
            # Callbacks'ı çağır
            await self._emit_signal(signal)
            
        except Exception as e:
            logger.error(f"❌ Price update hatası: {e}", exc_info=True)
    
    def _create_signal(
        self,
        spread_signal: SpreadSignal,
        timestamp: datetime,
    ) -> Optional[TradingSignal]:
        """
        Spread signal'dan trading signal oluştur.
        
        Args:
            spread_signal: SpreadSignal dataclass
            timestamp: Update zamanı
            
        Returns:
            TradingSignal veya None
        """
        z_score = spread_signal.z_score
        signal_type = spread_signal.signal_type
        confidence = spread_signal.confidence
        
        # Threshold kontrol
        entry_threshold = self.config.signal.entry_threshold
        exit_threshold = self.config.signal.exit_threshold
        
        # Signal strength belirle
        abs_z = abs(z_score)
        
        if abs_z >= entry_threshold * 1.5:
            strength = SignalStrength.EXTREME
            position_size = 1.0  # 100%
        elif abs_z >= entry_threshold:
            strength = SignalStrength.STRONG
            position_size = 0.75  # 75%
        elif abs_z >= exit_threshold:
            strength = SignalStrength.NORMAL
            position_size = 0.5  # 50%
        else:
            return None  # No signal
        
        # Stop loss ve take profit
        stop_loss_z = self.config.signal.stop_loss_threshold
        take_profit_z = 0.0  # Mean reversion, spread=0'da kapatıyoruz
        
        signal = TradingSignal(
            timestamp=timestamp,
            pair_x=self.pair_x,
            pair_y=self.pair_y,
            signal_type=signal_type,
            z_score=z_score,
            confidence=confidence,
            strength=strength,
            suggested_position_size=position_size,
            stop_loss_z=stop_loss_z,
            take_profit_z=take_profit_z,
        )
        
        return signal
    
    def _is_duplicate_signal(self, new_signal: TradingSignal) -> bool:
        """
        Son sinyatle aynı mı kontrol et (duplicate suppression)
        
        Args:
            new_signal: Yeni signal
            
        Returns:
            Duplicate mi
        """
        if self.last_signal is None:
            return False
        
        # Aynı tip ve 30 saniye içinde gelmiş mi?
        time_diff = (new_signal.timestamp - self.last_signal_time).total_seconds()
        
        is_duplicate = (
            self.last_signal.signal_type == new_signal.signal_type
            and time_diff < self.config.signal.duplicate_suppression_seconds
        )
        
        return is_duplicate
    
    async def _emit_signal(self, signal: TradingSignal) -> None:
        """
        Signal'ı tüm callbacks'a gönder.
        
        Args:
            signal: TradingSignal instance
        """
        logger.info(f"🚀 SIGNAL EMITTED: {signal}")
        
        tasks = []
        for callback in self.signal_callbacks:
            if asyncio.iscoroutinefunction(callback):
                tasks.append(callback(signal))
            else:
                callback(signal)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def start(self) -> None:
        """
        Generator'ı başlat (WebSocket dinlemesi başlat)
        """
        logger.info(f"🟢 Signal generator başlatıldı: {self.pair_x}/{self.pair_y}")
        
        try:
            # WebSocket'i bağla
            await self.ws_provider.connect()
            
            # Subscribe et
            await self.ws_provider.subscribe_ticker(
                [self.pair_x, self.pair_y],
                callback=self.on_price_update,
            )
            
            # Listen et (infinite)
            await self.ws_provider.listen()
            
        except Exception as e:
            logger.error(f"❌ Signal generator hatası: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Generator'ı durdur"""
        logger.info(f"🔴 Signal generator durduruldu")
        await self.ws_provider.disconnect()
    
    def get_current_state(self) -> Dict:
        """
        Mevcut signal state'ini döndür (monitoring için)
        
        Returns:
            Dictionary with current state
        """
        return {
            'pair_x': self.pair_x,
            'pair_y': self.pair_y,
            'hedge_ratio': self.hedge_ratio,
            'last_signal': self.last_signal,
            'last_signal_time': self.last_signal_time.isoformat(),
            'price_x_recent': self.price_history[self.pair_x][-1] if self.price_history[self.pair_x] else None,
            'price_y_recent': self.price_history[self.pair_y][-1] if self.price_history[self.pair_y] else None,
        }


class MultiPairSignalGenerator:
    """
    Multiple pairs için signal generator'lar yönet.
    
    Usage:
        gen = MultiPairSignalGenerator([('BTC', 'ETH', 0.5), ('BTC', 'SOL', 0.3)])
        gen.register_callback(my_trading_func)
        await gen.start()
    """
    
    def __init__(
        self,
        pairs_with_hedges: List[Tuple[str, str, float]],
        config: Optional[Config] = None,
    ):
        """
        Args:
            pairs_with_hedges: [(pair_x, pair_y, hedge_ratio), ...]
            config: Configuration
        """
        self.config = config or get_config()
        self.generators: List[SignalGenerator] = []
        
        for pair_x, pair_y, hedge_ratio in pairs_with_hedges:
            gen = SignalGenerator(
                pair_x=pair_x,
                pair_y=pair_y,
                hedge_ratio=hedge_ratio,
                config=self.config,
            )
            self.generators.append(gen)
        
        logger.info(f"✅ MultiPairSignalGenerator initialized: {len(self.generators)} pairs")
    
    def register_signal_callback(
        self,
        callback: Callable[[TradingSignal], None],
    ) -> None:
        """Tüm generators'a callback register et"""
        for gen in self.generators:
            gen.register_signal_callback(callback)
    
    async def start(self) -> None:
        """Tüm generators'ı başlat (parallel)"""
        logger.info("🟢 MultiPairSignalGenerator başlatıldı")
        
        tasks = [gen.start() for gen in self.generators]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"❌ MultiPairSignalGenerator hatası: {e}")
    
    async def stop(self) -> None:
        """Tüm generators'ı durdur"""
        logger.info("🔴 MultiPairSignalGenerator durduruldu")
        
        tasks = [gen.stop() for gen in self.generators]
        await asyncio.gather(*tasks)
    
    def get_all_states(self) -> List[Dict]:
        """Tüm pair'lerin state'ini döndür"""
        return [gen.get_current_state() for gen in self.generators]


async def example_trading_callback(signal: TradingSignal) -> None:
    """Example trading callback"""
    logger.info(f"💰 TRADING SIGNAL: {signal}")
    
    # Here you would place actual trades via ExecutionEngine
    # await execution_engine.execute(signal)


async def main():
    """Example usage"""
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    config = get_config()
    
    # Single pair
    gen = SignalGenerator(
        pair_x="BTC",
        pair_y="ETH",
        hedge_ratio=0.5,
        config=config,
    )
    
    gen.register_signal_callback(example_trading_callback)
    
    try:
        await gen.start()
    except KeyboardInterrupt:
        logger.info("Terminated by user")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Terminated")
