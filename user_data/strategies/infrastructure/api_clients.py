"""
Infrastructure Layer - External API Clients
===========================================
Concrete implementations of domain interfaces (DIP compliance)

AUTO-REGISTRATION: Providers register themselves (OCP via Registry Pattern)
"""
import logging
import time
from typing import Dict, Optional
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.interfaces import ISentimentProvider, IMarketDataProvider, SentimentData
from core.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class CryptoPanicSentimentProvider(ISentimentProvider):
    """
    CryptoPanic API client (SRP: Only handles CryptoPanic integration)
    
    OCP: Constructor accepts config dict → new params = no signature change
    """
    
    def __init__(self, config: dict):
        """
        Args:
            config: {
                'api_key': Optional API key (fallback to env),
                'cache_service': ICacheService instance,
                'cache_ttl': Cache duration in seconds
            }
        """
        self.api_key = config.get('api_key') or os.getenv("CRYPTOPANIC_API_KEY", "9993cd1826da97d855ee019eadf92a71de388063")
        self.cache = config.get('cache_service')
        self.cache_ttl = config.get('cache_ttl', 43200)  # Default 12h
        self.base_url = "https://cryptopanic.com/api/developer/v2/posts/"
    
    def get_sentiment(self, symbol: str) -> SentimentData:
        """Implementation of ISentimentProvider"""
        if not HAS_REQUESTS:
            return SentimentData(0, 0, 100, "cryptopanic")
        
        # Check cache (configurable TTL)
        cache_key = f"{symbol}_cryptopanic_{int(time.time() / self.cache_ttl)}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        try:
            url = f"{self.base_url}?auth_token={self.api_key}&currencies={symbol}&filter=hot&public=true"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            positive = negative = neutral = 0
            results = data.get("results", [])[:10]
            
            for post in results:
                votes = post.get("votes", {})
                positive += votes.get("positive", 0)
                negative += votes.get("negative", 0)
                
                sent = post.get("sentiment")
                if sent == "positive":
                    positive += 1
                elif sent == "negative":
                    negative += 1
                else:
                    neutral += 1
            
            total = positive + negative + neutral or 1
            
            result = SentimentData(
                positive=round(positive / total * 100),
                negative=round(negative / total * 100),
                neutral=round(neutral / total * 100),
                source="cryptopanic"
            )
            
            if self.cache:
                self.cache.set(cache_key, result)
            
            logger.info(f"{symbol} news sentiment: +{result.positive}% / -{result.negative}%")
            return result
            
        except Exception as e:
            logger.warning(f"CryptoPanic error: {e}")
            return SentimentData(0, 0, 100, "cryptopanic")


class BinanceMarketDataProvider(IMarketDataProvider):
    """
    Binance Futures API client (SRP: Only handles Binance data)
    
    OCP: Config dict allows adding new params without breaking changes
    """
    
    def __init__(self, config: dict):
        """
        Args:
            config: {
                'cache_service': ICacheService instance,
                'cache_ttl': Cache duration (default 7200s = 2h)
            }
        """
        self.cache = config.get('cache_service')
        self.cache_ttl = config.get('cache_ttl', 7200)
        self.base_url = "https://fapi.binance.com/fapi/v1"
        self.fear_greed_url = "https://api.alternative.me/fng/?limit=1"
    
    def get_fear_greed_index(self) -> Dict[str, any]:
        """Implementation of IMarketDataProvider"""
        if not HAS_REQUESTS:
            return {"value": 50, "classification": "Neutral"}
        
        # Configurable cache TTL
        cache_key = f"fear_greed_{int(time.time() / self.cache_ttl)}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        try:
            resp = requests.get(self.fear_greed_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            fng_data = data.get("data", [{}])[0]
            value = int(fng_data.get("value", 50))
            classification = fng_data.get("value_classification", "Neutral")
            
            result = {"value": value, "classification": classification}
            
            if self.cache:
                self.cache.set(cache_key, result)
            
            logger.info(f"Fear & Greed Index: {value} ({classification})")
            return result
            
        except Exception as e:
            logger.warning(f"Fear & Greed fetch error: {e}")
            return {"value": 50, "classification": "Neutral"}
    
    def get_funding_rate(self, symbol: str) -> float:
        """Implementation of IMarketDataProvider"""
        if not HAS_REQUESTS:
            return 0.0
        
        # 30-min cache
        cache_key = f"funding_{symbol}_{int(time.time() / 1800)}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        try:
            url = f"{self.base_url}/fundingRate?symbol={symbol}&limit=1"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            funding_rate = float(data[0].get("fundingRate", 0)) * 100 if data else 0.0
            
            if self.cache:
                self.cache.set(cache_key, funding_rate)
            
            logger.info(f"{symbol} Funding Rate: {funding_rate:.4f}%")
            
            # Arbitrage opportunity detection
            if abs(funding_rate) > 0.05:
                direction = "SHORT" if funding_rate > 0 else "LONG"
                annualized = funding_rate * 3 * 365
                logger.warning(f"[ARBITRAGE] 💰 {symbol} Funding Opportunity: {direction} | Annualized: {annualized:.2f}%")
            
            return funding_rate
            
        except Exception as e:
            logger.warning(f"Funding rate error: {e}")
            return 0.0


class CoinGeckoSentimentProvider(ISentimentProvider):
    """
    CoinGecko API client (SRP: Only handles CoinGecko integration)
    
    OCP: Config-driven initialization
    """
    
    def __init__(self, config: dict):
        """
        Args:
            config: {
                'cache_service': ICacheService,
                'cache_ttl': Cache duration (default 3600s = 1h)
            }
        """
        self.cache = config.get('cache_service')
        self.cache_ttl = config.get('cache_ttl', 3600)
        self.base_url = "https://api.coingecko.com/api/v3/coins"
    
    def get_sentiment(self, coin_id: str) -> SentimentData:
        """Get sentiment from 7-day price change"""
        if not HAS_REQUESTS:
            return SentimentData(0, 0, 100, "coingecko")
        
        # Configurable cache
        cache_key = f"{coin_id}_coingecko_{int(time.time() / self.cache_ttl)}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        try:
            url = f"{self.base_url}/{coin_id}?localization=false&community_data=true"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            price_change_7d = data.get("market_data", {}).get("price_change_percentage_7d", 0)
            
            if price_change_7d > 5:
                result = SentimentData(70, 10, 20, "coingecko")
            elif price_change_7d < -5:
                result = SentimentData(10, 70, 20, "coingecko")
            else:
                result = SentimentData(33, 33, 34, "coingecko")
            
            if self.cache:
                self.cache.set(cache_key, result)
            
            logger.info(f"{coin_id} sentiment (7d: {price_change_7d:.2f}%): {result.positive}% positive")
            return result
            
        except Exception as e:
            logger.warning(f"CoinGecko error: {e}")
            return SentimentData(0, 0, 100, "coingecko")


# ============================================================================
# AUTO-REGISTRATION (OCP): New providers automatically discoverable
# ============================================================================
# No manual registration needed - just add class and it's available via config
ProviderRegistry.register("CryptoPanicSentimentProvider", CryptoPanicSentimentProvider)
ProviderRegistry.register("CoinGeckoSentimentProvider", CoinGeckoSentimentProvider)
ProviderRegistry.register("BinanceMarketDataProvider", BinanceMarketDataProvider)

logger.info(f"✅ API Clients registered: {ProviderRegistry.list_available()}")
