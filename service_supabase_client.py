"""
Service-Specific Supabase Client

This module provides a Supabase client for a specific service or component,
which uses the connection pool for efficient connection management.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List, Tuple, Union, TypeVar, Generic, cast

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from supabase_connection_pool import get_connection, release_connection, with_connection
from supabase_env_manager import get_environment_variables

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')
U = TypeVar('U')

class ServiceSupabaseClient:
    """
    Service-specific Supabase client class that uses the connection pool.
    """
    
    def __init__(self, service_name: str, environment: Optional[str] = None):
        """
        Initialize the service-specific Supabase client.
        
        Args:
            service_name: Name of the service or component
            environment: Environment name (development, training, production)
        """
        self.service_name = service_name
        self.environment = environment
        self.client = None
        
        logger.info(f"Initialized ServiceSupabaseClient for {service_name}")
    
    def _get_client(self) -> Optional[Client]:
        """
        Get a Supabase client from the connection pool.
        
        Returns:
            Supabase client or None if not available
        """
        # Get environment variables
        env_vars = get_environment_variables(self.environment)
        
        if not env_vars["configured"]:
            logger.warning(f"Supabase environment {self.environment} not configured")
            return None
        
        # Get client from connection pool
        client = get_connection(env_vars["url"], env_vars["key"])
        
        return client
    
    def execute_query(self, table: str, 
                      query_builder: Optional[callable] = None, 
                      **kwargs) -> Dict[str, Any]:
        """
        Execute a query on a Supabase table.
        
        Args:
            table: Table name
            query_builder: Function that takes a table query and returns a modified query
            **kwargs: Additional arguments for the query builder
            
        Returns:
            Dictionary with query results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"data": [], "error": "Failed to get Supabase client"}
        
        try:
            # Start with the table query
            query = client.table(table)
            
            # Apply query builder if provided
            if query_builder:
                query = query_builder(query, **kwargs)
            else:
                # Default select all
                query = query.select("*")
            
            # Execute the query
            response = query.execute()
            
            result = {
                "data": response.data,
                "error": response.error
            }
            
            return result
        except Exception as e:
            logger.error(f"Error executing Supabase query: {str(e)}")
            return {"data": [], "error": str(e)}
        finally:
            release_connection(client)
    
    def insert_data(self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Insert data into a Supabase table.
        
        Args:
            table: Table name
            data: Dictionary or list of dictionaries to insert
            
        Returns:
            Dictionary with insert results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"data": [], "error": "Failed to get Supabase client"}
        
        try:
            # Insert the data
            response = client.table(table).insert(data).execute()
            
            result = {
                "data": response.data,
                "error": response.error
            }
            
            return result
        except Exception as e:
            logger.error(f"Error inserting data into Supabase: {str(e)}")
            return {"data": [], "error": str(e)}
        finally:
            release_connection(client)
    
    def update_data(self, table: str, data: Dict[str, Any], match_column: str, match_value: Any) -> Dict[str, Any]:
        """
        Update data in a Supabase table.
        
        Args:
            table: Table name
            data: Dictionary with the data to update
            match_column: Column name to match for the update
            match_value: Value to match for the update
            
        Returns:
            Dictionary with update results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"data": [], "error": "Failed to get Supabase client"}
        
        try:
            # Update the data
            response = client.table(table).update(data).eq(match_column, match_value).execute()
            
            result = {
                "data": response.data,
                "error": response.error
            }
            
            return result
        except Exception as e:
            logger.error(f"Error updating data in Supabase: {str(e)}")
            return {"data": [], "error": str(e)}
        finally:
            release_connection(client)
    
    def delete_data(self, table: str, match_column: str, match_value: Any) -> Dict[str, Any]:
        """
        Delete data from a Supabase table.
        
        Args:
            table: Table name
            match_column: Column name to match for the delete
            match_value: Value to match for the delete
            
        Returns:
            Dictionary with delete results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"data": [], "error": "Failed to get Supabase client"}
        
        try:
            # Delete the data
            response = client.table(table).delete().eq(match_column, match_value).execute()
            
            result = {
                "data": response.data,
                "error": response.error
            }
            
            return result
        except Exception as e:
            logger.error(f"Error deleting data from Supabase: {str(e)}")
            return {"data": [], "error": str(e)}
        finally:
            release_connection(client)
    
    def execute_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a raw SQL query via the Supabase RPC function.
        
        Args:
            sql: SQL query to execute
            params: Query parameters
            
        Returns:
            Dictionary with query results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"data": None, "error": "Failed to get Supabase client"}
        
        try:
            # Execute the SQL query
            response = client.rpc("run_sql", {"query": sql, "params": params or {}}).execute()
            
            result = {
                "data": response.data,
                "error": response.error
            }
            
            return result
        except Exception as e:
            logger.error(f"Error executing SQL in Supabase: {str(e)}")
            return {"data": None, "error": str(e)}
        finally:
            release_connection(client)
    
    def call_function(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call a Supabase Edge Function.
        
        Args:
            function_name: Name of the function to call
            params: Function parameters
            
        Returns:
            Dictionary with function results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"data": None, "error": "Failed to get Supabase client"}
        
        try:
            # Call the Edge Function
            response = client.functions.invoke(function_name, params or {})
            
            result = {
                "data": response.data,
                "error": response.error
            }
            
            return result
        except Exception as e:
            logger.error(f"Error calling Supabase function: {str(e)}")
            return {"data": None, "error": str(e)}
        finally:
            release_connection(client)
    
    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user with Supabase Auth.
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            Dictionary with authentication results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"user": None, "session": None, "error": "Failed to get Supabase client"}
        
        try:
            # Sign in the user
            response = client.auth.sign_in_with_password({"email": email, "password": password})
            
            result = {
                "user": response.user,
                "session": response.session,
                "error": None
            }
            
            return result
        except Exception as e:
            logger.error(f"Error authenticating user with Supabase: {str(e)}")
            return {"user": None, "session": None, "error": str(e)}
        finally:
            release_connection(client)
    
    def upload_file(self, bucket: str, path: str, file_data: bytes, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """
        Upload a file to Supabase Storage.
        
        Args:
            bucket: Bucket name
            path: File path within the bucket
            file_data: File data as bytes
            content_type: MIME type of the file
            
        Returns:
            Dictionary with upload results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"data": None, "error": "Failed to get Supabase client"}
        
        try:
            # Upload the file
            response = client.storage.from_(bucket).upload(path, file_data, {"content-type": content_type})
            
            result = {
                "data": response,
                "error": None
            }
            
            return result
        except Exception as e:
            logger.error(f"Error uploading file to Supabase Storage: {str(e)}")
            return {"data": None, "error": str(e)}
        finally:
            release_connection(client)
    
    def download_file(self, bucket: str, path: str) -> Dict[str, Any]:
        """
        Download a file from Supabase Storage.
        
        Args:
            bucket: Bucket name
            path: File path within the bucket
            
        Returns:
            Dictionary with download results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"data": None, "error": "Failed to get Supabase client"}
        
        try:
            # Download the file
            response = client.storage.from_(bucket).download(path)
            
            result = {
                "data": response,
                "error": None
            }
            
            return result
        except Exception as e:
            logger.error(f"Error downloading file from Supabase Storage: {str(e)}")
            return {"data": None, "error": str(e)}
        finally:
            release_connection(client)
    
    def get_file_url(self, bucket: str, path: str) -> Dict[str, Any]:
        """
        Get a public URL for a file in Supabase Storage.
        
        Args:
            bucket: Bucket name
            path: File path within the bucket
            
        Returns:
            Dictionary with URL results
        """
        client = self._get_client()
        if not client:
            logger.warning("Failed to get Supabase client")
            return {"url": None, "error": "Failed to get Supabase client"}
        
        try:
            # Get the public URL
            url = client.storage.from_(bucket).get_public_url(path)
            
            result = {
                "url": url,
                "error": None
            }
            
            return result
        except Exception as e:
            logger.error(f"Error getting file URL from Supabase Storage: {str(e)}")
            return {"url": None, "error": str(e)}
        finally:
            release_connection(client)


# Factory function to create a service-specific client
def create_service_client(service_name: str, environment: Optional[str] = None) -> ServiceSupabaseClient:
    """
    Create a service-specific Supabase client.
    
    Args:
        service_name: Name of the service or component
        environment: Environment name (development, training, production)
        
    Returns:
        ServiceSupabaseClient instance
    """
    return ServiceSupabaseClient(service_name, environment)


# Decorator for functions that need a service-specific client
def with_service_client(service_name: str, environment: Optional[str] = None):
    """
    Decorator for functions that need a service-specific Supabase client.
    
    The decorated function will receive a ServiceSupabaseClient as its first argument.
    
    Args:
        service_name: Name of the service or component
        environment: Environment name (development, training, production)
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            client = create_service_client(service_name, environment)
            return func(client, *args, **kwargs)
        return wrapper
    return decorator