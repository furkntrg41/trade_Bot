"""
Application Layer - Dynamic Service Container (OCP via Config)
===============================================================
NO HARDCODED DEPENDENCIES - Everything loaded from YAML.

Architecture Benefits:
1. OCP: Add providers in config, not code
2. Testability: Mock providers via config
3. Environment-specific: dev/staging/prod configs
4. A/B Testing: Toggle providers on/off

Complexity:
- Initialization: O(n × T_provider) where n = providers
- Service access: O(1) via property getters
"""
from typing import Optional, List
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.interfaces import ISentimentProvider, IMarketDataProvider, ICointegrationAnalyzer, ICacheService
from infrastructure.cache_service import InMemoryCacheService
from application.cointegration_service import CointegrationService
from application.sentiment_service import SentimentAggregatorService
from application.config_loader import ConfigurationLoader
from core.provider_registry import ProviderRegistry

# Register all available providers (auto-discovery)
from infrastructure import api_clients  # Triggers auto-registration

logger = logging.getLogger(__name__)


class DynamicServiceContainer:
    """
    Config-driven IoC Container (OCP compliance).
    
    Traditional Problem:
        - Add new provider → Modify __init__ → Recompile
        - OCP violation
    
    Solution:
        - Add provider in YAML → No code change
        - Dependency graph built dynamically
    
    Memory: O(n) services + O(m) providers
    Thread-Safety: Singleton with lazy init
    """
    
    _instance: Optional['DynamicServiceContainer'] = None
    
    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: str = None):
        if self._initialized:
            return
        
        # Default config path
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'config',
                'providers.yaml'
            )
        
        self.config_loader = ConfigurationLoader(config_path)
        self.config = self.config_loader.load()
        
        # Initialize infrastructure (shared dependencies)
        self._init_infrastructure()
        
        # Load providers dynamically from config
        self._load_sentiment_providers()
        self._load_market_data_providers()
        self._load_cointegration_service()
        
        self._initialized = True
        logger.info("✅ DynamicServiceContainer initialized from config")
    
    def _init_infrastructure(self):
        """Initialize shared infrastructure services"""
        # Cache service (singleton across all providers)
        self._cache_service: ICacheService = InMemoryCacheService(max_size=50)
        logger.debug("Cache service initialized")
    
    def _load_sentiment_providers(self):
        """
        Load sentiment providers from config (OCP).
        
        Time: O(n × T_init) where n = enabled providers
        """
        self._sentiment_providers: List[ISentimentProvider] = []
        
        try:
            providers = self.config_loader.instantiate_providers(
                category='sentiment_providers',
                registry=ProviderRegistry,
                additional_deps={'cache_service': self._cache_service}
            )
            
            self._sentiment_providers = providers
            logger.info(f"✅ Loaded {len(providers)} sentiment providers")
        
        except Exception as e:
            logger.error(f"❌ Failed to load sentiment providers: {e}")
            # Fallback: empty list (graceful degradation)
            self._sentiment_providers = []
    
    def _load_market_data_providers(self):
        """Load market data providers from config"""
        try:
            providers = self.config_loader.instantiate_providers(
                category='market_data_providers',
                registry=ProviderRegistry,
                additional_deps={'cache_service': self._cache_service}
            )
            
            # Use first enabled provider (strategy pattern: swappable)
            if providers:
                self._market_data_provider: IMarketDataProvider = providers[0]
                logger.info(f"✅ Market data provider: {type(self._market_data_provider).__name__}")
            else:
                logger.warning("⚠️ No market data provider enabled")
                self._market_data_provider = None
        
        except Exception as e:
            logger.error(f"❌ Market data provider load failed: {e}")
            self._market_data_provider = None
    
    def _load_cointegration_service(self):
        """Load cointegration service (business logic)"""
        try:
            # Cointegration config from YAML
            coint_config = self.config.get('cointegration_algorithms', [])
            enabled = [c for c in coint_config if c.get('enabled', False)]
            
            if enabled:
                config = enabled[0].get('config', {})
                self._cointegration_service = CointegrationService(
                    cache_service=self._cache_service,
                    max_spread_history=config.get('lookback_period', 252)
                )
                logger.info("✅ Cointegration service initialized")
            else:
                self._cointegration_service = None
                logger.warning("⚠️ No cointegration algorithm enabled")
        
        except Exception as e:
            logger.error(f"❌ Cointegration service init failed: {e}")
            self._cointegration_service = None
    
    # =============================================================================
    # PUBLIC API (Property Getters for Dependency Injection)
    # =============================================================================
    
    @property
    def cache_service(self) -> ICacheService:
        """Get cache service instance"""
        return self._cache_service
    
    @property
    def sentiment_aggregator(self) -> SentimentAggregatorService:
        """
        Get sentiment aggregator (OCP: Aggregates ALL enabled providers).
        
        If config changes (new provider enabled), next restart picks it up.
        NO CODE CHANGE NEEDED.
        """
        return SentimentAggregatorService(providers=self._sentiment_providers)
    
    @property
    def market_data_provider(self) -> Optional[IMarketDataProvider]:
        """Get market data provider (Strategy Pattern: swappable via config)"""
        return self._market_data_provider
    
    @property
    def cointegration_service(self) -> Optional[ICointegrationAnalyzer]:
        """Get cointegration service"""
        return self._cointegration_service
    
    def reload_config(self):
        """Hot-reload configuration (advanced feature)"""
        self._initialized = False
        self.__init__()
        logger.info("🔄 Configuration reloaded")
    
    def get_provider_stats(self) -> dict:
        """
        Debug: Get loaded provider statistics.
        
        Returns:
            {
                'sentiment_providers': int,
                'market_data_providers': int,
                'cointegration_enabled': bool
            }
        """
        return {
            'sentiment_providers': len(self._sentiment_providers),
            'market_data_providers': 1 if self._market_data_provider else 0,
            'cointegration_enabled': self._cointegration_service is not None
        }
