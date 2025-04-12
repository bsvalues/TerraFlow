"""
Configuration Loader

This module loads configuration settings from environment variables, config files,
and provides access to them throughout the application.
"""

import os
import logging
import json
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "database": {
        "engine": "postgresql",
        "connection_string": "postgresql://postgres:postgres@localhost:5432/postgres"
    },
    "auth": {
        "provider": "supabase",
        "bypass_auth": False
    },
    "storage": {
        "provider": "supabase",
        "bucket_name": "files"
    },
    "api": {
        "use_supabase_api": True
    },
    "sync": {
        "interval": 15,  # minutes
        "auto_sync": False
    }
}

# Global config instance
_config = None

def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables and config files
    
    Returns:
        Dict containing configuration settings
    """
    global _config
    
    if _config is not None:
        return _config
        
    # Start with default config
    config = DEFAULT_CONFIG.copy()
    
    # Override with environment variables
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        config["database"]["engine"] = "postgresql"
        config["database"]["provider"] = "supabase"
        config["database"]["connection_string"] = os.environ.get("DATABASE_URL", "")
        config["database"]["supabase_url"] = os.environ.get("SUPABASE_URL")
        config["database"]["supabase_key"] = os.environ.get("SUPABASE_KEY")
        config["database"]["supabase_service_key"] = os.environ.get("SUPABASE_SERVICE_KEY", "")
        
        # Set use_supabase flag to true
        config["use_supabase"] = True
        
        # If Supabase is configured, also use it for auth and storage
        config["auth"]["provider"] = "supabase"
        config["storage"]["provider"] = "supabase"
        
        logger.info("Supabase configuration detected and enabled")
        
    # Allow bypassing authentication for development
    if os.environ.get("BYPASS_LDAP", "").lower() == "true":
        config["auth"]["bypass_auth"] = True
        
    # Try to load config from JSON file if it exists
    config_file = os.environ.get("CONFIG_FILE", "config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)
                
            # Deep merge the configurations
            for section, values in file_config.items():
                if section in config:
                    if isinstance(config[section], dict) and isinstance(values, dict):
                        config[section].update(values)
                    else:
                        config[section] = values
                else:
                    config[section] = values
                    
            logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Error loading config file {config_file}: {str(e)}")
    
    _config = config
    return config

def get_config(section: Optional[str] = None, key: Optional[str] = None) -> Any:
    """
    Get configuration value(s)
    
    Args:
        section: Configuration section name (optional)
        key: Configuration key within section (optional)
        
    Returns:
        Config value, section, or entire config depending on args
    """
    config = load_config()
    
    if section is None:
        return config
        
    if section not in config:
        return None
        
    if key is None:
        return config[section]
        
    return config[section].get(key)

def get_database_config() -> Dict[str, Any]:
    """
    Get database configuration
    
    Returns:
        Dict with database configuration
    """
    return get_config("database")

def get_auth_config() -> Dict[str, Any]:
    """
    Get authentication configuration
    
    Returns:
        Dict with auth configuration
    """
    return get_config("auth")

def get_storage_config() -> Dict[str, Any]:
    """
    Get file storage configuration
    
    Returns:
        Dict with storage configuration
    """
    return get_config("storage")

def get_sync_config() -> Dict[str, Any]:
    """
    Get data synchronization configuration
    
    Returns:
        Dict with sync configuration
    """
    return get_config("sync")

def is_development_mode() -> bool:
    """
    Check if application is running in development mode
    
    Returns:
        True if in development mode, False otherwise
    """
    return get_config("auth", "bypass_auth") is True or os.environ.get("BYPASS_LDAP", "").lower() == "true"

def is_supabase_enabled() -> bool:
    """
    Check if Supabase integration is enabled
    
    Returns:
        True if Supabase is configured, False otherwise
    """
    # First check for the top-level use_supabase flag
    if get_config().get("use_supabase") is True:
        return True
        
    # Fallback to checking database configuration
    db_config = get_database_config()
    if not db_config:
        return False
        
    return db_config.get("provider") == "supabase" and "supabase_url" in db_config and "supabase_key" in db_config