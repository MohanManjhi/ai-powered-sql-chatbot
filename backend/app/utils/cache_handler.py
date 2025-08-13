import hashlib
import json
import time
from typing import Any, Optional
from config import Config

class CacheHandler:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = Config.CACHE_TIMEOUT
    
    def _generate_key(self, data: Any) -> str:
        """Generate a cache key from data"""
        if isinstance(data, str):
            return hashlib.md5(data.encode()).hexdigest()
        elif isinstance(data, dict):
            # Sort keys for consistent hashing
            sorted_data = json.dumps(data, sort_keys=True)
            return hashlib.md5(sorted_data.encode()).hexdigest()
        else:
            return hashlib.md5(str(data).encode()).hexdigest()
    
    def get(self, key_data: Any) -> Optional[Any]:
        """Get cached data if it exists and is not expired"""
        key = self._generate_key(key_data)
        if key in self.cache:
            cached_item = self.cache[key]
            if time.time() - cached_item['timestamp'] < self.cache_timeout:
                return cached_item['data']
            else:
                # Remove expired cache
                del self.cache[key]
        return None
    
    def set(self, key_data: Any, value: Any) -> None:
        """Cache data with timestamp"""
        key = self._generate_key(key_data)
        self.cache[key] = {
            'data': value,
            'timestamp': time.time()
        }
        
        # Clean up old cache entries if cache gets too large
        if len(self.cache) > 1000:
            self._cleanup_expired()
    
    def _cleanup_expired(self) -> None:
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self.cache.items()
            if current_time - item['timestamp'] > self.cache_timeout
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        current_time = time.time()
        active_cache = {
            key: item for key, item in self.cache.items()
            if current_time - item['timestamp'] < self.cache_timeout
        }
        
        return {
            'total_entries': len(self.cache),
            'active_entries': len(active_cache),
            'expired_entries': len(self.cache) - len(active_cache),
            'cache_size_mb': len(json.dumps(self.cache)) / (1024 * 1024)
        }

# Global cache instance
cache_handler = CacheHandler()

