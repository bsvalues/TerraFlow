"""
Supabase Environment Manager

This module provides functionality for managing multiple Supabase environments
(development, training, production) and switching between them.
"""

import os
import logging
import json
from typing import Dict, Optional, Any, List, Tuple

try:
    import dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
ENV_FILE = ".env"
VALID_ENVIRONMENTS = ["development", "training", "production"]

def load_environment_variables() -> bool:
    """
    Load environment variables from .env file if available.
    
    Returns:
        True if successful, False otherwise
    """
    if DOTENV_AVAILABLE:
        try:
            dotenv.load_dotenv(ENV_FILE)
            logger.debug(f"Loaded environment variables from {ENV_FILE}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load environment variables from {ENV_FILE}: {str(e)}")
            return False
    else:
        logger.warning("dotenv package not installed, cannot load from .env file")
        return False

def get_current_environment() -> str:
    """
    Get the current active Supabase environment.
    
    Returns:
        Environment name (development, training, production)
    """
    # Load environment variables
    load_environment_variables()
    
    # Get current environment
    return os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")

def set_current_environment(environment: str) -> bool:
    """
    Set the current active Supabase environment.
    
    Args:
        environment: Environment name (development, training, production)
        
    Returns:
        True if successful, False otherwise
    """
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        return False
    
    # Check if environment is configured
    env_url_var = f"SUPABASE_URL_{environment.upper()}"
    env_key_var = f"SUPABASE_KEY_{environment.upper()}"
    
    url = os.environ.get(env_url_var)
    key = os.environ.get(env_key_var)
    
    if not url or not key:
        logger.error(f"Environment {environment} is not configured")
        return False
    
    try:
        # Set active environment in .env file if available
        if DOTENV_AVAILABLE:
            dotenv.set_key(ENV_FILE, "SUPABASE_ACTIVE_ENVIRONMENT", environment)
        
        # Set in current environment
        os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = environment
        
        # Update base variables to match active environment
        os.environ["SUPABASE_URL"] = url
        os.environ["SUPABASE_KEY"] = key
        
        # Set service key if available
        service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{environment.upper()}")
        if service_key:
            os.environ["SUPABASE_SERVICE_KEY"] = service_key
        
        logger.info(f"Set active Supabase environment to {environment}")
        return True
    except Exception as e:
        logger.error(f"Error setting active environment: {str(e)}")
        return False

def get_all_environments() -> Dict[str, Dict[str, Any]]:
    """
    Get information about all Supabase environments.
    
    Returns:
        Dictionary mapping environment names to their details
    """
    # Load environment variables
    load_environment_variables()
    
    # Get active environment
    active_env = get_current_environment()
    
    # Get information about each environment
    environments = {}
    
    for env in VALID_ENVIRONMENTS:
        url = os.environ.get(f"SUPABASE_URL_{env.upper()}")
        key = os.environ.get(f"SUPABASE_KEY_{env.upper()}")
        service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{env.upper()}")
        
        environments[env] = {
            "url": url,
            "key_available": bool(key),
            "service_key_available": bool(service_key),
            "is_active": env == active_env,
            "configured": bool(url and key)
        }
    
    return environments

def configure_environment(environment: str, url: str, key: str, service_key: Optional[str] = None) -> bool:
    """
    Configure a Supabase environment.
    
    Args:
        environment: Environment name (development, training, production)
        url: Supabase URL
        key: Supabase API key
        service_key: Supabase service key (optional)
        
    Returns:
        True if successful, False otherwise
    """
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        return False
    
    try:
        # Set environment variables in .env file if available
        if DOTENV_AVAILABLE:
            dotenv.set_key(ENV_FILE, f"SUPABASE_URL_{environment.upper()}", url)
            dotenv.set_key(ENV_FILE, f"SUPABASE_KEY_{environment.upper()}", key)
            
            if service_key:
                dotenv.set_key(ENV_FILE, f"SUPABASE_SERVICE_KEY_{environment.upper()}", service_key)
        
        # Set in current environment
        os.environ[f"SUPABASE_URL_{environment.upper()}"] = url
        os.environ[f"SUPABASE_KEY_{environment.upper()}"] = key
        
        if service_key:
            os.environ[f"SUPABASE_SERVICE_KEY_{environment.upper()}"] = service_key
        
        # If this is the active environment, update base variables
        active_env = get_current_environment()
        if environment == active_env:
            os.environ["SUPABASE_URL"] = url
            os.environ["SUPABASE_KEY"] = key
            
            if service_key:
                os.environ["SUPABASE_SERVICE_KEY"] = service_key
        
        logger.info(f"Configured Supabase environment {environment}")
        return True
    except Exception as e:
        logger.error(f"Error configuring environment {environment}: {str(e)}")
        return False

def get_environment_variables(environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Get environment variables for a specific Supabase environment.
    
    Args:
        environment: Environment name (development, training, production) or None for active
        
    Returns:
        Dictionary with environment variables
    """
    # Load environment variables
    load_environment_variables()
    
    # If no environment specified, use active
    if not environment:
        environment = get_current_environment()
    
    # Get environment variables
    if environment == "development":
        # For development, check the base variables first
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        # If not set, check environment-specific variables
        if not url:
            url = os.environ.get("SUPABASE_URL_DEVELOPMENT")
        if not key:
            key = os.environ.get("SUPABASE_KEY_DEVELOPMENT")
        if not service_key:
            service_key = os.environ.get("SUPABASE_SERVICE_KEY_DEVELOPMENT")
    else:
        # For other environments, use environment-specific variables
        url = os.environ.get(f"SUPABASE_URL_{environment.upper()}")
        key = os.environ.get(f"SUPABASE_KEY_{environment.upper()}")
        service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{environment.upper()}")
    
    return {
        "url": url,
        "key": key,
        "service_key": service_key,
        "environment": environment,
        "configured": bool(url and key)
    }

def export_environments_to_file(file_path: str) -> bool:
    """
    Export environment configurations to a file.
    
    Args:
        file_path: Path to the file to export to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get all environments
        environments = get_all_environments()
        
        # Get active environment
        active_env = get_current_environment()
        
        # Create export data
        export_data = {
            "active_environment": active_env,
            "environments": {}
        }
        
        # Add each environment
        for env, info in environments.items():
            if info["configured"]:
                export_data["environments"][env] = {
                    "url": info["url"],
                    "key_available": info["key_available"],
                    "service_key_available": info["service_key_available"]
                }
        
        # Write to file
        with open(file_path, "w") as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported environment configurations to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting environments: {str(e)}")
        return False

def import_environments_from_file(file_path: str) -> bool:
    """
    Import environment configurations from a file.
    
    Args:
        file_path: Path to the file to import from
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read from file
        with open(file_path, "r") as f:
            import_data = json.load(f)
        
        # Validate import data
        if "environments" not in import_data:
            logger.error("Invalid import data: 'environments' key not found")
            return False
        
        # Import each environment
        for env, info in import_data["environments"].items():
            if env not in VALID_ENVIRONMENTS:
                logger.warning(f"Skipping invalid environment: {env}")
                continue
            
            if "url" not in info:
                logger.warning(f"Skipping environment {env}: 'url' not found")
                continue
            
            # Configure environment
            configure_environment(
                env,
                info["url"],
                info.get("key", ""),
                info.get("service_key", None)
            )
        
        # Set active environment if specified
        if "active_environment" in import_data:
            active_env = import_data["active_environment"]
            if active_env in VALID_ENVIRONMENTS:
                set_current_environment(active_env)
        
        logger.info(f"Imported environment configurations from {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error importing environments: {str(e)}")
        return False