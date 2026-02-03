"""
Core Layer - Provider Registry (OCP via Plugin Architecture)
=============================================================
Dynamic provider loading WITHOUT code modification.

Design Pattern: Abstract Factory + Registry Pattern
Time Complexity: O(1) provider lookup via dict
Memory: O(n) providers registered (minimal overhead)
"""
from typing import Dict, Type, Protocol
import logging

logger = logging.getLogger(__name__)


class IProvider(Protocol):
    """Base provider protocol (Liskov Substitution)"""
    def __init__(self, config: dict): ...


class ProviderRegistry:
    """
    SINGLETON Registry for dynamic provider discovery.
    
    OCP Compliance: Add new providers via register() - no source modification.
    Thread-Safe: Uses class-level dict (immutable after registration phase).
    
    Complexity:
    - Register: O(1)
    - Get: O(1) dict lookup
    - Memory: O(n) where n = number of providers
    """
    
    _providers: Dict[str, Type[IProvider]] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: Type[IProvider]) -> None:
        """
        Register provider class for dynamic instantiation.
        
        Args:
            name: Unique provider identifier
            provider_class: Class implementing IProvider protocol
            
        Raises:
            ValueError: If provider already registered (prevents overwrites)
        """
        if name in cls._providers:
            raise ValueError(f"Provider '{name}' already registered")
        
        cls._providers[name] = provider_class
        logger.info(f"✅ Provider registered: {name} -> {provider_class.__name__}")
    
    @classmethod
    def get(cls, name: str) -> Type[IProvider]:
        """
        Retrieve provider class by name (Factory Pattern).
        
        Time: O(1) dict access
        
        Raises:
            KeyError: If provider not found
        """
        if name not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise KeyError(f"Provider '{name}' not found. Available: {available}")
        
        return cls._providers[name]
    
    @classmethod
    def create(cls, name: str, config: dict) -> IProvider:
        """
        Factory method: Create provider instance with config.
        
        OCP: New provider types supported without modification.
        DIP: Returns interface, not concrete type.
        
        Time: O(1) + provider constructor time
        """
        provider_class = cls.get(name)
        instance = provider_class(config)
        
        logger.debug(f"Created provider: {name} with config: {config}")
        return instance
    
    @classmethod
    def list_available(cls) -> list[str]:
        """List all registered providers (debugging)"""
        return list(cls._providers.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear registry (testing only)"""
        cls._providers.clear()
