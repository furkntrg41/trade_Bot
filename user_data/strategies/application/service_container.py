"""
Application Layer - Service Container (IoC Container Pattern)
==============================================================
Dependency injection container (SOLID compliance)
"""
from typing import Optional

from ..core.interfaces import (
    ISentimentProvider, 
    IMarketDataProvider, 
    ICointegrationAnalyzer,
    ICacheService
)
from ..infrastructure.api_clients import (
    CryptoPanicSentimentProvider,
    CoinGeckoSentimentProvider,
    BinanceMarketDataProvider
)
from ..infrastructure.cache_service import InMemoryCacheService
from ..application.cointegration_service import CointegrationService
from ..application.sentiment_service import SentimentAggregatorService


class ServiceContainer:
    """
    IoC Container for dependency management (DIP)
    Singleton pattern for application-wide access
    """
    
    _instance: Optional['ServiceContainer'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Infrastructure services
        self._cache_service: ICacheService = InMemoryCacheService(max_size=50)
        
        # API clients (infrastructure layer)
        self._cryptopanic_provider: ISentimentProvider = CryptoPanicSentimentProvider(
            cache_service=self._cache_service
        )
        self._coingecko_provider: ISentimentProvider = CoinGeckoSentimentProvider(
            cache_service=self._cache_service
        )
        self._binance_market_provider: IMarketDataProvider = BinanceMarketDataProvider(
            cache_service=self._cache_service
        )
        
        # Application services (business logic)
        self._cointegration_service: ICointegrationAnalyzer = CointegrationService(
            cache_service=self._cache_service,
            max_spread_history=252
        )
        
        self._sentiment_aggregator = SentimentAggregatorService(
            providers=[self._cryptopanic_provider, self._coingecko_provider]
        )
        
        self._initialized = True
    
    @property
    def cache_service(self) -> ICacheService:
        """Get cache service instance"""
        return self._cache_service
    
    @property
    def cointegration_service(self) -> ICointegrationAnalyzer:
        """Get cointegration service instance"""
        return self._cointegration_service
    
    @property
    def sentiment_aggregator(self) -> SentimentAggregatorService:
        """Get sentiment aggregator instance"""
        return self._sentiment_aggregator
    
    @property
    def market_data_provider(self) -> IMarketDataProvider:
        """Get market data provider instance"""
        return self._binance_market_provider
    
    def reset(self):
        """Reset container (useful for testing)"""
        self._cache_service.clear()
