"""
WebSocket Data Provider - Async
==================================
Binance WebSocket'inden canlı tick veri akışı.
REST polling yerine event-driven, low-latency akışı.

Author: Quant Team
Date: 2026-02-01
"""

import asyncio
import json
import logging
from typing import Callable, Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import aiohttp
import asyncio

try:
    import websockets
except ImportError:
    raise ImportError("websockets kütüphanesi gereklidir. Kurulum: pip install websockets")


logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """Tick data point"""
    timestamp: int
    symbol: str
    bid: float
    ask: float
    mid: float
    bid_size: float
    ask_size: float
    trade_price: float
    trade_size: float
    

class BinanceWebSocketProvider:
    """
    Binance Futures WebSocket Provider.
    
    Özellikler:
    -----------
    - Async/Await pattern (non-blocking)
    - Multiple stream subscription
    - Automatic reconnection
    - Order book snapshot caching (optional)
    """
    
    # Binance Futures WebSocket endpoints
    WSS_BASE_TESTNET = "wss://stream.testnet.binancefuture.com"
    WSS_BASE_LIVE = "wss://fstream.binance.com"
    
    def __init__(
        self,
        use_testnet: bool = False,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 5.0,
    ):
        """
        Args:
            use_testnet: Testnet mi live mi
            max_reconnect_attempts: Max reconnection denemesi
            reconnect_delay: Reconnect arasındaki bekleme (saniye)
        """
        self.use_testnet = use_testnet
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        self.wss_base = self.WSS_BASE_TESTNET if use_testnet else self.WSS_BASE_LIVE
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.subscribed_symbols: Set[str] = set()
        
        # Callback registry
        self.callbacks: Dict[str, list[Callable]] = {}
        
        # Data caching
        self.latest_prices: Dict[str, float] = {}
        self.order_book_cache: Dict[str, dict] = {}  # {symbol: {bid: X, ask: Y}}
        
        self._running = False
        self._reconnect_count = 0
        self._stream_handles = []
        
    async def connect(self) -> bool:
        """
        WebSocket bağlantısını kur.
        
        Returns:
            Başarılı mı
        """
        try:
            uri = f"{self.wss_base}/ws"
            logger.info(f"WebSocket bağlanıyor: {uri}")
            
            self.websocket = await websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
                compression=None,
            )
            
            self._running = True
            self._reconnect_count = 0
            logger.info("✅ WebSocket bağlantısı başarılı")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket bağlantı hatası: {e}")
            return False
    
    async def disconnect(self) -> None:
        """WebSocket bağlantısını kapat"""
        self._running = False
        if self.websocket:
            await self.websocket.close()
        logger.info("WebSocket kapatıldı")
    
    async def subscribe_ticker(self, symbols: list[str]) -> None:
        """
        Semboller için aggTrade stream'ine abone ol.
        
        Args:
            symbols: ["BTCUSDT", "ETHUSDT", ...]
        """
        if not self.websocket or not self._running:
            logger.warning("WebSocket bağlı değil")
            return
        
        streams = [f"{symbol.lower()}@aggTrade" for symbol in symbols]
        self.subscribed_symbols.update(symbols)
        
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1,
        }
        
        try:
            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribe edildi: {symbols}")
        except Exception as e:
            logger.error(f"Subscribe hatası: {e}")
    
    async def subscribe_book_ticker(self, symbols: list[str]) -> None:
        """
        Order book (bid/ask) snapshot'larına abone ol.
        
        Args:
            symbols: ["BTCUSDT", "ETHUSDT", ...]
        """
        if not self.websocket or not self._running:
            logger.warning("WebSocket bağlı değil")
            return
        
        streams = [f"{symbol.lower()}@bookTicker" for symbol in symbols]
        
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 2,
        }
        
        try:
            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info(f"Book Ticker subscribe edildi: {symbols}")
        except Exception as e:
            logger.error(f"Book Ticker subscribe hatası: {e}")
    
    async def listen(self) -> None:
        """
        WebSocket'ten gelen mesajları dinle.
        Bu coroutine sonsuz döngüde çalışır.
        """
        if not self.websocket:
            logger.error("WebSocket bağlı değil")
            return
        
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except asyncio.CancelledError:
            logger.info("Listen iptal edildi")
        except Exception as e:
            logger.error(f"Listen hatası: {e}")
            await self._attempt_reconnect()
    
    async def _handle_message(self, message: str) -> None:
        """
        Gelen WebSocket mesajını işle.
        
        Mesaj türleri:
        - aggTrade: Aggregate trade
        - bookTicker: Best bid/ask snapshot
        """
        try:
            data = json.loads(message)
            
            # aggTrade mesajı
            if "a" in data:  # Aggregate trade ID
                await self._handle_agg_trade(data)
            
            # bookTicker mesajı
            elif "b" in data:  # Bid price
                await self._handle_book_ticker(data)
            
        except json.JSONDecodeError:
            logger.debug(f"JSON decode hatası: {message}")
        except Exception as e:
            logger.error(f"Mesaj işleme hatası: {e}")
    
    async def _handle_agg_trade(self, data: dict) -> None:
        """
        Aggregate trade mesajını işle.
        
        {
            "e": "aggTrade",
            "E": 123456789,
            "s": "BTCUSDT",
            "a": 26129,
            "p": "0.01633102",
            "q": "4.70443515",
            "f": 27781,
            "l": 27781,
            "T": 1519605289000,
            "m": true,
            "M": true
        }
        """
        symbol = data.get("s", "")
        trade_price = float(data.get("p", 0))
        trade_size = float(data.get("q", 0))
        timestamp = int(data.get("E", 0))
        
        # Cache'i güncelle
        self.latest_prices[symbol] = trade_price
        
        # Callback'leri çağır
        await self._call_callbacks("agg_trade", {
            "symbol": symbol,
            "price": trade_price,
            "size": trade_size,
            "timestamp": timestamp,
        })
        
        logger.debug(
            f"AggTrade: {symbol} @ {trade_price} × {trade_size}"
        )
    
    async def _handle_book_ticker(self, data: dict) -> None:
        """
        Book ticker (best bid/ask) mesajını işle.
        
        {
            "u": 400900217,
            "s": "BNBUSDT",
            "b": "25.35190000",
            "B": "31.21000000",
            "a": "25.36236000",
            "A": "40.66000000"
        }
        """
        symbol = data.get("s", "")
        bid_price = float(data.get("b", 0))
        bid_size = float(data.get("B", 0))
        ask_price = float(data.get("a", 0))
        ask_size = float(data.get("A", 0))
        
        # Order book cache'ini güncelle
        self.order_book_cache[symbol] = {
            "bid": bid_price,
            "bid_size": bid_size,
            "ask": ask_price,
            "ask_size": ask_size,
            "mid": (bid_price + ask_price) / 2,
        }
        
        # Callback'leri çağır
        await self._call_callbacks("book_ticker", {
            "symbol": symbol,
            "bid": bid_price,
            "bid_size": bid_size,
            "ask": ask_price,
            "ask_size": ask_size,
        })
        
        logger.debug(
            f"BookTicker: {symbol} bid={bid_price} ask={ask_price}"
        )
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Event callback'i kaydet.
        
        Event types: "agg_trade", "book_ticker"
        
        Args:
            event_type: Callback tipi
            callback: async callable(data: dict)
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
        logger.info(f"Callback registered: {event_type}")
    
    async def _call_callbacks(self, event_type: str, data: dict) -> None:
        """Kayıtlı callback'leri çağır"""
        if event_type not in self.callbacks:
            return
        
        tasks = [callback(data) for callback in self.callbacks[event_type]]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _attempt_reconnect(self) -> None:
        """Reconnection mantığı"""
        while self._reconnect_count < self.max_reconnect_attempts:
            self._reconnect_count += 1
            wait_time = min(self.reconnect_delay * (2 ** (self._reconnect_count - 1)), 60)
            
            logger.warning(
                f"Reconnect denemesi {self._reconnect_count}/{self.max_reconnect_attempts} "
                f"(wait: {wait_time}s)"
            )
            
            await asyncio.sleep(wait_time)
            
            if await self.connect():
                if self.subscribed_symbols:
                    await self.subscribe_ticker(list(self.subscribed_symbols))
                return
        
        logger.error("Max reconnection attempts exceeded")
        self._running = False
    
    async def run(self, symbols: list[str]) -> None:
        """
        Bağlan → Subscribe → Dinle (main loop)
        
        Args:
            symbols: Trade etmek istediğin semboller
        """
        if not await self.connect():
            logger.error("Başlangıç bağlantı başarısız")
            return
        
        # Subscribe et
        await self.subscribe_ticker(symbols)
        await self.subscribe_book_ticker(symbols)
        
        # Dinle
        await self.listen()
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Son kâhini fiyatı döndür"""
        return self.latest_prices.get(symbol)
    
    def get_order_book(self, symbol: str) -> Optional[dict]:
        """Son order book snapshot'ını döndür"""
        return self.order_book_cache.get(symbol)


async def example_usage():
    """Kullanım örneği"""
    
    # Provider'ı oluştur
    provider = BinanceWebSocketProvider(use_testnet=True)
    
    # Callback'leri kaydet
    async def on_trade(data: dict):
        print(f"Trade: {data['symbol']} @ {data['price']}")
    
    async def on_book(data: dict):
        print(
            f"Book: {data['symbol']} "
            f"bid={data['bid']} ask={data['ask']}"
        )
    
    provider.register_callback("agg_trade", on_trade)
    provider.register_callback("book_ticker", on_book)
    
    # Çalıştır
    try:
        await provider.run(["BTCUSDT", "ETHUSDT"])
    except KeyboardInterrupt:
        await provider.disconnect()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    asyncio.run(example_usage())
