"""
Supabase Environment Manager

This module provides utility functions for managing environment-specific connections
to Supabase, making it easier to switch between development, training, and production
environments for database operations, authentication, and storage.
"""

import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from config_loader import get_config, is_development_mode

# Set up logging
logger = logging.getLogger(__name__)

# Current thread-local environment context
_current_environment = None

def get_current_environment() -> str:
    """
    Get the current environment context.
    
    Returns:
        Current environment name (development, training, production)
    """
    global _current_environment
    
    # If no specific environment is set, use the default from config
    if _current_environment is None:
        default_env = "development" if is_development_mode() else "production"
        return default_env
    
    return _current_environment

def set_current_environment(environment: str) -> None:
    """
    Set the current environment context.
    
    Args:
        environment: Environment name (development, training, production)
    """
    global _current_environment
    
    if environment not in ["development", "training", "production"]:
        logger.warning(f"Invalid environment: {environment}. Using development instead.")
        environment = "development"
    
    logger.info(f"Setting current Supabase environment to: {environment}")
    _current_environment = environment

@contextmanager
def environment_context(environment: str):
    """
    Context manager for temporarily switching environments.
    
    Args:
        environment: Environment name to use within the context
        
    Example:
        with environment_context('production'):
            # Code here uses production environment
            result = supabase_client.execute_query('my_table')
    """
    previous_env = get_current_environment()
    try:
        set_current_environment(environment)
        yield
    finally:
        set_current_environment(previous_env)

def get_environment_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Get configuration for a specific environment.
    
    Args:
        environment: Optional environment name (development, training, production)
                    If None, uses the current environment
    
    Returns:
        Dictionary with environment-specific configuration
    """
    if environment is None:
        environment = get_current_environment()
        
    # Get base Supabase configuration
    config = get_config('supabase')
    if not config:
        config = {}
    
    # Get environment-specific overrides
    env_config = config.get(environment, {})
    
    # Merge with base configuration
    result = {**config, **env_config}
    
    # Remove environment-specific sections
    for env in ['development', 'training', 'production']:
        if env in result:
            del result[env]
    
    return result

def get_environment_url(environment: Optional[str] = None) -> Optional[str]:
    """
    Get Supabase URL for a specific environment.
    
    Args:
        environment: Optional environment name (development, training, production)
                    If None, uses the current environment
    
    Returns:
        Supabase URL for the specified environment
    """
    env_config = get_environment_config(environment)
    
    # Try environment-specific URL first
    url = env_config.get('url')
    
    # Fallback to environment variable
    if not url:
        url = os.environ.get('SUPABASE_URL')
    
    return url

def get_environment_key(environment: Optional[str] = None) -> Optional[str]:
    """
    Get Supabase API key for a specific environment.
    
    Args:
        environment: Optional environment name (development, training, production)
                    If None, uses the current environment
    
    Returns:
        Supabase API key for the specified environment
    """
    env_config = get_environment_config(environment)
    
    # Try environment-specific key first
    key = env_config.get('key')
    
    # Fallback to environment variable
    if not key:
        key = os.environ.get('SUPABASE_KEY')
    
    return key

def get_environment_service_key(environment: Optional[str] = None) -> Optional[str]:
    """
    Get Supabase service role key for a specific environment.
    
    Args:
        environment: Optional environment name (development, training, production)
                    If None, uses the current environment
    
    Returns:
        Supabase service role key for the specified environment
    """
    env_config = get_environment_config(environment)
    
    # Try environment-specific service key first
    service_key = env_config.get('service_key')
    
    # Fallback to environment variable
    if not service_key:
        service_key = os.environ.get('SUPABASE_SERVICE_KEY')
    
    return service_key

def check_environment_config(environment: Optional[str] = None) -> bool:
    """
    Check if a specific environment is properly configured.
    
    Args:
        environment: Optional environment name (development, training, production)
                    If None, uses the current environment
    
    Returns:
        True if the environment is properly configured, False otherwise
    """
    if environment is None:
        environment = get_current_environment()
    
    url = get_environment_url(environment)
    key = get_environment_key(environment)
    
    if not url or not key:
        logger.warning(f"Supabase environment '{environment}' is not properly configured. Missing URL or API key.")
        return False
    
    return True

def get_all_configured_environments() -> Dict[str, bool]:
    """
    Get all available environments and their configuration status.
    
    Returns:
        Dictionary mapping environment names to their configuration status (True if configured)
    """
    return {
        env: check_environment_config(env)
        for env in ['development', 'training', 'production']
    }