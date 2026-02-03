"""
Infrastructure - Cache Service
===============================
In-memory cache implementation (LSP compliance)
"""
from typing import Dict, Optional
from ..core.interfaces import ICacheService


class InMemoryCacheService(ICacheService):
    """
    Simple in-memory cache (SRP: Only handles caching)
    Thread-safe could be added via threading.Lock if needed
    """
    
    def __init__(self, max_size: int = 50):
        self._cache: Dict[str, any] = {}
        self._max_size = max_size
    
    def get(self, key: str) -> Optional[any]:
        """Retrieve cached value"""
        return self._cache.get(key)
    
    def set(self, key: str, value: any) -> None:
        """Store value in cache"""
        self._cache[key] = value
        
        # Auto-clean if exceeds max size
        if len(self._cache) > self._max_size:
            self.clean(self._max_size)
    
    def clean(self, max_size: int) -> None:
        """Clean old cache entries (FIFO)"""
        if len(self._cache) > max_size:
            keys_to_remove = list(self._cache.keys())[:-max_size // 2]
            for key in keys_to_remove:
                del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
