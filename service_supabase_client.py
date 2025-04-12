#!/usr/bin/env python3
"""
Service Supabase Client

This module provides helper functions for services to connect to the shared
Supabase database with appropriate service identifiers and connection settings.
"""

import os
import logging
from typing import Dict, Any, Optional
import functools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("service_supabase_client")

# Try to import supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.error("❌ Supabase package not installed. Install with: pip install supabase")

# Known services
VALID_SERVICES = [
    "core",
    "gis_service",
    "valuation_service",
    "sync_service",
    "analytics_service",
    "external_app"
]

# Service-specific environment variable patterns
SERVICE_ENV_PATTERNS = {
    "gis_service": "GIS_SUPABASE_",
    "valuation_service": "VALUATION_SUPABASE_",
    "sync_service": "SYNC_SUPABASE_",
    "analytics_service": "ANALYTICS_SUPABASE_",
    "external_app": "EXTERNAL_SUPABASE_"
}

@functools.lru_cache(maxsize=8)
def get_service_supabase_client(service_name: str, api_key: Optional[str] = None) -> Optional[Client]:
    """
    Get a Supabase client configured for a specific service.
    
    This function returns a Supabase client with appropriate headers and
    connection settings for the specified service. It also handles service-specific
    environment variables if available.
    
    Args:
        service_name: The name of the service (must be one of the valid services)
        api_key: Optional API key override (if not provided, will use environment variables)
        
    Returns:
        Configured Supabase client or None if configuration failed
    """
    if not SUPABASE_AVAILABLE:
        logger.error("Supabase package is not available")
        return None
    
    if service_name not in VALID_SERVICES:
        logger.error(f"Invalid service name: {service_name}")
        logger.info(f"Valid services are: {', '.join(VALID_SERVICES)}")
        return None
    
    # Check for service-specific environment variables first
    env_prefix = SERVICE_ENV_PATTERNS.get(service_name, "")
    url = None
    key = None
    
    if env_prefix:
        url = os.environ.get(f"{env_prefix}URL")
        key = api_key or os.environ.get(f"{env_prefix}KEY") or os.environ.get(f"{env_prefix}SERVICE_KEY")
    
    # Fall back to default environment variables if service-specific ones are not set
    if not url or not key:
        url = os.environ.get("SUPABASE_URL")
        key = api_key or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        logger.error(f"Missing Supabase URL or key for service: {service_name}")
        return None
    
    try:
        # Create the client
        client = create_client(url, key)
        
        # Set the application name to identify the service in audit logs
        client.postgrest.request_builder.session.headers.update({
            "X-Application-Name": service_name
        })
        
        # Execute setup query to set the application name in the connection
        try:
            client.sql(f"SET app.service_name TO '{service_name}';").execute()
        except Exception as e:
            logger.warning(f"Could not set app.service_name (not critical): {str(e)}")
        
        logger.info(f"Created Supabase client for service: {service_name}")
        return client
    except Exception as e:
        logger.error(f"Error creating Supabase client for service {service_name}: {str(e)}")
        return None

def get_core_client() -> Optional[Client]:
    """Get the Supabase client for the core service."""
    return get_service_supabase_client("core")

def get_gis_client() -> Optional[Client]:
    """Get the Supabase client for the GIS service."""
    return get_service_supabase_client("gis_service")

def get_valuation_client() -> Optional[Client]:
    """Get the Supabase client for the valuation service."""
    return get_service_supabase_client("valuation_service")

def get_sync_client() -> Optional[Client]:
    """Get the Supabase client for the synchronization service."""
    return get_service_supabase_client("sync_service")

def get_analytics_client() -> Optional[Client]:
    """Get the Supabase client for the analytics service."""
    return get_service_supabase_client("analytics_service")

def get_external_client() -> Optional[Client]:
    """Get the Supabase client for external applications."""
    return get_service_supabase_client("external_app")

def execute_query(client: Client, table: str, select: str = "*", 
                 filters: Optional[Dict[str, Any]] = None, 
                 order: Optional[str] = None,
                 limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a database query with a service-specific client.
    
    Args:
        client: The service-specific Supabase client
        table: Table or view name (can include schema)
        select: Fields to select
        filters: Query filters
        order: Order by clause
        limit: Result limit
        
    Returns:
        Query results or error information
    """
    if not client:
        return {
            "success": False,
            "error": "No valid client provided",
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

def listen_for_changes(client: Client, channel: str, callback) -> Any:
    """
    Listen for database changes on a specific channel.
    
    Args:
        client: The service-specific Supabase client
        channel: The channel to listen on (e.g., 'property_updates')
        callback: Function to call when an event is received
        
    Returns:
        Subscription object or None on error
    """
    try:
        # Set up realtime subscription
        return client.channel(channel).on('postgres_changes', callback).subscribe()
    except Exception as e:
        logger.error(f"Error setting up change listener on channel {channel}: {str(e)}")
        return None

def test_connection(service_name: str) -> bool:
    """
    Test the connection to Supabase for a specific service.
    
    Args:
        service_name: Name of the service to test
        
    Returns:
        True if connection is successful, False otherwise
    """
    client = get_service_supabase_client(service_name)
    if not client:
        return False
    
    try:
        # Try a simple query
        response = client.table('information_schema.tables').select('table_name').limit(1).execute()
        
        if hasattr(response, 'data'):
            logger.info(f"Successfully connected to Supabase as service: {service_name}")
            logger.info(f"Sample data: {response.data}")
            return True
        else:
            logger.error(f"Invalid response from Supabase for service: {service_name}")
            return False
    except Exception as e:
        logger.error(f"Error testing connection for service {service_name}: {str(e)}")
        return False

if __name__ == "__main__":
    # Simple test if this script is run directly
    import sys
    
    if len(sys.argv) > 1:
        service = sys.argv[1]
        success = test_connection(service)
        sys.exit(0 if success else 1)
    else:
        print("Usage: python service_supabase_client.py <service_name>")
        print(f"Valid services: {', '.join(VALID_SERVICES)}")
        sys.exit(1)