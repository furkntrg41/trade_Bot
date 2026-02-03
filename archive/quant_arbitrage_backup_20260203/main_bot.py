"""
Main Quant Arbitrage Bot
========================
Pairs Trading + Funding Rate Arbitrage entegre bot.

Workflow:
1. Kointegrasyon taraması (offline)
2. WebSocket bağlantısı (live data)
3. Sinyal üretimi (Z-score)
4. Position management
5. Risk yönetimi

Author: Quant Team
Date: 2026-02-01
"""

import asyncio
import logging
from typing import Dict, List
import numpy as np
import pandas as pd

from quant_arbitrage import (
    CointegrationAnalyzer,
    PairsSpreadCalculator,
    BinanceWebSocketProvider,
    FundingRateMonitor,
    RiskManager,
    PositionSide,
    SignalType,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QuantArbitrageBot:
    """
    Delta-Neutral Quantitative Arbitrage Bot
    
    Features:
    - Pairs Trading (Statistical Arbitrage)
    - Funding Rate Arbitrage
    - Risk Management (Kelly Criterion, Delta Hedging)
    - WebSocket Real-time Data
    """
    
    def __init__(
        self,
        account_equity: float = 10000.0,
        use_testnet: bool = True,
    ):
        """
        Args:
            account_equity: İlk hesap öz sermayesi
            use_testnet: Testnet mi kullan
        """
        self.account_equity = account_equity
        self.use_testnet = use_testnet
        
        # Components
        self.cointegration_analyzer = CointegrationAnalyzer(
            lookback_window=252,
            adf_pvalue_threshold=0.05,
            coint_pvalue_threshold=0.05,
            min_correlation=0.6,
        )
        
        self.websocket_provider = BinanceWebSocketProvider(
            use_testnet=use_testnet,
            max_reconnect_attempts=5,
        )
        
        self.funding_monitor = FundingRateMonitor(
            annualized_funding_threshold=0.05,
            min_position_size=0.1,
        )
        
        self.risk_manager = RiskManager(
            account_equity=account_equity,
            max_loss_per_trade=0.01,  # %1
            max_total_delta=0.1,  # %10
            max_concentration=0.05,  # %5
            kelly_fraction=0.25,
        )
        
        # Pairs trading state
        self.pairs_calculators: Dict[str, PairsSpreadCalculator] = {}
        self.identified_pairs: List[tuple] = []  # [(X, Y, hedge_ratio), ...]
        
        # Live prices cache
        self.prices: Dict[str, float] = {}
        
    async def initialize(self) -> bool:
        """Bot'ı başlat"""
        logger.info("🤖 Quant Arbitrage Bot başlatılıyor...")
        
        # WebSocket callback'leri kaydet
        self.websocket_provider.register_callback(
            "agg_trade", self._on_trade
        )
        self.websocket_provider.register_callback(
            "book_ticker", self._on_book_ticker
        )
        
        logger.info(f"✅ Bot hazır (Equity: {self.account_equity} USDT)")
        return True
    
    async def scan_cointegration(
        self,
        symbol_list: List[str],
        historical_data: Dict[str, np.ndarray],
    ) -> None:
        """
        Kointegrasyon taraması (offline).
        
        Args:
            symbol_list: Sembol listesi
            historical_data: {symbol: price_array}
        """
        logger.info(f"📊 Kointegrasyon taraması başlatılıyor ({len(symbol_list)} sembol)...")
        
        # Tarama yap
        top_pairs = self.cointegration_analyzer.scan_universe(
            historical_data,
            top_n=10
        )
        
        for result in top_pairs:
            logger.info(f"  ✅ {result}")
            
            # Calculator'ı oluştur
            pair_id = f"{result.pair_x}_{result.pair_y}"
            calculator = PairsSpreadCalculator(
                hedge_ratio=result.hedge_ratio,
                lookback_periods=252,
                z_score_threshold=2.0,
                z_score_exit=0.5,
            )
            self.pairs_calculators[pair_id] = calculator
            self.identified_pairs.append(
                (result.pair_x, result.pair_y, result.hedge_ratio)
            )
        
        logger.info(f"🎯 {len(self.pairs_calculators)} pair trader'ı kayıtlı")
    
    async def _on_trade(self, data: dict) -> None:
        """Trade event callback"""
        symbol = data.get("symbol")
        price = data.get("price")
        
        # Cache'i güncelle
        self.prices[symbol] = price
        
        # Pairs trading sinyalleri
        await self._process_pairs_signals(symbol, price)
    
    async def _on_book_ticker(self, data: dict) -> None:
        """Book ticker event callback"""
        symbol = data.get("symbol")
        bid = data.get("bid")
        ask = data.get("ask")
        
        # Funding arbitrage fırsatı
        await self._check_funding_opportunity(symbol, bid, ask)
    
    async def _process_pairs_signals(self, symbol: str, price: float) -> None:
        """Pairs trading sinyallerini işle"""
        # Önce symbol'e ait pair'leri bulsa
        relevant_pairs = [
            (pair_id, calc) for pair_id, calc in self.pairs_calculators.items()
            if symbol in pair_id
        ]
        
        for pair_id, calculator in relevant_pairs:
            # Diğer varlığın fiyatını alalı
            parts = pair_id.split("_")
            other_symbol = parts[1] if parts[0] == symbol else parts[0]
            
            if other_symbol not in self.prices:
                continue
            
            other_price = self.prices[other_symbol]
            
            # Sinyal üret
            signal = calculator.add_prices(price, other_price)
            
            # Sinyal temelinde aksiyon al
            if signal.signal == SignalType.LONG_SPREAD:
                logger.info(
                    f"📈 LONG SPREAD {pair_id} | "
                    f"Z={signal.z_score:.2f} | Conf={signal.confidence:.2f}"
                )
                await self._enter_pairs_position(pair_id, "long", signal)
            
            elif signal.signal == SignalType.SHORT_SPREAD:
                logger.info(
                    f"📉 SHORT SPREAD {pair_id} | "
                    f"Z={signal.z_score:.2f} | Conf={signal.confidence:.2f}"
                )
                await self._enter_pairs_position(pair_id, "short", signal)
            
            elif signal.signal == SignalType.EXIT_LONG:
                logger.info(f"🔚 EXIT LONG SPREAD {pair_id}")
                await self._exit_pairs_position(pair_id)
            
            elif signal.signal == SignalType.EXIT_SHORT:
                logger.info(f"🔚 EXIT SHORT SPREAD {pair_id}")
                await self._exit_pairs_position(pair_id)
    
    async def _enter_pairs_position(
        self,
        pair_id: str,
        direction: str,
        signal,
    ) -> None:
        """Pairs trading pozisyonuna gir"""
        parts = pair_id.split("_")
        symbol_x, symbol_y = parts[0], parts[1]
        
        price_x = self.prices.get(symbol_x, 0)
        price_y = self.prices.get(symbol_y, 0)
        
        if price_x <= 0 or price_y <= 0:
            logger.warning("Fiyat verisi eksik")
            return
        
        # Position size hesapla
        entry_price = price_x  # Reference olarak X'i kullan
        stop_loss = entry_price * 1.02 if direction == "long" else entry_price * 0.98
        
        position_size = self.risk_manager.calculate_position_size(
            symbol=symbol_x,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
        )
        
        if position_size <= 0:
            logger.warning("Position size sıfır")
            return
        
        # Risk manager'a ekle
        side = PositionSide.LONG if direction == "long" else PositionSide.SHORT
        self.risk_manager.add_position(
            symbol=pair_id,
            side=side,
            size=position_size,
            entry_price=entry_price,
            delta=0.8,  # Pairs trading daha düşük delta
        )
        
        logger.info(
            f"✅ Position opened: {pair_id} {direction.upper()} "
            f"Size: {position_size:.2f} USDT"
        )
    
    async def _exit_pairs_position(self, pair_id: str) -> None:
        """Pairs trading pozisyonundan çık"""
        parts = pair_id.split("_")
        symbol_x = parts[0]
        exit_price = self.prices.get(symbol_x, 0)
        
        if exit_price <= 0:
            logger.warning("Exit fiyatı bulunamadı")
            return
        
        position = self.risk_manager.remove_position(pair_id, exit_price)
        if position:
            logger.info(f"✅ Position closed: {pair_id} PnL: {position.get('pnl', 0):.2f}")
    
    async def _check_funding_opportunity(
        self,
        symbol: str,
        bid: float,
        ask: float,
    ) -> None:
        """Funding rate arbitraj fırsatını kontrol et"""
        # Burada funding rate API'den alınacak
        # Şimdilik placeholder
        
        # current_funding_rate = await self._fetch_funding_rate(symbol)
        # opportunity = self.funding_monitor.check_opportunity(...)
        pass
    
    async def _fetch_funding_rate(self, symbol: str) -> float:
        """Binance REST API'den funding rate al"""
        # TODO: Implement Binance funding rate REST API call
        return 0.0
    
    async def run(
        self,
        symbols: List[str],
        historical_data: Dict[str, np.ndarray],
    ) -> None:
        """
        Bot'ı çalıştır.
        
        Args:
            symbols: Trade etmek istediğin semboller
            historical_data: Kointegrasyon testi için geçmiş veri
        """
        # Initialize
        await self.initialize()
        
        # Kointegrasyon tara
        await self.scan_cointegration(symbols, historical_data)
        
        # WebSocket bağlan
        logger.info("🔗 WebSocket bağlanılıyor...")
        websocket_task = asyncio.create_task(
            self.websocket_provider.run(symbols)
        )
        
        # Monitoring loop
        try:
            while True:
                await asyncio.sleep(60)  # Her dakika rapor
                
                # Status raporu
                logger.info("\n" + "="*50)
                logger.info("📊 BOT STATUS")
                logger.info("="*50)
                logger.info(self.risk_manager.get_summary())
                logger.info(f"Active Pairs: {len(self.pairs_calculators)}")
                logger.info("="*50 + "\n")
        
        except KeyboardInterrupt:
            logger.info("🛑 Bot kapatılıyor...")
            await self.websocket_provider.disconnect()
            websocket_task.cancel()


async def main():
    """Example: Kointegrasyon taraması ve bot çalıştırması"""
    
    # Örnek: Geçmiş veriyi Binance'dan indir
    # (Gerçek implementation'da pd_datareader veya ccxt kullan)
    
    symbols = ["BTC", "ETH", "SOL", "XRP", "ADA"]
    
    # Dummy data (gerçekten indirmiyoruz)
    historical_data = {
        symbol: np.random.randn(252).cumsum() + 100
        for symbol in symbols
    }
    
    # Bot'u oluştur ve çalıştır
    bot = QuantArbitrageBot(
        account_equity=10000.0,
        use_testnet=True,
    )
    
    try:
        await bot.run(
            symbols=[f"{s}USDT" for s in symbols],
            historical_data=historical_data,
        )
    except Exception as e:
        logger.error(f"Bot hatası: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
