"""
Storage Handlers Module

This module provides functions to handle file storage operations using either
local filesystem storage or Supabase storage, depending on configuration.
"""

import os
import logging
import shutil
from werkzeug.utils import secure_filename
from config_loader import is_supabase_enabled, get_storage_config
from flask import current_app

# Configure logging
logger = logging.getLogger(__name__)

# Import Supabase client conditionally
try:
    from supabase_client import upload_file, download_file, get_public_url
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    logger.warning("Supabase client not available, falling back to local storage")

def get_storage_provider():
    """
    Get the configured storage provider
    
    Returns:
        str: 'supabase' or 'local'
    """
    if is_supabase_enabled() and HAS_SUPABASE:
        return 'supabase'
    return 'local'

def get_bucket_name():
    """
    Get the Supabase bucket name for file storage
    
    Returns:
        str: Bucket name
    """
    storage_config = get_storage_config()
    return storage_config.get('bucket_name', 'files')

def store_file(file, filename, user_id, project_name=None):
    """
    Store a file using the configured storage provider
    
    Args:
        file: File object to store
        filename: Secure filename
        user_id: ID of the user who owns the file
        project_name: Optional project name for organizing files
        
    Returns:
        dict with file info including path or URL
    """
    provider = get_storage_provider()
    
    if provider == 'supabase':
        return _store_file_supabase(file, filename, user_id, project_name)
    else:
        return _store_file_local(file, filename, user_id, project_name)

def retrieve_file(file_id, filename, destination_path=None):
    """
    Retrieve a file from storage
    
    Args:
        file_id: ID of the file to retrieve
        filename: Name of the file
        destination_path: Optional path to save the file
        
    Returns:
        path to the file or None if retrieval failed
    """
    provider = get_storage_provider()
    
    if provider == 'supabase':
        return _retrieve_file_supabase(file_id, filename, destination_path)
    else:
        return _retrieve_file_local(file_id, filename)

def delete_stored_file(file_id, filename):
    """
    Delete a file from storage
    
    Args:
        file_id: ID of the file to delete
        filename: Name of the file
        
    Returns:
        bool: True if successful, False otherwise
    """
    provider = get_storage_provider()
    
    if provider == 'supabase':
        return _delete_file_supabase(file_id, filename)
    else:
        return _delete_file_local(file_id, filename)

def get_file_url(file_id, filename):
    """
    Get a URL for accessing the file
    
    Args:
        file_id: ID of the file
        filename: Name of the file
        
    Returns:
        URL to access the file
    """
    provider = get_storage_provider()
    
    if provider == 'supabase':
        bucket_name = get_bucket_name()
        storage_path = f"{file_id}/{filename}"
        return get_public_url(bucket_name, storage_path)
    else:
        # For local files, we'll return a relative URL that can be used with Flask's send_from_directory
        return f"/download/{file_id}"

# Private helper functions

def _store_file_supabase(file, filename, user_id, project_name):
    """Store a file in Supabase Storage"""
    try:
        # Save to temporary location first
        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        # Determine storage path in Supabase
        bucket_name = get_bucket_name()
        storage_path = f"{user_id}/{filename}" if not project_name else f"{user_id}/{project_name}/{filename}"
        
        # Upload to Supabase
        result = upload_file(bucket_name, temp_path, storage_path)
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        if "error" in result:
            logger.error(f"Error uploading to Supabase: {result['error']}")
            return None
            
        # Get public URL
        file_url = get_public_url(bucket_name, storage_path)
        
        return {
            'provider': 'supabase',
            'bucket': bucket_name,
            'path': storage_path,
            'url': file_url
        }
    except Exception as e:
        logger.error(f"Error storing file in Supabase: {str(e)}")
        return None

def _retrieve_file_supabase(file_id, filename, destination_path=None):
    """Retrieve a file from Supabase Storage"""
    try:
        # Determine storage path in Supabase
        bucket_name = get_bucket_name()
        storage_path = f"{file_id}/{filename}"
        
        # Set destination path if not provided
        if not destination_path:
            temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            destination_path = os.path.join(temp_dir, filename)
        
        # Download from Supabase
        result = download_file(bucket_name, storage_path, destination_path)
        
        if "error" in result:
            logger.error(f"Error downloading from Supabase: {result['error']}")
            return None
            
        return destination_path
    except Exception as e:
        logger.error(f"Error retrieving file from Supabase: {str(e)}")
        return None

def _delete_file_supabase(file_id, filename):
    """Delete a file from Supabase Storage"""
    try:
        from supabase_client import get_supabase_client
        
        client = get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return False
            
        # Determine storage path in Supabase
        bucket_name = get_bucket_name()
        storage_path = f"{file_id}/{filename}"
        
        # Delete from Supabase
        client.storage.from_(bucket_name).remove([storage_path])
        
        return True
    except Exception as e:
        logger.error(f"Error deleting file from Supabase: {str(e)}")
        return False

def _store_file_local(file, filename, user_id, project_name):
    """Store a file in the local filesystem"""
    try:
        # Create directory for the file
        file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id))
        if project_name:
            file_dir = os.path.join(file_dir, secure_filename(project_name))
        os.makedirs(file_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(file_dir, filename)
        file.save(file_path)
        
        return {
            'provider': 'local',
            'path': file_path
        }
    except Exception as e:
        logger.error(f"Error storing file locally: {str(e)}")
        return None

def _retrieve_file_local(file_id, filename):
    """Retrieve a file from the local filesystem"""
    try:
        # Determine file path
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], str(file_id), filename)
        
        if os.path.exists(file_path):
            return file_path
        else:
            logger.error(f"File not found: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving local file: {str(e)}")
        return None

def _delete_file_local(file_id, filename):
    """Delete a file from the local filesystem"""
    try:
        # Determine file path
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], str(file_id), filename)
        
        if os.path.exists(file_path):
            os.unlink(file_path)
            
            # If directory is empty, remove it too
            file_dir = os.path.dirname(file_path)
            if not os.listdir(file_dir):
                os.rmdir(file_dir)
                
            return True
        else:
            logger.error(f"File not found for deletion: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error deleting local file: {str(e)}")
        return False