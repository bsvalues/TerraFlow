"""
Supabase Client Module

This module provides a central client for Supabase services.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from functools import lru_cache

try:
    from supabase import create_client, Client
    from postgrest.exceptions import APIError
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from config_loader import get_config, is_supabase_enabled

# Configure logging
logger = logging.getLogger(__name__)

# Cache the client creation
@lru_cache(maxsize=1)
def get_supabase_client() -> Optional[Client]:
    """
    Get a Supabase client instance.
    
    Returns:
        Supabase client or None if not available
    """
    if not SUPABASE_AVAILABLE:
        logger.warning("Supabase package is not installed")
        return None
    
    if not is_supabase_enabled():
        logger.warning("Supabase is not enabled in configuration")
        return None
    
    try:
        # Get configuration
        db_config = get_config("database")
        url = db_config.get("supabase_url")
        key = db_config.get("supabase_service_key", db_config.get("supabase_key"))
        
        if not url or not key:
            logger.error("Missing Supabase URL or key in configuration")
            return None
        
        logger.debug(f"Creating Supabase client for {url}")
        client = create_client(url, key)
        return client
    except Exception as e:
        logger.error(f"Error creating Supabase client: {str(e)}")
        return None

def upload_file_to_storage(
    file_path: str, 
    bucket: str, 
    destination_path: str, 
    content_type: Optional[str] = None
) -> Optional[str]:
    """
    Upload a file to Supabase Storage.
    
    Args:
        file_path: Path to local file
        bucket: Storage bucket name
        destination_path: Path within the bucket
        content_type: MIME type of the file (optional)
        
    Returns:
        Public URL of the uploaded file or None on failure
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        logger.info(f"Uploading {file_path} to {bucket}/{destination_path}")
        options = {}
        if content_type:
            options["content_type"] = content_type
        
        result = client.storage.from_(bucket).upload(
            destination_path,
            file_data,
            options
        )
        
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Upload error: {result.error}")
        
        # Get public URL
        public_url = client.storage.from_(bucket).get_public_url(destination_path)
        return public_url
    except Exception as e:
        logger.error(f"Error uploading file to Supabase: {str(e)}")
        return None

def list_files_in_storage(bucket: str, path: str = '') -> Optional[List[Dict[str, Any]]]:
    """
    List files in a Supabase Storage bucket.
    
    Args:
        bucket: Storage bucket name
        path: Path prefix within the bucket
        
    Returns:
        List of file metadata or None on failure
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        result = client.storage.from_(bucket).list(path)
        if hasattr(result, 'error') and result.error:
            raise Exception(f"List error: {result.error}")
        return result
    except Exception as e:
        logger.error(f"Error listing files in Supabase: {str(e)}")
        return None

def delete_file_from_storage(bucket: str, path: str) -> bool:
    """
    Delete a file from Supabase Storage.
    
    Args:
        bucket: Storage bucket name
        path: Path to the file within the bucket
        
    Returns:
        True on success, False on failure
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        result = client.storage.from_(bucket).remove([path])
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Delete error: {result.error}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file from Supabase: {str(e)}")
        return False

def download_file_from_storage(bucket: str, storage_path: str, destination_path: str) -> bool:
    """
    Download a file from Supabase Storage.
    
    Args:
        bucket: Storage bucket name
        storage_path: Path to the file within the bucket
        destination_path: Local path to save the file
        
    Returns:
        True on success, False on failure
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Download the file to the destination
        with open(destination_path, 'wb') as f:
            response = client.storage.from_(bucket).download(storage_path)
            f.write(response)
        
        logger.info(f"Downloaded {bucket}/{storage_path} to {destination_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading file from Supabase: {str(e)}")
        return False

def execute_query(table: str, select: str = "*", filters: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Execute a query against a Supabase table.
    
    Args:
        table: Table name
        select: Select clause
        filters: Dictionary of filters to apply
        
    Returns:
        List of records or None on failure
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        query = client.table(table).select(select)
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                # Handle different filter types here
                if isinstance(value, dict):
                    # Operator filter like {"gt": 100}
                    for op, op_value in value.items():
                        query = query.filter(key, op, op_value)
                else:
                    # Simple equality filter
                    query = query.eq(key, value)
        
        # Execute the query
        result = query.execute()
        
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Query error: {result.error}")
        
        return result.data
    except Exception as e:
        logger.error(f"Error executing Supabase query: {str(e)}")
        return None

def insert_record(table: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Insert a record into a Supabase table.
    
    Args:
        table: Table name
        record: Record to insert
        
    Returns:
        Inserted record or None on failure
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        result = client.table(table).insert(record).execute()
        
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Insert error: {result.error}")
        
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error inserting record into Supabase: {str(e)}")
        return None

def update_record(table: str, record_id: str, updates: Dict[str, Any], id_column: str = "id") -> Optional[Dict[str, Any]]:
    """
    Update a record in a Supabase table.
    
    Args:
        table: Table name
        record_id: ID of the record to update
        updates: Fields to update
        id_column: Name of the ID column
        
    Returns:
        Updated record or None on failure
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        result = client.table(table).update(updates).eq(id_column, record_id).execute()
        
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Update error: {result.error}")
        
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error updating record in Supabase: {str(e)}")
        return None

def delete_record(table: str, record_id: str, id_column: str = "id") -> bool:
    """
    Delete a record from a Supabase table.
    
    Args:
        table: Table name
        record_id: ID of the record to delete
        id_column: Name of the ID column
        
    Returns:
        True on success, False on failure
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        result = client.table(table).delete().eq(id_column, record_id).execute()
        
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Delete error: {result.error}")
        
        return True
    except Exception as e:
        logger.error(f"Error deleting record from Supabase: {str(e)}")
        return False