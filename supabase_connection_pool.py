#!/usr/bin/env python3
"""
Supabase Connection Pool Manager

This module provides connection pooling functionality for efficient database access
across multiple services, microservices, and third-party applications.

It works in conjunction with PgBouncer, which must be configured separately
in your Supabase project via the Database Pool settings in the Supabase Dashboard.
"""

import os
import time
import logging
import threading
import queue
import weakref
from typing import Dict, Any, Optional, List, Callable, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("supabase_pool")

# Try to import supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.error("❌ Supabase package not installed. Install with: pip install supabase")

# Import our service client
from service_supabase_client import get_service_supabase_client

# Default pool settings
DEFAULT_POOL_CONFIG = {
    "max_size": 10,              # Maximum number of connections in the pool
    "min_size": 2,               # Minimum number of connections in the pool
    "max_idle_time": 60,         # Maximum time (seconds) a connection can be idle before being closed
    "connection_timeout": 10,    # Timeout (seconds) for getting a connection from the pool
    "max_queue_size": 20,        # Maximum number of waiting requests
    "acquire_retry_count": 3     # Number of times to retry acquiring a connection
}

# Connection pools by service
_connection_pools: Dict[str, 'ConnectionPool'] = {}
_pool_lock = threading.RLock()


class PooledConnection:
    """A wrapped Supabase connection from the pool."""
    
    def __init__(self, client: Client, pool: 'ConnectionPool'):
        """Initialize with a Supabase client and reference to the parent pool."""
        self.client = client
        self.pool = pool
        self.last_used = time.time()
        self.in_use = True
        
        # Run a simple query to verify connection
        self._verify_connection()
    
    def _verify_connection(self) -> bool:
        """Verify that the connection is still valid."""
        try:
            self.client.table('information_schema.tables').select('table_name').limit(1).execute()
            return True
        except Exception as e:
            logger.warning(f"Connection verification failed: {str(e)}")
            return False
    
    def release(self) -> None:
        """Release the connection back to the pool."""
        if self.in_use:
            self.in_use = False
            self.last_used = time.time()
            self.pool._release_connection(self)


class PoolConnection:
    """Context manager for using a connection from the pool."""
    
    def __init__(self, pool: 'ConnectionPool'):
        """Initialize with a connection pool."""
        self.pool = pool
        self.connection = None
    
    def __enter__(self) -> Optional[Client]:
        """Get a connection from the pool."""
        self.connection = self.pool.get_connection()
        return self.connection.client if self.connection else None
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release the connection back to the pool."""
        if self.connection:
            self.connection.release()


class ConnectionPool:
    """Connection pool for Supabase clients."""
    
    def __init__(self, service_name: str, config: Dict[str, Any] = None):
        """Initialize the connection pool."""
        self.service_name = service_name
        self.config = {**DEFAULT_POOL_CONFIG, **(config or {})}
        
        self._pool: List[PooledConnection] = []
        self._in_use_count = 0
        self._pending_queue = queue.Queue(maxsize=self.config["max_queue_size"])
        self._lock = threading.RLock()
        
        # Create initial connections
        for _ in range(self.config["min_size"]):
            self._create_connection()
        
        # Start maintenance thread
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_worker,
            daemon=True
        )
        self._maintenance_thread.start()
    
    def get_connection(self) -> Optional[PooledConnection]:
        """Get a connection from the pool."""
        # Try to get connection from the pool
        conn = self._get_available_connection()
        if conn:
            return conn
        
        # If we need to create a new connection
        with self._lock:
            if len(self._pool) + self._in_use_count < self.config["max_size"]:
                return self._create_connection()
        
        # Wait for a connection
        try:
            # Use a pending queue with timeout
            queued_event = threading.Event()
            self._pending_queue.put(queued_event, block=True, timeout=self.config["connection_timeout"])
            
            # Wait for connection to become available
            if queued_event.wait(self.config["connection_timeout"]):
                return self._get_available_connection()
            else:
                logger.error(f"Timeout waiting for connection to service {self.service_name}")
                return None
        except queue.Full:
            logger.error(f"Connection queue is full for service {self.service_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting connection from pool: {str(e)}")
            return None
    
    def _get_available_connection(self) -> Optional[PooledConnection]:
        """Get an available connection from the pool."""
        with self._lock:
            if not self._pool:
                return None
            
            # Get a connection and mark it as in use
            conn = self._pool.pop(0)
            conn.in_use = True
            conn.last_used = time.time()
            self._in_use_count += 1
            
            return conn
    
    def _create_connection(self) -> Optional[PooledConnection]:
        """Create a new connection."""
        with self._lock:
            for attempt in range(self.config["acquire_retry_count"]):
                try:
                    client = get_service_supabase_client(self.service_name)
                    if client:
                        conn = PooledConnection(client, self)
                        conn.in_use = True
                        self._in_use_count += 1
                        return conn
                except Exception as e:
                    logger.error(f"Error creating connection (attempt {attempt+1}): {str(e)}")
                    time.sleep(0.5)  # Short delay before retry
            
            logger.error(f"Failed to create connection after {self.config['acquire_retry_count']} attempts")
            return None
    
    def _release_connection(self, conn: PooledConnection) -> None:
        """Release a connection back to the pool."""
        with self._lock:
            # Verify the connection is still good
            try:
                if conn._verify_connection():
                    self._pool.append(conn)
                else:
                    logger.warning("Discarding invalid connection")
            except Exception as e:
                logger.warning(f"Error verifying connection: {str(e)}")
            
            self._in_use_count -= 1
            
            # Notify a waiting request if any
            try:
                if not self._pending_queue.empty():
                    event = self._pending_queue.get_nowait()
                    event.set()
            except Exception as e:
                logger.warning(f"Error notifying waiting request: {str(e)}")
    
    def _maintenance_worker(self) -> None:
        """Background thread to manage the connection pool."""
        while True:
            try:
                # Sleep for a bit
                time.sleep(30)
                
                with self._lock:
                    # Close idle connections if we have more than min_size
                    current_time = time.time()
                    idle_timeout = self.config["max_idle_time"]
                    
                    # Only keep non-expired connections
                    active_pool = []
                    for conn in self._pool:
                        if len(active_pool) < self.config["min_size"]:
                            # Keep min_size connections
                            active_pool.append(conn)
                        elif current_time - conn.last_used < idle_timeout:
                            # Keep non-idle connections
                            active_pool.append(conn)
                        else:
                            # Connection is idle, let it be garbage collected
                            logger.debug(f"Closing idle connection for service {self.service_name}")
                    
                    # Update the pool
                    self._pool = active_pool
                    
                    # Create connections if below min_size
                    if len(self._pool) + self._in_use_count < self.config["min_size"]:
                        needed = self.config["min_size"] - (len(self._pool) + self._in_use_count)
                        logger.debug(f"Creating {needed} new connections to maintain min_size")
                        for _ in range(needed):
                            conn = self._create_connection()
                            if conn:
                                conn.in_use = False
                                self._in_use_count -= 1
                                self._pool.append(conn)
                    
                    # Log pool stats
                    logger.debug(f"Pool stats for {self.service_name}: "
                                 f"available={len(self._pool)}, "
                                 f"in_use={self._in_use_count}, "
                                 f"waiting={self._pending_queue.qsize()}")
            except Exception as e:
                logger.error(f"Error in maintenance worker: {str(e)}")


def get_connection_pool(service_name: str, config: Dict[str, Any] = None) -> ConnectionPool:
    """
    Get or create a connection pool for a service.
    
    Args:
        service_name: Name of the service
        config: Optional configuration overrides
        
    Returns:
        A connection pool for the service
    """
    with _pool_lock:
        if service_name not in _connection_pools:
            _connection_pools[service_name] = ConnectionPool(service_name, config)
        return _connection_pools[service_name]


def with_connection(service_name: str):
    """
    Decorator to provide a database connection to a function.
    
    Example:
        @with_connection('gis_service')
        def get_property(client, property_id):
            result = client.table('properties').select('*').eq('id', property_id).execute()
            return result.data[0] if result.data else None
    
    Args:
        service_name: Name of the service to connect as
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            pool = get_connection_pool(service_name)
            with PoolConnection(pool) as client:
                if not client:
                    raise Exception(f"Could not get connection for service {service_name}")
                return func(client, *args, **kwargs)
        return wrapper
    return decorator


def get_supabase_client(service_name: str = "default") -> Optional[Client]:
    """
    Get a Supabase client from the connection pool.
    
    Args:
        service_name: Name of the service (defaults to "default")
        
    Returns:
        A Supabase client or None if unavailable
    """
    if not SUPABASE_AVAILABLE:
        logger.error("Supabase package not installed")
        return None
    
    pool = get_connection_pool(service_name)
    conn = pool.get_connection()
    
    if conn:
        client = conn.client
        
        # Create a finalizer to release the connection when the client is garbage collected
        def release_callback(weak_conn=weakref.ref(conn)):
            connection = weak_conn()
            if connection:
                connection.release()
        
        # Attach the connection and release method to the client
        setattr(client, "_pooled_connection", conn)
        setattr(client, "release", conn.release)
        
        return client
    
    return None


def get_stats() -> Dict[str, Dict[str, Any]]:
    """
    Get statistics for all connection pools.
    
    Returns:
        Dictionary with pool statistics by service
    """
    stats = {}
    with _pool_lock:
        for service_name, pool in _connection_pools.items():
            with pool._lock:
                stats[service_name] = {
                    "available": len(pool._pool),
                    "in_use": pool._in_use_count,
                    "waiting": pool._pending_queue.qsize(),
                    "max_size": pool.config["max_size"],
                    "min_size": pool.config["min_size"]
                }
    return stats


def execute_query(service_name: str, table: str, select: str = "*", 
                 filters: Optional[Dict[str, Any]] = None,
                 order: Optional[str] = None,
                 limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a query using a pooled connection.
    
    Args:
        service_name: Name of the service to connect as
        table: Table name
        select: Select clause
        filters: Query filters
        order: Order by clause
        limit: Result limit
        
    Returns:
        Query results
    """
    pool = get_connection_pool(service_name)
    
    with PoolConnection(pool) as client:
        if not client:
            return {
                "success": False,
                "error": f"Could not get connection for service {service_name}",
                "data": None
            }
        
        try:
            query = client.table(table).select(select)
            
            # Apply filters if provided
            if filters:
                for field, value in filters.items():
                    if isinstance(value, dict):
                        # Handle operators like eq, gt, lt, etc.
                        for op, op_value in value.items():
                            if op == "eq":
                                query = query.eq(field, op_value)
                            elif op == "neq":
                                query = query.neq(field, op_value)
                            elif op == "gt":
                                query = query.gt(field, op_value)
                            elif op == "gte":
                                query = query.gte(field, op_value)
                            elif op == "lt":
                                query = query.lt(field, op_value)
                            elif op == "lte":
                                query = query.lte(field, op_value)
                            elif op == "in":
                                query = query.in_(field, op_value)
                            elif op == "is":
                                query = query.is_(field, op_value)
                    else:
                        # Simple equality filter
                        query = query.eq(field, value)
            
            # Apply order if provided
            if order:
                query = query.order(order)
            
            # Apply limit if provided
            if limit is not None:
                query = query.limit(limit)
            
            # Execute the query
            response = query.execute()
            
            return {
                "success": True,
                "data": response.data,
                "count": len(response.data) if isinstance(response.data, list) else 0,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error executing query on table {table}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

if __name__ == "__main__":
    # Simple test if this script is run directly
    import sys
    
    if len(sys.argv) > 1:
        service = sys.argv[1]
        
        # Test the connection pool
        pool = get_connection_pool(service)
        
        @with_connection(service)
        def test_query(client, table="information_schema.tables"):
            logger.info(f"Testing query on {table}")
            result = client.table(table).select("table_name").limit(5).execute()
            return result.data
        
        # Run a test query
        try:
            data = test_query()
            logger.info(f"Query result: {data}")
            logger.info(f"Pool stats: {get_stats()}")
            
            # Run multiple queries in parallel to test pool
            logger.info("Testing parallel queries...")
            import concurrent.futures
            
            def parallel_test(i):
                result = test_query()
                return f"Query {i}: {len(result)} results"
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(parallel_test, i) for i in range(20)]
                for future in concurrent.futures.as_completed(futures):
                    logger.info(future.result())
            
            logger.info(f"Final pool stats: {get_stats()}")
            
            sys.exit(0)
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            sys.exit(1)
    else:
        print("Usage: python supabase_connection_pool.py <service_name>")
        sys.exit(1)