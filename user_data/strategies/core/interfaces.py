"""
Core Domain Interfaces
======================
Abstractions following Interface Segregation Principle (ISP)
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class SentimentData:
    """Domain model for sentiment data"""
    positive: int
    negative: int
    neutral: int
    source: str


@dataclass
class MarketData:
    """Domain model for market indicators"""
    fear_greed_value: int
    fear_greed_classification: str
    funding_rate: float


class ISentimentProvider(ABC):
    """Interface for sentiment data providers (ISP compliance)"""
    
    @abstractmethod
    def get_sentiment(self, symbol: str) -> SentimentData:
        """Retrieve sentiment data for a symbol"""
        pass


class IMarketDataProvider(ABC):
    """Interface for market data providers"""
    
    @abstractmethod
    def get_fear_greed_index(self) -> Dict[str, any]:
        """Retrieve Fear & Greed Index"""
        pass
    
    @abstractmethod
    def get_funding_rate(self, symbol: str) -> float:
        """Retrieve funding rate for a futures pair"""
        pass


class ICointegrationAnalyzer(ABC):
    """Interface for cointegration analysis (SRP)"""
    
    @abstractmethod
    def calculate_cointegration(self, price_x, price_y, pair_x: str, pair_y: str) -> Dict:
        """Calculate cointegration between two price series"""
        pass


class ICacheService(ABC):
    """Interface for caching (DIP compliance)"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[any]:
        """Retrieve cached value"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: any) -> None:
        """Store value in cache"""
        pass
    
    @abstractmethod
    def clean(self, max_size: int) -> None:
        """Clean old cache entries"""
        pass
