"""
Application Layer - Configuration Loader (OCP via External Config)
===================================================================
Load providers from YAML WITHOUT code changes.

Complexity Analysis:
- Load YAML: O(n) where n = file size
- Parse providers: O(m) where m = number of providers
- Total: O(n + m) - linear, acceptable for startup
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.provider_registry import ProviderRegistry
from core.interfaces import ISentimentProvider, IMarketDataProvider

logger = logging.getLogger(__name__)


class ConfigurationLoader:
    """
    Load provider configuration from YAML (OCP compliance).
    
    Benefits:
    - Add/remove providers: Edit YAML, no code recompile
    - A/B testing: Toggle 'enabled' flag
    - Environment-specific configs: dev.yaml, prod.yaml
    
    Memory: O(c) where c = config size (typically < 10KB)
    """
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config: dict = {}
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
    
    def load(self) -> dict:
        """
        Load and parse YAML config.
        
        Time: O(n) where n = file size
        Memory: O(n) for parsed dict
        """
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        logger.info(f"✅ Config loaded: {self.config_path}")
        return self.config
    
    def get_enabled_providers(self, category: str) -> List[Dict]:
        """
        Filter enabled providers by category.
        
        Time: O(m) where m = providers in category
        
        Args:
            category: 'sentiment_providers', 'market_data_providers', etc.
        
        Returns:
            List of enabled provider configs
        """
        providers = self.config.get(category, [])
        enabled = [p for p in providers if p.get('enabled', False)]
        
        logger.info(f"📦 {category}: {len(enabled)}/{len(providers)} enabled")
        return enabled
    
    def instantiate_providers(
        self, 
        category: str,
        registry: ProviderRegistry,
        additional_deps: dict = None
    ) -> list:
        """
        Create provider instances from config (Factory Pattern).
        
        OCP: New provider in YAML = auto-instantiated, no code change.
        
        Time: O(m × T_init) where:
            m = number of providers
            T_init = provider constructor time (typically O(1))
        
        Args:
            category: Provider category
            registry: ProviderRegistry for class lookup
            additional_deps: Extra dependencies (cache_service, etc.)
        
        Returns:
            List of instantiated providers
        """
        enabled = self.get_enabled_providers(category)
        instances = []
        
        for provider_config in enabled:
            name = provider_config['name']
            class_name = provider_config['class']
            config = provider_config.get('config', {})
            
            # Merge additional dependencies
            if additional_deps:
                config.update(additional_deps)
            
            try:
                # Resolve API keys from environment (12-Factor App)
                if 'api_key_env' in config:
                    env_var = config['api_key_env']
                    config['api_key'] = os.environ.get(env_var, '')
                
                instance = registry.create(class_name, config)
                instances.append(instance)
                
                logger.info(f"✅ Instantiated: {name} ({class_name})")
            
            except Exception as e:
                logger.error(f"❌ Failed to create {name}: {e}")
                # Continue loading other providers (fault tolerance)
        
        return instances
