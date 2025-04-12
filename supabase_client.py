"""
Supabase Client Module

This module provides the interface to interact with Supabase services.
It handles authentication, database, and storage operations.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union
import json
import requests
from config_loader import get_config

# Configure logging
logger = logging.getLogger(__name__)

# Check if Supabase package is available
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    logger.warning("Supabase package not available. Some functionality will be limited.")
    HAS_SUPABASE = False

# Global client instance
_supabase_client = None

def get_supabase_client() -> Optional[Client]:
    """
    Get a Supabase client instance
    
    Returns:
        Supabase client or None if not available
    """
    global _supabase_client
    
    if not HAS_SUPABASE:
        logger.error("Supabase package not installed")
        return None
    
    if _supabase_client is None:
        # Get credentials from environment or config
        supabase_url = os.environ.get("SUPABASE_URL") or get_config("supabase", "url")
        supabase_key = os.environ.get("SUPABASE_KEY") or get_config("supabase", "api_key")
        
        if not supabase_url or not supabase_key:
            logger.error("Supabase URL or API key not configured")
            return None
        
        try:
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {str(e)}")
            return None
    
    return _supabase_client

# Authentication functions

def sign_up(email: str, password: str, user_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Sign up a new user with Supabase
    
    Args:
        email: User email
        password: User password
        user_metadata: Optional additional user data
        
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        response = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": user_metadata
            }
        })
        
        return {
            "user": response.user,
            "session": response.session
        }
    except Exception as e:
        logger.error(f"Error signing up user: {str(e)}")
        return {"error": str(e)}

def sign_in(email: str, password: str) -> Dict[str, Any]:
    """
    Sign in a user with Supabase
    
    Args:
        email: User email
        password: User password
        
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        return {
            "user": response.user,
            "session": response.session
        }
    except Exception as e:
        logger.error(f"Error signing in user: {str(e)}")
        return {"error": str(e)}

def sign_out() -> Dict[str, Any]:
    """
    Sign out the current user
    
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        client.auth.sign_out()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error signing out: {str(e)}")
        return {"error": str(e)}

# Database functions

def get_data(table: str, query_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get data from a Supabase table
    
    Args:
        table: Table name
        query_params: Optional query parameters (limit, offset, etc.)
        
    Returns:
        Dict with data or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        query = client.table(table).select("*")
        
        # Apply query parameters if provided
        if query_params:
            if "limit" in query_params:
                query = query.limit(query_params["limit"])
            if "offset" in query_params:
                query = query.offset(query_params["offset"])
            if "order" in query_params and "column" in query_params:
                if query_params["order"].lower() == "asc":
                    query = query.order(query_params["column"])
                else:
                    query = query.order(query_params["column"], desc=True)
            if "filter" in query_params and "value" in query_params:
                # Simple filter for now, can be extended
                query = query.eq(query_params["filter"], query_params["value"])
        
        response = query.execute()
        
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error getting data from {table}: {str(e)}")
        return {"error": str(e)}

def insert_data(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert data into a Supabase table
    
    Args:
        table: Table name
        data: Data to insert
        
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        response = client.table(table).insert(data).execute()
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error inserting data into {table}: {str(e)}")
        return {"error": str(e)}

def update_data(table: str, data: Dict[str, Any], match_column: str, match_value: Any) -> Dict[str, Any]:
    """
    Update data in a Supabase table
    
    Args:
        table: Table name
        data: Data to update
        match_column: Column to match for update
        match_value: Value to match for update
        
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        response = client.table(table).update(data).eq(match_column, match_value).execute()
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error updating data in {table}: {str(e)}")
        return {"error": str(e)}

def delete_data(table: str, match_column: str, match_value: Any) -> Dict[str, Any]:
    """
    Delete data from a Supabase table
    
    Args:
        table: Table name
        match_column: Column to match for deletion
        match_value: Value to match for deletion
        
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        response = client.table(table).delete().eq(match_column, match_value).execute()
        return {"success": True, "count": len(response.data)}
    except Exception as e:
        logger.error(f"Error deleting data from {table}: {str(e)}")
        return {"error": str(e)}

# Storage functions

def list_buckets() -> Dict[str, Any]:
    """
    List all storage buckets
    
    Returns:
        Dict with buckets or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        response = client.storage.list_buckets()
        return {"buckets": response}
    except Exception as e:
        logger.error(f"Error listing buckets: {str(e)}")
        return {"error": str(e)}

def create_bucket(bucket_name: str, is_public: bool = False) -> Dict[str, Any]:
    """
    Create a new storage bucket
    
    Args:
        bucket_name: Name of the bucket
        is_public: Whether the bucket should be public
        
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        client.storage.create_bucket(bucket_name, {'public': is_public})
        return {"success": True, "bucket": bucket_name}
    except Exception as e:
        logger.error(f"Error creating bucket {bucket_name}: {str(e)}")
        return {"error": str(e)}

def list_files(bucket_name: str, path: str = "") -> Dict[str, Any]:
    """
    List files in a bucket
    
    Args:
        bucket_name: Name of the bucket
        path: Path within the bucket
        
    Returns:
        Dict with files or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        response = client.storage.from_(bucket_name).list(path)
        return {"files": response}
    except Exception as e:
        logger.error(f"Error listing files in {bucket_name}/{path}: {str(e)}")
        return {"error": str(e)}

def upload_file(bucket_name: str, file_path: str, destination_path: str) -> Dict[str, Any]:
    """
    Upload a file to Supabase storage
    
    Args:
        bucket_name: Name of the bucket
        file_path: Local path to the file
        destination_path: Path in the bucket
        
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        response = client.storage.from_(bucket_name).upload(destination_path, file_content)
        return {"path": response.get("path", "")}
    except Exception as e:
        logger.error(f"Error uploading file to {bucket_name}/{destination_path}: {str(e)}")
        return {"error": str(e)}

def download_file(bucket_name: str, file_path: str, destination_path: str) -> Dict[str, Any]:
    """
    Download a file from Supabase storage
    
    Args:
        bucket_name: Name of the bucket
        file_path: Path to the file in the bucket
        destination_path: Local path to save the file
        
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        response = client.storage.from_(bucket_name).download(file_path)
        
        # Save the file
        with open(destination_path, "wb") as f:
            f.write(response)
            
        return {"success": True, "path": destination_path}
    except Exception as e:
        logger.error(f"Error downloading file from {bucket_name}/{file_path}: {str(e)}")
        return {"error": str(e)}

def delete_file(bucket_name: str, file_path: str) -> Dict[str, Any]:
    """
    Delete a file from Supabase storage
    
    Args:
        bucket_name: Name of the bucket
        file_path: Path to the file in the bucket
        
    Returns:
        Dict with result or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
    
    try:
        client.storage.from_(bucket_name).remove([file_path])
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting file from {bucket_name}/{file_path}: {str(e)}")
        return {"error": str(e)}

def get_public_url(bucket_name: str, file_path: str) -> str:
    """
    Get a public URL for a file
    
    Args:
        bucket_name: Name of the bucket
        file_path: Path to the file in the bucket
        
    Returns:
        Public URL for the file
    """
    client = get_supabase_client()
    if not client:
        return ""
    
    try:
        return client.storage.from_(bucket_name).get_public_url(file_path)
    except Exception as e:
        logger.error(f"Error getting public URL for {bucket_name}/{file_path}: {str(e)}")
        return ""