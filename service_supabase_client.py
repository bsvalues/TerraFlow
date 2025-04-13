"""
Service Supabase Client

This module provides a specialized Supabase client for services
that need their own dedicated connections with specific permissions.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Import connection pool for optimized connections
from supabase_connection_pool import get_client, release_client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ServiceSupabaseClient:
    """Service-oriented Supabase client with dedicated access and schema management."""
    
    def __init__(self, service_name: str, environment: str = "development"):
        """
        Initialize a service Supabase client.
        
        Args:
            service_name: The name of the service (used for schema access)
            environment: The Supabase environment to use
        """
        self.service_name = service_name
        self.environment = environment
        self.client = None
        self.schema = f"service_{service_name}"
        
        # Initialize the client
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize the Supabase client for this service."""
        if not SUPABASE_AVAILABLE:
            logger.warning(f"Supabase package not available for service {self.service_name}")
            return
        
        # Get environment variables with environment prefix
        env_prefix = f"{self.environment.upper()}_" if self.environment != "development" else ""
        url = os.environ.get(f"{env_prefix}SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        key = os.environ.get(f"{env_prefix}SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not url or not key:
            logger.error(f"Missing Supabase URL or service key for service {self.service_name} in environment {self.environment}")
            return
        
        try:
            # Get client from connection pool
            self.client = get_client(url, key, True)
            
            if not self.client:
                logger.error(f"Failed to initialize Supabase client for service {self.service_name}")
                return
            
            logger.info(f"Initialized Supabase client for service {self.service_name} in environment {self.environment}")
        except Exception as e:
            logger.error(f"Error initializing Supabase client for service {self.service_name}: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if the Supabase client is available."""
        return self.client is not None
    
    def close(self) -> None:
        """Release the client back to the connection pool."""
        if self.client:
            # Get environment variables with environment prefix
            env_prefix = f"{self.environment.upper()}_" if self.environment != "development" else ""
            url = os.environ.get(f"{env_prefix}SUPABASE_URL") or os.environ.get("SUPABASE_URL")
            key = os.environ.get(f"{env_prefix}SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
            
            if url and key:
                release_client(url, key, True)
            
            self.client = None
    
    def change_environment(self, environment: str) -> bool:
        """
        Change the environment for this client.
        
        Args:
            environment: The new environment name
            
        Returns:
            True if successful, False otherwise
        """
        if environment not in ["development", "training", "production"]:
            logger.error(f"Invalid environment: {environment}")
            return False
        
        # Close existing client
        self.close()
        
        # Update environment
        self.environment = environment
        
        # Reinitialize client
        self._init_client()
        
        return self.is_available()
    
    def table(self, table_name: str, schema: Optional[str] = None) -> Any:
        """
        Access a table in the database.
        
        Args:
            table_name: The name of the table
            schema: Optional schema override (defaults to service schema)
            
        Returns:
            Table query builder or None if client not available
        """
        if not self.is_available():
            logger.error(f"Supabase client not available for service {self.service_name}")
            return None
        
        # Use service schema by default
        schema_name = schema or self.schema
        
        try:
            return self.client.table(f"{schema_name}.{table_name}")
        except Exception as e:
            logger.error(f"Error accessing table {schema_name}.{table_name}: {str(e)}")
            return None
    
    def query(self, table_name: str, select: str = "*", filters: Optional[Dict[str, Any]] = None, 
              schema: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a query against a table.
        
        Args:
            table_name: The name of the table
            select: The columns to select
            filters: Optional filters to apply
            schema: Optional schema override
            
        Returns:
            List of records or None on error
        """
        table = self.table(table_name, schema)
        if not table:
            return None
        
        try:
            query = table.select(select)
            
            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    if isinstance(value, dict):
                        # Handle operator filters like {"gt": 100}
                        for op, op_value in value.items():
                            query = query.filter(key, op, op_value)
                    else:
                        # Simple equality filter
                        query = query.eq(key, value)
            
            # Execute query
            result = query.execute()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Query error: {result.error}")
            
            return result.data
        except Exception as e:
            logger.error(f"Error executing query on {table_name}: {str(e)}")
            return None
    
    def insert(self, table_name: str, record: Union[Dict[str, Any], List[Dict[str, Any]]], 
               schema: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Insert record(s) into a table.
        
        Args:
            table_name: The name of the table
            record: Record or list of records to insert
            schema: Optional schema override
            
        Returns:
            Inserted record(s) or None on error
        """
        table = self.table(table_name, schema)
        if not table:
            return None
        
        try:
            result = table.insert(record).execute()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Insert error: {result.error}")
            
            return result.data
        except Exception as e:
            logger.error(f"Error inserting into {table_name}: {str(e)}")
            return None
    
    def update(self, table_name: str, record_id: str, updates: Dict[str, Any], 
               id_column: str = "id", schema: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Update a record in a table.
        
        Args:
            table_name: The name of the table
            record_id: ID of the record to update
            updates: Fields to update
            id_column: Name of the ID column
            schema: Optional schema override
            
        Returns:
            Updated record or None on error
        """
        table = self.table(table_name, schema)
        if not table:
            return None
        
        try:
            result = table.update(updates).eq(id_column, record_id).execute()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Update error: {result.error}")
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating record in {table_name}: {str(e)}")
            return None
    
    def delete(self, table_name: str, record_id: str, id_column: str = "id", 
               schema: Optional[str] = None) -> bool:
        """
        Delete a record from a table.
        
        Args:
            table_name: The name of the table
            record_id: ID of the record to delete
            id_column: Name of the ID column
            schema: Optional schema override
            
        Returns:
            True on success, False on error
        """
        table = self.table(table_name, schema)
        if not table:
            return False
        
        try:
            result = table.delete().eq(id_column, record_id).execute()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Delete error: {result.error}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting record from {table_name}: {str(e)}")
            return False
    
    def execute_function(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a Supabase Edge Function.
        
        Args:
            function_name: The name of the function
            params: Optional parameters to pass to the function
            
        Returns:
            Function result or None on error
        """
        if not self.is_available():
            logger.error(f"Supabase client not available for service {self.service_name}")
            return None
        
        try:
            if params:
                result = self.client.functions.invoke(function_name, params)
            else:
                result = self.client.functions.invoke(function_name)
            
            return result
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {str(e)}")
            return None
    
    def get_user(self) -> Optional[Dict[str, Any]]:
        """
        Get the current user information.
        
        Returns:
            User information or None on error
        """
        if not self.is_available():
            logger.error(f"Supabase client not available for service {self.service_name}")
            return None
        
        try:
            result = self.client.auth.get_user()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Get user error: {result.error}")
            
            return result.user
        except Exception as e:
            logger.error(f"Error getting user information: {str(e)}")
            return None
    
    def storage_upload(self, bucket: str, path: str, file_data: bytes, 
                      content_type: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to storage.
        
        Args:
            bucket: Storage bucket name
            path: Path within the bucket
            file_data: File data to upload
            content_type: Optional content type
            
        Returns:
            Public URL of the file or None on error
        """
        if not self.is_available():
            logger.error(f"Supabase client not available for service {self.service_name}")
            return None
        
        try:
            options = {}
            if content_type:
                options["content_type"] = content_type
            
            result = self.client.storage.from_(bucket).upload(path, file_data, options)
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Upload error: {result.error}")
            
            public_url = self.client.storage.from_(bucket).get_public_url(path)
            return public_url
        except Exception as e:
            logger.error(f"Error uploading file to storage: {str(e)}")
            return None
    
    def storage_download(self, bucket: str, path: str) -> Optional[bytes]:
        """
        Download a file from storage.
        
        Args:
            bucket: Storage bucket name
            path: Path within the bucket
            
        Returns:
            File data or None on error
        """
        if not self.is_available():
            logger.error(f"Supabase client not available for service {self.service_name}")
            return None
        
        try:
            result = self.client.storage.from_(bucket).download(path)
            return result
        except Exception as e:
            logger.error(f"Error downloading file from storage: {str(e)}")
            return None
    
    def storage_delete(self, bucket: str, path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            bucket: Storage bucket name
            path: Path within the bucket
            
        Returns:
            True on success, False on error
        """
        if not self.is_available():
            logger.error(f"Supabase client not available for service {self.service_name}")
            return False
        
        try:
            result = self.client.storage.from_(bucket).remove([path])
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Delete error: {result.error}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting file from storage: {str(e)}")
            return False
    
    def __del__(self):
        """Clean up when object is deleted."""
        self.close()

# Factory function to create service clients
def get_service_client(service_name: str, environment: str = "development") -> ServiceSupabaseClient:
    """
    Get a service Supabase client.
    
    Args:
        service_name: The name of the service
        environment: The environment to use
        
    Returns:
        ServiceSupabaseClient instance
    """
    return ServiceSupabaseClient(service_name, environment)