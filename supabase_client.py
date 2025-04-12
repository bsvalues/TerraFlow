"""
Supabase Client Module

This module provides functions to interact with Supabase for database, auth, storage, and realtime functionality.
"""

import os
import logging
from supabase import create_client, Client
from typing import Optional, Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

# Get Supabase credentials from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") 

# Initialize Supabase client
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """
    Get or initialize the Supabase client.
    
    Returns:
        Client: The Supabase client instance or None if credentials are missing
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
        
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials not found in environment variables")
        return None
        
    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {str(e)}")
        return None

# Authentication functions
def sign_up(email: str, password: str, user_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Register a new user in Supabase Auth.
    
    Args:
        email: User's email address
        password: User's password
        user_metadata: Additional user metadata
        
    Returns:
        Dict with user information or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
        
    try:
        response = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": user_metadata or {}
            }
        })
        return {"user": response.user, "session": response.session}
    except Exception as e:
        logger.error(f"Error signing up user: {str(e)}")
        return {"error": str(e)}

def sign_in(email: str, password: str) -> Dict[str, Any]:
    """
    Sign in a user using email and password.
    
    Args:
        email: User's email address
        password: User's password
        
    Returns:
        Dict with user information or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
        
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        return {"user": response.user, "session": response.session}
    except Exception as e:
        logger.error(f"Error signing in user: {str(e)}")
        return {"error": str(e)}

def sign_out() -> Dict[str, Any]:
    """
    Sign out the current user.
    
    Returns:
        Dict with success or error message
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
        
    try:
        client.auth.sign_out()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error signing out user: {str(e)}")
        return {"error": str(e)}

# Database access functions
def get_table_data(table_name: str, query_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get data from a Supabase table with optional query parameters.
    
    Args:
        table_name: Name of the table to query
        query_params: Dictionary of query parameters
            - select: Fields to select
            - order: Order by clause
            - limit: Number of rows to return
            - offset: Number of rows to skip
            - filter: Dictionary of filter conditions
            
    Returns:
        Dict with data or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
        
    try:
        query = client.table(table_name).select(query_params.get("select", "*"))
        
        # Apply filters if provided
        if "filter" in query_params:
            for column, condition in query_params["filter"].items():
                if isinstance(condition, dict):
                    for operator, value in condition.items():
                        if operator == "eq":
                            query = query.eq(column, value)
                        elif operator == "neq":
                            query = query.neq(column, value)
                        elif operator == "gt":
                            query = query.gt(column, value)
                        elif operator == "lt":
                            query = query.lt(column, value)
                        elif operator == "gte":
                            query = query.gte(column, value)
                        elif operator == "lte":
                            query = query.lte(column, value)
                        elif operator == "in":
                            query = query.in_(column, value)
                else:
                    # Default to equality
                    query = query.eq(column, condition)
        
        # Apply ordering if provided
        if "order" in query_params:
            query = query.order(query_params["order"])
            
        # Apply limit and offset if provided
        if "limit" in query_params:
            query = query.limit(query_params["limit"])
            
        if "offset" in query_params:
            query = query.offset(query_params["offset"])
            
        response = query.execute()
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error querying table {table_name}: {str(e)}")
        return {"error": str(e)}

def insert_row(table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a new row into a Supabase table.
    
    Args:
        table_name: Name of the table
        data: Dictionary of column-value pairs
        
    Returns:
        Dict with inserted data or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
        
    try:
        response = client.table(table_name).insert(data).execute()
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error inserting into table {table_name}: {str(e)}")
        return {"error": str(e)}

def update_row(table_name: str, data: Dict[str, Any], match_column: str, match_value: Any) -> Dict[str, Any]:
    """
    Update a row in a Supabase table.
    
    Args:
        table_name: Name of the table
        data: Dictionary of column-value pairs to update
        match_column: Column name to match for the update
        match_value: Value to match for the update
        
    Returns:
        Dict with updated data or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
        
    try:
        response = client.table(table_name).update(data).eq(match_column, match_value).execute()
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error updating table {table_name}: {str(e)}")
        return {"error": str(e)}

def delete_row(table_name: str, match_column: str, match_value: Any) -> Dict[str, Any]:
    """
    Delete a row from a Supabase table.
    
    Args:
        table_name: Name of the table
        match_column: Column name to match for the delete
        match_value: Value to match for the delete
        
    Returns:
        Dict with deleted data or error
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
        
    try:
        response = client.table(table_name).delete().eq(match_column, match_value).execute()
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error deleting from table {table_name}: {str(e)}")
        return {"error": str(e)}

# Storage functions
def upload_file(bucket_name: str, file_path: str, destination_path: str) -> Dict[str, Any]:
    """
    Upload a file to Supabase Storage.
    
    Args:
        bucket_name: Name of the storage bucket
        file_path: Path to the local file
        destination_path: Path in the bucket to store the file
        
    Returns:
        Dict with success or error message
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
        
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
            
        response = client.storage.from_(bucket_name).upload(destination_path, file_data)
        return {"success": True, "path": response}
    except Exception as e:
        logger.error(f"Error uploading file to storage: {str(e)}")
        return {"error": str(e)}

def download_file(bucket_name: str, source_path: str, destination_path: str) -> Dict[str, Any]:
    """
    Download a file from Supabase Storage.
    
    Args:
        bucket_name: Name of the storage bucket
        source_path: Path of the file in the bucket
        destination_path: Local path to save the file
        
    Returns:
        Dict with success or error message
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client not available"}
        
    try:
        response = client.storage.from_(bucket_name).download(source_path)
        
        with open(destination_path, "wb") as f:
            f.write(response)
            
        return {"success": True, "path": destination_path}
    except Exception as e:
        logger.error(f"Error downloading file from storage: {str(e)}")
        return {"error": str(e)}

def get_public_url(bucket_name: str, file_path: str) -> str:
    """
    Get a public URL for a file in Supabase Storage.
    
    Args:
        bucket_name: Name of the storage bucket
        file_path: Path of the file in the bucket
        
    Returns:
        Public URL or empty string on error
    """
    client = get_supabase_client()
    if not client:
        return ""
        
    try:
        return client.storage.from_(bucket_name).get_public_url(file_path)
    except Exception as e:
        logger.error(f"Error getting public URL for file: {str(e)}")
        return ""

# Realtime subscription functions
def subscribe_to_table(table_name: str, callback, event_types: List[str] = None) -> Optional[str]:
    """
    Subscribe to changes on a table.
    
    Args:
        table_name: Name of the table to subscribe to
        callback: Function to call when an event occurs
        event_types: List of event types to subscribe to (default: ["INSERT", "UPDATE", "DELETE"])
        
    Returns:
        Subscription ID or None on error
    """
    client = get_supabase_client()
    if not client:
        return None
        
    event_types = event_types or ["INSERT", "UPDATE", "DELETE"]
    
    try:
        channel = client.channel('table-filter')
        
        # Set up the subscription
        channel = channel.on(
            'postgres_changes',
            {
                'event': '*',  # or specific events: 'INSERT', 'UPDATE', 'DELETE'
                'schema': 'public',
                'table': table_name
            },
            callback
        )
        
        # Subscribe
        channel.subscribe()
        return channel.id
    except Exception as e:
        logger.error(f"Error subscribing to table changes: {str(e)}")
        return None

def unsubscribe(subscription_id: str) -> bool:
    """
    Unsubscribe from realtime changes.
    
    Args:
        subscription_id: ID of the subscription to cancel
        
    Returns:
        True if successful, False otherwise
    """
    client = get_supabase_client()
    if not client:
        return False
        
    try:
        client.remove_channel(subscription_id)
        return True
    except Exception as e:
        logger.error(f"Error unsubscribing from channel: {str(e)}")
        return False