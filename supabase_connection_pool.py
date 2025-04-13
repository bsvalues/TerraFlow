"""
Supabase Connection Pool

This module provides a connection pool for Supabase clients
to optimize performance and avoid creating too many connections.
"""

import os
import time
import logging
import threading
import queue
from typing import Dict, Any, Optional, List, Tuple, Set, Callable

# Import Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thread-local storage for connections
_thread_local = threading.local()

class ConnectionPoolManager:
    """
    Manages a pool of Supabase client connections.
    """
    
    def __init__(self, max_connections: int = 10, connection_timeout: int = 60):
        """
        Initialize the connection pool manager.
        
        Args:
            max_connections: Maximum number of connections in the pool
            connection_timeout: Timeout for idle connections in seconds
        """
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.pool = queue.Queue(maxsize=max_connections)
        self.active_connections: Set[Client] = set()
        self.connection_timestamps: Dict[Client, float] = {}
        self.lock = threading.RLock()
        self.cleanup_thread = None
        self.stop_cleanup = threading.Event()
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self) -> None:
        """Start the thread that cleans up idle connections."""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.stop_cleanup.clear()
            self.cleanup_thread = threading.Thread(target=self._cleanup_idle_connections, daemon=True)
            self.cleanup_thread.start()
            logger.debug("Started connection pool cleanup thread")
    
    def _cleanup_idle_connections(self) -> None:
        """Periodically clean up idle connections."""
        while not self.stop_cleanup.is_set():
            # Sleep for a while
            time.sleep(10)
            
            try:
                # Clean up idle connections
                current_time = time.time()
                with self.lock:
                    idle_connections = []
                    for conn, timestamp in self.connection_timestamps.items():
                        if current_time - timestamp > self.connection_timeout:
                            idle_connections.append(conn)
                    
                    for conn in idle_connections:
                        if conn in self.active_connections:
                            # If connection is still active but idle, don't remove it yet
                            continue
                        
                        # Remove from pool and dictionaries
                        try:
                            self.connection_timestamps.pop(conn, None)
                            # Can't easily remove from queue, so we'll let it be garbage collected
                            logger.debug(f"Removed idle connection from pool")
                        except Exception as e:
                            logger.warning(f"Error removing idle connection: {str(e)}")
            except Exception as e:
                logger.warning(f"Error in connection pool cleanup: {str(e)}")
    
    def get_connection(self, url: Optional[str] = None, key: Optional[str] = None) -> Optional[Client]:
        """
        Get a connection from the pool.
        
        Args:
            url: Supabase URL (optional, will use SUPABASE_URL from environment if not provided)
            key: Supabase API key (optional, will use SUPABASE_KEY from environment if not provided)
            
        Returns:
            Supabase client or None if not available
        """
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase package not installed, cannot create client")
            return None
        
        # Get URL and key from environment if not provided
        url = url or os.environ.get("SUPABASE_URL")
        key = key or os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            logger.warning("Supabase URL or key not set, cannot create client")
            return None
        
        # Check thread-local storage first
        if hasattr(_thread_local, 'supabase_client'):
            logger.debug("Using thread-local Supabase client")
            client = _thread_local.supabase_client
            
            # Update timestamp to prevent cleanup
            with self.lock:
                self.connection_timestamps[client] = time.time()
                self.active_connections.add(client)
            
            return client
        
        # Try to get a connection from the pool
        try:
            with self.lock:
                if not self.pool.empty():
                    client = self.pool.get(block=False)
                    logger.debug("Got Supabase client from pool")
                    
                    # Update timestamp and add to active connections
                    self.connection_timestamps[client] = time.time()
                    self.active_connections.add(client)
                    
                    # Store in thread-local storage
                    _thread_local.supabase_client = client
                    
                    return client
        except queue.Empty:
            pass
        
        # If pool is empty and we haven't reached max connections, create a new one
        with self.lock:
            if len(self.active_connections) < self.max_connections:
                try:
                    client = create_client(url, key)
                    logger.debug("Created new Supabase client")
                    
                    # Update timestamp and add to active connections
                    self.connection_timestamps[client] = time.time()
                    self.active_connections.add(client)
                    
                    # Store in thread-local storage
                    _thread_local.supabase_client = client
                    
                    return client
                except Exception as e:
                    logger.error(f"Error creating Supabase client: {str(e)}")
                    return None
        
        # If we've reached max connections, log warning and return None
        logger.warning("Maximum number of Supabase connections reached")
        return None
    
    def release_connection(self, client: Optional[Client] = None) -> None:
        """
        Release a connection back to the pool.
        
        Args:
            client: Supabase client to release (optional, will use thread-local client if not provided)
        """
        if not client and hasattr(_thread_local, 'supabase_client'):
            client = _thread_local.supabase_client
            delattr(_thread_local, 'supabase_client')
        
        if not client:
            return
        
        with self.lock:
            # Remove from active connections
            self.active_connections.discard(client)
            
            # Update timestamp
            self.connection_timestamps[client] = time.time()
            
            # Add back to pool
            try:
                self.pool.put(client, block=False)
                logger.debug("Released Supabase client back to pool")
            except queue.Full:
                logger.debug("Connection pool is full, discarding client")
    
    def close_all_connections(self) -> None:
        """Close all connections in the pool."""
        with self.lock:
            # Stop cleanup thread
            self.stop_cleanup.set()
            if self.cleanup_thread and self.cleanup_thread.is_alive():
                self.cleanup_thread.join(timeout=1)
            
            # Clear active connections
            self.active_connections.clear()
            
            # Clear connection timestamps
            self.connection_timestamps.clear()
            
            # Clear pool
            while not self.pool.empty():
                try:
                    self.pool.get(block=False)
                except queue.Empty:
                    break
            
            logger.info("Closed all Supabase connections")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the connection pool.
        
        Returns:
            Dictionary with pool statistics
        """
        with self.lock:
            return {
                "max_connections": self.max_connections,
                "active_connections": len(self.active_connections),
                "available_connections": self.pool.qsize(),
                "connection_timeout": self.connection_timeout,
                "cleanup_thread_active": bool(self.cleanup_thread and self.cleanup_thread.is_alive())
            }


# Global connection pool instance
_connection_pool = ConnectionPoolManager()

def get_connection(url: Optional[str] = None, key: Optional[str] = None) -> Optional[Client]:
    """
    Get a Supabase client from the connection pool.
    
    Args:
        url: Supabase URL (optional, will use SUPABASE_URL from environment if not provided)
        key: Supabase API key (optional, will use SUPABASE_KEY from environment if not provided)
        
    Returns:
        Supabase client or None if not available
    """
    return _connection_pool.get_connection(url, key)

def release_connection(client: Optional[Client] = None) -> None:
    """
    Release a Supabase client back to the connection pool.
    
    Args:
        client: Supabase client to release (optional, will use thread-local client if not provided)
    """
    _connection_pool.release_connection(client)

def close_all_connections() -> None:
    """Close all connections in the pool."""
    _connection_pool.close_all_connections()

def get_pool_stats() -> Dict[str, Any]:
    """
    Get statistics about the connection pool.
    
    Returns:
        Dictionary with pool statistics
    """
    return _connection_pool.get_pool_stats()

def with_connection(func: Callable) -> Callable:
    """
    Decorator for functions that need a Supabase connection.
    
    The decorated function will receive a Supabase client as its first argument.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        client = get_connection()
        if not client:
            raise ValueError("Could not get Supabase connection")
        
        try:
            return func(client, *args, **kwargs)
        finally:
            release_connection(client)
    
    return wrapper