"""
Application Layer - Sentiment Aggregation Service
==================================================
Orchestrates multiple sentiment providers (OCP compliance)
"""
import logging
from typing import List, Dict
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.interfaces import ISentimentProvider, SentimentData

logger = logging.getLogger(__name__)


class SentimentAggregatorService:
    """
    Aggregates sentiment from multiple providers (OCP)
    New providers can be added without modifying this class
    """
    
    def __init__(self, providers: List[ISentimentProvider]):
        """
        Constructor injection (DIP)
        
        Args:
            providers: List of sentiment providers (CryptoPanic, CoinGecko, etc.)
        """
        self._providers = providers
    
    def get_aggregated_sentiment(self, symbol: str, coin_id: str = None) -> Dict[str, int]:
        """
        Aggregate sentiment from all providers
        
        Returns:
            {
                'positive': weighted average,
                'negative': weighted average,
                'neutral': weighted average,
                'sources': number of sources
            }
        """
        if not self._providers:
            return {'positive': 0, 'negative': 0, 'neutral': 100, 'sources': 0}
        
        sentiments: List[SentimentData] = []
        
        for provider in self._providers:
            try:
                # Use coin_id for CoinGecko, symbol for others
                param = coin_id if 'CoinGecko' in provider.__class__.__name__ and coin_id else symbol
                sentiment = provider.get_sentiment(param)
                sentiments.append(sentiment)
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")
        
        if not sentiments:
            return {'positive': 0, 'negative': 0, 'neutral': 100, 'sources': 0}
        
        # Simple average (could be weighted by source reliability)
        total_positive = sum(s.positive for s in sentiments)
        total_negative = sum(s.negative for s in sentiments)
        total_neutral = sum(s.neutral for s in sentiments)
        count = len(sentiments)
        
        return {
            'positive': round(total_positive / count),
            'negative': round(total_negative / count),
            'neutral': round(total_neutral / count),
            'sources': count
        }
