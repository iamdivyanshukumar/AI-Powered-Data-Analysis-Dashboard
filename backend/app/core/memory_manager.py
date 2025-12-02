import threading
import time
import gc
import psutil
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Manages memory usage and performs garbage collection for long-running sessions.
    Implements intelligent caching and cleanup strategies.
    """
    
    def __init__(self, max_memory_mb: int = 1024, 
                 cleanup_interval: int = 300,  # 5 minutes
                 max_session_age: int = 3600):  # 1 hour
        """
        Initialize MemoryManager
        
        Args:
            max_memory_mb: Maximum memory usage in MB
            cleanup_interval: Cleanup interval in seconds
            max_session_age: Maximum session age in seconds
        """
        self.max_memory_mb = max_memory_mb
        self.cleanup_interval = cleanup_interval
        self.max_session_age = max_session_age
        
        # Tracking structures
        self.session_last_access: Dict[str, datetime] = {}
        self.session_memory_usage: Dict[str, float] = {}
        self.cached_objects: Dict[str, Dict[str, Any]] = {}
        
        # Threading
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = False
        
        logger.info(f"MemoryManager initialized with {max_memory_mb}MB limit")
    
    def start(self):
        """Start cleanup thread"""
        if self._cleanup_thread is None:
            self._running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
            logger.info("MemoryManager cleanup thread started")
    
    def stop(self):
        """Stop cleanup thread"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
            self._cleanup_thread = None
            logger.info("MemoryManager cleanup thread stopped")
    
    def register_session(self, session_id: str):
        """Register a session with the memory manager"""
        with self._lock:
            self.session_last_access[session_id] = datetime.now()
            self.session_memory_usage[session_id] = 0.0
            logger.debug(f"Registered session: {session_id}")
    
    def update_session_access(self, session_id: str, memory_used_mb: float = 0):
        """Update session last access time and memory usage"""
        with self._lock:
            if session_id in self.session_last_access:
                self.session_last_access[session_id] = datetime.now()
                if memory_used_mb > 0:
                    self.session_memory_usage[session_id] = memory_used_mb
                logger.debug(f"Updated session {session_id} access time")
    
    def unregister_session(self, session_id: str):
        """Unregister a session"""
        with self._lock:
            if session_id in self.session_last_access:
                del self.session_last_access[session_id]
            if session_id in self.session_memory_usage:
                del self.session_memory_usage[session_id]
            
            # Clear cached objects for this session
            self._clear_session_cache(session_id)
            logger.info(f"Unregistered session: {session_id}")
    
    def cache_object(self, session_id: str, cache_key: str, obj: Any, 
                    size_mb: float = None):
        """
        Cache an object with size estimation
        
        Args:
            session_id: Session identifier
            cache_key: Cache key
            obj: Object to cache
            size_mb: Estimated size in MB (calculated if None)
        """
        with self._lock:
            if session_id not in self.cached_objects:
                self.cached_objects[session_id] = {}
            
            # Estimate size if not provided
            if size_mb is None:
                size_mb = self._estimate_object_size(obj)
            
            # Check if we have space
            current_memory = self._get_total_memory_usage()
            if current_memory + size_mb > self.max_memory_mb:
                self._perform_emergency_cleanup()
            
            self.cached_objects[session_id][cache_key] = {
                'object': obj,
                'size_mb': size_mb,
                'created_at': datetime.now(),
                'last_accessed': datetime.now(),
                'access_count': 0
            }
            
            # Update session memory usage
            self.session_memory_usage[session_id] = \
                self.session_memory_usage.get(session_id, 0) + size_mb
            
            logger.debug(f"Cached object {cache_key} for session {session_id} "
                        f"({size_mb:.2f}MB)")
    
    def get_cached_object(self, session_id: str, cache_key: str) -> Optional[Any]:
        """Get cached object if it exists"""
        with self._lock:
            if (session_id in self.cached_objects and 
                cache_key in self.cached_objects[session_id]):
                
                cache_entry = self.cached_objects[session_id][cache_key]
                cache_entry['last_accessed'] = datetime.now()
                cache_entry['access_count'] += 1
                
                logger.debug(f"Retrieved cached object {cache_key} for session {session_id}")
                return cache_entry['object']
            
            return None
    
    def clear_cache(self, session_id: str = None, cache_key: str = None):
        """
        Clear cache entries
        
        Args:
            session_id: Clear cache for specific session (all if None)
            cache_key: Clear specific cache key (all if None)
        """
        with self._lock:
            if session_id is None:
                # Clear all cached objects
                memory_freed = sum(
                    entry['size_mb']
                    for session_cache in self.cached_objects.values()
                    for entry in session_cache.values()
                )
                self.cached_objects.clear()
                logger.info(f"Cleared all cache, freed {memory_freed:.2f}MB")
            
            elif cache_key is None:
                # Clear all cache for session
                if session_id in self.cached_objects:
                    memory_freed = sum(
                        entry['size_mb'] 
                        for entry in self.cached_objects[session_id].values()
                    )
                    del self.cached_objects[session_id]
                    logger.info(f"Cleared cache for session {session_id}, "
                               f"freed {memory_freed:.2f}MB")
            
            else:
                # Clear specific cache key
                if (session_id in self.cached_objects and 
                    cache_key in self.cached_objects[session_id]):
                    
                    memory_freed = self.cached_objects[session_id][cache_key]['size_mb']
                    del self.cached_objects[session_id][cache_key]
                    logger.info(f"Cleared cache key {cache_key} for session {session_id}, "
                               f"freed {memory_freed:.2f}MB")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        with self._lock:
            total_cached_mb = sum(
                entry['size_mb']
                for session_cache in self.cached_objects.values()
                for entry in session_cache.values()
            )
            
            total_sessions = len(self.session_last_access)
            active_sessions = len([
                sid for sid, last_access in self.session_last_access.items()
                if (datetime.now() - last_access).total_seconds() < 300  # 5 minutes
            ])
            
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / 1024**2
            
            return {
                'total_memory_mb': self.max_memory_mb,
                'cached_memory_mb': round(total_cached_mb, 2),
                'process_memory_mb': round(process_memory, 2),
                'available_memory_mb': round(self.max_memory_mb - total_cached_mb, 2),
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'cached_objects_count': sum(
                    len(session_cache) 
                    for session_cache in self.cached_objects.values()
                ),
                'cache_hit_rate': self._calculate_cache_hit_rate(),
                'last_cleanup': self._last_cleanup_time.isoformat() if hasattr(self, '_last_cleanup_time') else None
            }
    
    def _cleanup_loop(self):
        """Main cleanup loop"""
        while self._running:
            try:
                self._perform_scheduled_cleanup()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")
                time.sleep(60)  # Wait before retrying
    
    def _perform_scheduled_cleanup(self):
        """Perform scheduled cleanup operations"""
        with self._lock:
            # Clean up old sessions
            self._cleanup_old_sessions()
            
            # Clean up least recently used cache entries
            self._cleanup_lru_cache()
            
            # Force garbage collection
            self._force_garbage_collection()
            
            # Update last cleanup time
            self._last_cleanup_time = datetime.now()
            
            logger.debug("Performed scheduled cleanup")
    
    def _cleanup_old_sessions(self):
        """Clean up sessions that haven't been accessed recently"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, last_access in self.session_last_access.items():
            session_age = (current_time - last_access).total_seconds()
            if session_age > self.max_session_age:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            logger.info(f"Cleaning up old session: {session_id} "
                       f"(age: {session_age:.0f}s)")
            self.unregister_session(session_id)
    
    def _cleanup_lru_cache(self):
        """Clean up least recently used cache entries"""
        current_memory = self._get_total_memory_usage()
        
        if current_memory > self.max_memory_mb * 0.8:  # 80% threshold
            # Collect all cache entries
            all_entries = []
            for session_id, session_cache in self.cached_objects.items():
                for cache_key, entry in session_cache.items():
                    all_entries.append({
                        'session_id': session_id,
                        'cache_key': cache_key,
                        'last_accessed': entry['last_accessed'],
                        'size_mb': entry['size_mb'],
                        'access_count': entry['access_count']
                    })
            
            # Sort by last accessed (oldest first)
            all_entries.sort(key=lambda x: x['last_accessed'])
            
            # Remove entries until we're below threshold
            memory_to_free = current_memory - (self.max_memory_mb * 0.7)  # Target 70%
            memory_freed = 0
            
            for entry in all_entries:
                if memory_freed >= memory_to_free:
                    break
                
                self.clear_cache(entry['session_id'], entry['cache_key'])
                memory_freed += entry['size_mb']
            
            if memory_freed > 0:
                logger.info(f"Freed {memory_freed:.2f}MB from LRU cache")
    
    def _perform_emergency_cleanup(self):
        """Perform emergency cleanup when memory is critical"""
        logger.warning("Performing emergency memory cleanup")
        
        # Force garbage collection
        gc.collect()
        
        # Clear all cache
        self.clear_cache()
        
        # Clear Python's internal caches
        import sys
        if hasattr(sys, 'getallocatedblocks'):
            # Clear float cache
            import builtins
            if hasattr(builtins, '__dict__'):
                builtins.__dict__.clear()
        
        logger.info("Emergency cleanup completed")
    
    def _clear_session_cache(self, session_id: str):
        """Clear cache for a specific session"""
        if session_id in self.cached_objects:
            del self.cached_objects[session_id]
    
    def _get_total_memory_usage(self) -> float:
        """Get total memory usage from cache"""
        return sum(
            entry['size_mb']
            for session_cache in self.cached_objects.values()
            for entry in session_cache.values()
        )
    
    def _estimate_object_size(self, obj: Any) -> float:
        """Estimate object size in MB"""
        try:
            import sys
            size_bytes = sys.getsizeof(obj)
            
            # For complex objects, try to get a better estimate
            if hasattr(obj, '__dict__'):
                size_bytes += sum(
                    sys.getsizeof(v) for v in obj.__dict__.values()
                )
            elif isinstance(obj, (list, tuple, set)):
                size_bytes += sum(sys.getsizeof(item) for item in obj)
            elif isinstance(obj, dict):
                size_bytes += sum(
                    sys.getsizeof(k) + sys.getsizeof(v) 
                    for k, v in obj.items()
                )
            
            return size_bytes / 1024**2  # Convert to MB
            
        except Exception:
            # Fallback estimation
            return 0.1  # Assume 100KB as default
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_accesses = 0
        total_hits = 0
        
        for session_cache in self.cached_objects.values():
            for entry in session_cache.values():
                total_accesses += entry['access_count']
                if entry['access_count'] > 0:
                    total_hits += 1
        
        if total_accesses > 0:
            return round((total_hits / total_accesses) * 100, 1)
        return 0.0
    
    def _force_garbage_collection(self):
        """Force garbage collection with generation targeting"""
        # Collect generation 0
        collected0 = gc.collect(0)
        
        # Collect generation 1
        collected1 = gc.collect(1)
        
        # Collect generation 2 (full collection)
        collected2 = gc.collect(2)
        
        # Get garbage collection stats
        gc_stats = gc.get_stats()
        
        logger.debug(f"Garbage collection: gen0={collected0}, "
                    f"gen1={collected1}, gen2={collected2}")
        
        return {
            'collected_gen0': collected0,
            'collected_gen1': collected1,
            'collected_gen2': collected2,
            'gc_stats': gc_stats
        }
    
    def optimize_memory(self):
        """Optimize memory usage with aggressive cleanup"""
        logger.info("Starting memory optimization")
        
        # Force garbage collection
        gc.collect()
        
        # Clear all cache
        self.clear_cache()
        
        # Clear Python's internal caches
        import sys
        
        # Attempt to invalidate import caches (safer, portable)
        try:
            import importlib
            importlib.invalidate_caches()
        except Exception:
            pass
        
        # Clear various caches
        for module in list(sys.modules.values()):
            if hasattr(module, '__dict__'):
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, 'cache_clear'):
                        try:
                            attr.cache_clear()
                        except:
                            pass
        
        logger.info("Memory optimization completed")
        return self.get_memory_stats()