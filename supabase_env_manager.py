"""
Supabase Environment Manager

This module provides functionality for managing multiple Supabase environments
(development, testing, production) and switching between them.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

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
DEFAULT_ENVIRONMENT = "development"
VALID_ENVIRONMENTS = ["development", "training", "production"]

# Environment cache for performance
_environment_cache = {}
_current_environment = None  # Defaults to None, will use DEFAULT_ENVIRONMENT if not set

def load_environment_variables():
    """
    Load environment variables from .env file if available.
    """
    if DOTENV_AVAILABLE:
        try:
            dotenv.load_dotenv(ENV_FILE)
            logger.debug("Loaded environment variables from .env file")
        except Exception as e:
            logger.warning(f"Failed to load environment variables from .env file: {str(e)}")

def get_current_environment() -> str:
    """
    Get the currently active Supabase environment.
    
    Returns:
        Current environment name (development, training, or production)
    """
    global _current_environment
    
    if _current_environment:
        return _current_environment
    
    # Try to get from environment variable
    env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", DEFAULT_ENVIRONMENT)
    
    # Validate environment
    if env not in VALID_ENVIRONMENTS:
        logger.warning(f"Invalid environment: {env}, using default: {DEFAULT_ENVIRONMENT}")
        env = DEFAULT_ENVIRONMENT
    
    _current_environment = env
    return env

def set_current_environment(environment: str) -> bool:
    """
    Set the active Supabase environment.
    
    Args:
        environment: Environment name (development, training, or production)
        
    Returns:
        True if successful, False otherwise
    """
    global _current_environment
    
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        return False
    
    # Check if environment is configured
    url = get_environment_url(environment)
    key = get_environment_key(environment)
    
    if not url or not key:
        logger.error(f"Environment {environment} is not configured")
        return False
    
    # Set current environment
    _current_environment = environment
    os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = environment
    
    # Update the base variables
    os.environ["SUPABASE_URL"] = url
    os.environ["SUPABASE_KEY"] = key
    
    # Set service key if available
    service_key = get_environment_service_key(environment)
    if service_key:
        os.environ["SUPABASE_SERVICE_KEY"] = service_key
    elif "SUPABASE_SERVICE_KEY" in os.environ:
        del os.environ["SUPABASE_SERVICE_KEY"]
    
    logger.info(f"Active environment changed to {environment}")
    
    # If dotenv is available, try to save to .env file
    if DOTENV_AVAILABLE:
        try:
            dotenv.set_key(ENV_FILE, "SUPABASE_ACTIVE_ENVIRONMENT", environment)
            logger.debug(f"Saved active environment to {ENV_FILE}")
        except Exception as e:
            logger.warning(f"Failed to save active environment to {ENV_FILE}: {str(e)}")
    
    return True

def get_environment_url(environment: str) -> Optional[str]:
    """
    Get the Supabase URL for a specific environment.
    
    Args:
        environment: Environment name (development, training, or production)
        
    Returns:
        Supabase URL or None if not configured
    """
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        return None
    
    # First check environment-specific variables
    url = os.environ.get(f"SUPABASE_URL_{environment.upper()}")
    
    # If environment is current, fallback to base variable
    if not url and environment == get_current_environment():
        url = os.environ.get("SUPABASE_URL")
    
    return url

def get_environment_key(environment: str) -> Optional[str]:
    """
    Get the Supabase API key for a specific environment.
    
    Args:
        environment: Environment name (development, training, or production)
        
    Returns:
        Supabase API key or None if not configured
    """
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        return None
    
    # First check environment-specific variables
    key = os.environ.get(f"SUPABASE_KEY_{environment.upper()}")
    
    # If environment is current, fallback to base variable
    if not key and environment == get_current_environment():
        key = os.environ.get("SUPABASE_KEY")
    
    return key

def get_environment_service_key(environment: str) -> Optional[str]:
    """
    Get the Supabase service key for a specific environment.
    
    Args:
        environment: Environment name (development, training, or production)
        
    Returns:
        Supabase service key or None if not configured
    """
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        return None
    
    # First check environment-specific variables
    key = os.environ.get(f"SUPABASE_SERVICE_KEY_{environment.upper()}")
    
    # If environment is current, fallback to base variable
    if not key and environment == get_current_environment():
        key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    return key

def get_all_environments() -> Dict[str, Dict[str, Any]]:
    """
    Get information about all Supabase environments.
    
    Returns:
        Dictionary with environment information
    """
    environments = {}
    
    for env in VALID_ENVIRONMENTS:
        url = get_environment_url(env)
        key = get_environment_key(env)
        service_key = get_environment_service_key(env)
        
        environments[env] = {
            "configured": bool(url and key),
            "url": url,
            "key": f"{key[:5]}...{key[-5:]}" if key else None,
            "service_key": bool(service_key)
        }
    
    return environments

def configure_environment(environment: str, url: str, key: str, service_key: Optional[str] = None) -> bool:
    """
    Configure a Supabase environment with URL and keys.
    
    Args:
        environment: Environment name (development, training, or production)
        url: Supabase URL
        key: Supabase API key
        service_key: Supabase service key (optional)
        
    Returns:
        True if successful, False otherwise
    """
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        return False
    
    if not url or not key:
        logger.error("URL and API key are required")
        return False
    
    # Set environment-specific variables
    os.environ[f"SUPABASE_URL_{environment.upper()}"] = url
    os.environ[f"SUPABASE_KEY_{environment.upper()}"] = key
    
    if service_key:
        os.environ[f"SUPABASE_SERVICE_KEY_{environment.upper()}"] = service_key
    elif f"SUPABASE_SERVICE_KEY_{environment.upper()}" in os.environ:
        del os.environ[f"SUPABASE_SERVICE_KEY_{environment.upper()}"]
    
    # If this is the active environment, also update the base variables
    if environment == get_current_environment():
        os.environ["SUPABASE_URL"] = url
        os.environ["SUPABASE_KEY"] = key
        
        if service_key:
            os.environ["SUPABASE_SERVICE_KEY"] = service_key
        elif "SUPABASE_SERVICE_KEY" in os.environ:
            del os.environ["SUPABASE_SERVICE_KEY"]
    
    logger.info(f"Environment {environment} configured successfully")
    
    # If dotenv is available, try to save to .env file
    if DOTENV_AVAILABLE:
        try:
            dotenv.set_key(ENV_FILE, f"SUPABASE_URL_{environment.upper()}", url)
            dotenv.set_key(ENV_FILE, f"SUPABASE_KEY_{environment.upper()}", key)
            
            if service_key:
                dotenv.set_key(ENV_FILE, f"SUPABASE_SERVICE_KEY_{environment.upper()}", service_key)
            
            logger.debug(f"Saved environment {environment} configuration to {ENV_FILE}")
        except Exception as e:
            logger.warning(f"Failed to save environment configuration to {ENV_FILE}: {str(e)}")
    
    return True

# Initialize environment variables on module import
load_environment_variables()