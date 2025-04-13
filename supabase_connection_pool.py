"""
Supabase Connection Pool

This module provides a connection pool for Supabase clients to optimize
resource usage and prevent opening too many connections.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, Tuple

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SupabaseConnectionPool:
    """Connection pool for Supabase clients."""
    
    def __init__(self, max_size: int = 5, idle_timeout: int = 300, check_interval: int = 60):
        """
        Initialize the connection pool.
        
        Args:
            max_size: Maximum number of connections to keep in the pool
            idle_timeout: Seconds after which an idle connection is closed
            check_interval: Seconds between checking for idle connections
        """
        self._pool: Dict[str, Tuple[Client, float]] = {}  # Maps connection_id to (client, last_used_time)
        self._max_size = max_size
        self._idle_timeout = idle_timeout
        self._check_interval = check_interval
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = False
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start the cleanup thread to remove idle connections."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self._cleanup_thread.start()
    
    def _cleanup_worker(self):
        """Worker function to clean up idle connections."""
        while self._running:
            time.sleep(self._check_interval)
            self._remove_idle_connections()
    
    def _remove_idle_connections(self):
        """Remove idle connections from the pool."""
        current_time = time.time()
        with self._lock:
            to_remove = []
            for connection_id, (_, last_used) in self._pool.items():
                if current_time - last_used > self._idle_timeout:
                    to_remove.append(connection_id)
            
            for connection_id in to_remove:
                logger.info(f"Removing idle connection: {connection_id}")
                del self._pool[connection_id]
    
    def get_connection(self, url: str, key: str, service_role: bool = False) -> Optional[Client]:
        """
        Get a Supabase client from the pool or create a new one.
        
        Args:
            url: Supabase URL
            key: Supabase API key or service role key
            service_role: Whether to use the service role key
            
        Returns:
            Supabase client or None if not available
        """
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase package is not installed")
            return None
        
        # Create a connection ID from the URL and key (service role)
        connection_id = f"{url}:{key}:{service_role}"
        
        # Check if we already have a connection in the pool
        with self._lock:
            if connection_id in self._pool:
                client, _ = self._pool[connection_id]
                # Update last used time
                self._pool[connection_id] = (client, time.time())
                return client
            
            # Check if we need to remove the oldest connection when at max capacity
            if len(self._pool) >= self._max_size:
                oldest_id = None
                oldest_time = float('inf')
                for conn_id, (_, last_used) in self._pool.items():
                    if last_used < oldest_time:
                        oldest_time = last_used
                        oldest_id = conn_id
                
                if oldest_id:
                    logger.info(f"Removing oldest connection to make room: {oldest_id}")
                    del self._pool[oldest_id]
            
            # Create a new connection
            try:
                logger.info(f"Creating new Supabase connection: {url}")
                client = create_client(url, key)
                self._pool[connection_id] = (client, time.time())
                return client
            except Exception as e:
                logger.error(f"Error creating Supabase client: {str(e)}")
                return None
    
    def release_connection(self, url: str, key: str, service_role: bool = False):
        """
        Release a connection back to the pool.
        
        Args:
            url: Supabase URL
            key: Supabase API key or service role key
            service_role: Whether to use the service role key
        """
        # In this implementation, we don't actually need to do anything
        # as the connection is already in the pool with its last used time
        # Just update the last used time
        connection_id = f"{url}:{key}:{service_role}"
        with self._lock:
            if connection_id in self._pool:
                client, _ = self._pool[connection_id]
                self._pool[connection_id] = (client, time.time())
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            self._running = False
            self._pool.clear()
    
    def __del__(self):
        """Clean up when the pool is garbage collected."""
        self.close_all()

# Create a global connection pool
connection_pool = SupabaseConnectionPool()

def get_client(url: str, key: str, service_role: bool = False) -> Optional[Client]:
    """
    Get a Supabase client from the connection pool.
    
    Args:
        url: Supabase URL
        key: Supabase API key or service role key
        service_role: Whether to use the service role key
        
    Returns:
        Supabase client or None if not available
    """
    return connection_pool.get_connection(url, key, service_role)

def release_client(url: str, key: str, service_role: bool = False):
    """
    Release a Supabase client back to the connection pool.
    
    Args:
        url: Supabase URL
        key: Supabase API key or service role key
        service_role: Whether to use the service role key
    """
    connection_pool.release_connection(url, key, service_role)

def close_all_connections():
    """Close all connections in the pool."""
    connection_pool.close_all()