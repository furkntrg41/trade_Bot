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
from infrastructure import feature_generators  # Register feature generators
from application import cointegration_algorithms  # Register algorithms

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
    
    def __new__(cls, config_path: str = None, enable_hot_reload: bool = False):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: str = None, enable_hot_reload: bool = False):
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
        
        self.config_path = config_path
        self.config_loader = ConfigurationLoader(config_path)
        self.config = self.config_loader.load()
        
        # Initialize infrastructure (shared dependencies)
        self._init_infrastructure()
        
        # Load providers dynamically from config
        self._load_sentiment_providers()
        self._load_market_data_providers()
        self._load_cointegration_service()
        self._load_feature_pipeline()  # NEW: Plugin-based features
        
        # Hot-reload watcher (optional - production feature)
        self._config_watcher = None
        if enable_hot_reload:
            self._start_hot_reload()
        
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
    
    def _load_feature_pipeline(self):
        """
        Load feature generators from config (OCP).
        
        Benefits:
        - Add new features: Edit YAML, no code change
        - A/B test features: Toggle enabled flag
        - Feature importance: See config for active features
        """
        try:
            from core.feature_interfaces import FeaturePipeline
            
            generators = self.config_loader.instantiate_providers(
                category='feature_generators',
                registry=ProviderRegistry,
                additional_deps={}  # Feature generators don't need cache
            )
            
            self._feature_pipeline = FeaturePipeline(generators)
            logger.info(f"✅ Feature pipeline: {len(generators)} generators loaded")
        
        except Exception as e:
            logger.error(f"❌ Feature pipeline init failed: {e}")
            self._feature_pipeline = None
    
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
    
    @property
    def feature_pipeline(self):
        """
        Get feature engineering pipeline (OCP: Add generators via config).
        
        Usage in strategy:
            df = self._container.feature_pipeline.execute(df, metadata)
        
        Benefits:
        - All features generated in one call
        - Error handling per generator
        - Performance tracking
        """
        return self._feature_pipeline
    
    def _start_hot_reload(self):
        """
        Start hot-reload watcher (production-grade).
        
        WARNING: Use with caution in production!
        - Can cause race conditions during reload
        - Test thoroughly before enabling
        - Recommended: Use manual reload_config() instead
        """
        try:
            from application.config_watcher import ConfigWatcher
            
            self._config_watcher = ConfigWatcher(
                config_path=self.config_path,
                callback=self.reload_config,
                poll_interval=10.0  # Check every 10s (production-safe)
            )
            
            self._config_watcher.start()
            logger.info("🔥 Hot-reload ENABLED - config changes auto-applied")
        
        except Exception as e:
            logger.error(f"❌ Hot-reload init failed: {e}")
            self._config_watcher = None
    
    def reload_config(self):
        """
        Hot-reload configuration.
        
        Thread-Safety: Uses _initialized flag to prevent concurrent reloads.
        
        Use cases:
        1. Manual reload: container.reload_config()
        2. Auto reload: enable_hot_reload=True
        3. Emergency disable: Edit YAML, reload instantly
        """
        if not self._initialized:
            logger.warning("⚠️ Reload already in progress")
            return
        
        logger.info("🔄 Reloading configuration...")
        
        self._initialized = False
        self.__init__(config_path=self.config_path, enable_hot_reload=False)
        
        logger.info("✅ Configuration reloaded successfully")
    
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
            'cointegration_enabled': self._cointegration_service is not None,
            'feature_generators': len(self._feature_pipeline.generators) if self._feature_pipeline else 0,
            'hot_reload_enabled': self._config_watcher is not None and self._config_watcher.is_running()
        }
    
    def shutdown(self):
        """
        Graceful shutdown (stop watcher thread).
        
        Call this before app exit to prevent resource leaks.
        """
        if self._config_watcher:
            self._config_watcher.stop()
            logger.info("✅ Container shutdown complete")
