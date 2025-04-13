"""
Supabase Connection Pool

This module provides a connection pool for Supabase clients to improve
performance and resource usage.
"""

import os
import time
import logging
import threading
from typing import Dict, Optional, Any, List, Tuple
from collections import defaultdict

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thread-local storage for connections
thread_local = threading.local()

# Global connection pools for each environment
# Format: {(url, key): {"client": client, "last_used": timestamp, "in_use": count}}
connection_pools = {}
connection_pools_lock = threading.RLock()

# Configuration
MAX_POOL_SIZE = 10  # Maximum number of clients per pool
MAX_IDLE_TIME = 300  # Maximum idle time in seconds before a client is removed
CHECK_INTERVAL = 60  # Interval in seconds to check for expired clients

def get_client(url: str, key: str) -> Optional[Client]:
    """
    Get a Supabase client from the connection pool or create a new one.
    
    Args:
        url: Supabase URL
        key: Supabase API key or service key
        
    Returns:
        Supabase client or None if not available
    """
    if not SUPABASE_AVAILABLE:
        logger.warning("Supabase package is not installed")
        return None
    
    if not url or not key:
        logger.error("Supabase URL and key are required")
        return None
    
    # Create a pool key based on URL and key
    pool_key = (url, key)
    
    # Check if we already have a client for this thread
    if hasattr(thread_local, 'client_cache') and pool_key in thread_local.client_cache:
        logger.debug(f"Using thread-local client for {url}")
        
        # Update last used time in the global pool
        with connection_pools_lock:
            if pool_key in connection_pools:
                connection_pools[pool_key]["last_used"] = time.time()
                connection_pools[pool_key]["in_use"] += 1
        
        return thread_local.client_cache[pool_key]
    
    # Check if we have a client in the global pool
    with connection_pools_lock:
        if pool_key in connection_pools:
            client_info = connection_pools[pool_key]
            client_info["last_used"] = time.time()
            client_info["in_use"] += 1
            logger.debug(f"Using pooled client for {url}")
            
            # Store in thread-local storage
            if not hasattr(thread_local, 'client_cache'):
                thread_local.client_cache = {}
            thread_local.client_cache[pool_key] = client_info["client"]
            
            return client_info["client"]
        
        # Create a new client
        try:
            logger.info(f"Creating new Supabase client for {url}")
            client = create_client(url, key)
            
            # Store in thread-local storage
            if not hasattr(thread_local, 'client_cache'):
                thread_local.client_cache = {}
            thread_local.client_cache[pool_key] = client
            
            # Store in global pool
            connection_pools[pool_key] = {
                "client": client,
                "last_used": time.time(),
                "in_use": 1
            }
            
            # Check if we need to clean up the pool
            if len(connection_pools) > MAX_POOL_SIZE:
                _cleanup_pool()
            
            return client
        except Exception as e:
            logger.error(f"Error creating Supabase client: {str(e)}")
            return None

def release_client(url: str, key: str) -> bool:
    """
    Release a Supabase client back to the pool.
    
    Args:
        url: Supabase URL
        key: Supabase API key or service key
        
    Returns:
        True if successful, False otherwise
    """
    pool_key = (url, key)
    
    with connection_pools_lock:
        if pool_key in connection_pools:
            connection_pools[pool_key]["in_use"] -= 1
            logger.debug(f"Released client for {url}")
            return True
    
    return False

def _cleanup_pool():
    """
    Clean up the connection pool by removing expired clients.
    """
    now = time.time()
    
    with connection_pools_lock:
        # Find expired clients
        expired_keys = []
        for key, info in connection_pools.items():
            if info["in_use"] <= 0 and now - info["last_used"] > MAX_IDLE_TIME:
                expired_keys.append(key)
        
        # Remove expired clients
        for key in expired_keys:
            url, api_key = key
            logger.info(f"Removing expired client for {url}")
            del connection_pools[key]
            
            # Remove from thread-local storage
            for thread_id, thread_cache in _get_all_thread_caches().items():
                if key in thread_cache:
                    del thread_cache[key]

def _get_all_thread_caches() -> Dict[int, Dict[Tuple[str, str], Client]]:
    """
    Get all thread-local client caches.
    
    Returns:
        Dictionary mapping thread IDs to their client caches
    """
    # This is a bit of a hack, but it's the only way to access thread-local storage of other threads
    thread_caches = {}
    
    for thread in threading.enumerate():
        if hasattr(thread, '_Thread__target') and thread._Thread__target is not None:
            thread_id = thread.ident
            if hasattr(thread_local, 'client_cache'):
                thread_caches[thread_id] = thread_local.client_cache
    
    return thread_caches

def get_pool_stats() -> Dict[str, Any]:
    """
    Get statistics about the connection pool.
    
    Returns:
        Dictionary with pool statistics
    """
    with connection_pools_lock:
        stats = {
            "total_pools": len(connection_pools),
            "total_clients": sum(1 for info in connection_pools.values() if info["client"] is not None),
            "active_clients": sum(info["in_use"] for info in connection_pools.values() if info["client"] is not None),
            "idle_clients": sum(1 for info in connection_pools.values() if info["client"] is not None and info["in_use"] <= 0),
            "pools": []
        }
        
        for (url, key), info in connection_pools.items():
            stats["pools"].append({
                "url": url,
                "in_use": info["in_use"],
                "idle_time": time.time() - info["last_used"]
            })
        
        return stats

# Start a background thread to clean up the pool periodically
def _cleanup_thread():
    """
    Background thread to clean up the connection pool periodically.
    """
    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            _cleanup_pool()
        except Exception as e:
            logger.error(f"Error cleaning up connection pool: {str(e)}")

# Start the cleanup thread when the module is imported
cleanup_thread = threading.Thread(target=_cleanup_thread, daemon=True)
cleanup_thread.start()