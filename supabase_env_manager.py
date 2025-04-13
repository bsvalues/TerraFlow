"""
Supabase Environment Manager

This module provides utilities for managing multiple Supabase environments
(development, training, production) and switching between them.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Current active environment (default to 'development')
_current_environment = 'development'

def get_current_environment() -> str:
    """
    Get the currently active Supabase environment.
    
    Returns:
        String name of the current environment
    """
    return _current_environment

def set_current_environment(environment: str) -> bool:
    """
    Set the current active Supabase environment.
    
    Args:
        environment: Name of the environment to set as active
        
    Returns:
        True if successful, False otherwise
    """
    if environment not in ['development', 'training', 'production']:
        logger.error(f"Invalid environment: {environment}")
        return False
    
    global _current_environment
    _current_environment = environment
    
    # Set base environment variables to the selected environment
    url = get_environment_url(environment)
    key = get_environment_key(environment)
    service_key = get_environment_service_key(environment)
    
    if url:
        os.environ['SUPABASE_URL'] = url
    if key:
        os.environ['SUPABASE_KEY'] = key
    if service_key:
        os.environ['SUPABASE_SERVICE_KEY'] = service_key
    
    logger.info(f"Set current Supabase environment to: {environment}")
    return True

def get_environment_url(environment: str) -> Optional[str]:
    """
    Get the Supabase URL for the specified environment.
    
    Args:
        environment: Environment name
        
    Returns:
        URL string or None if not configured
    """
    return os.environ.get(f"SUPABASE_URL_{environment.upper()}")

def get_environment_key(environment: str) -> Optional[str]:
    """
    Get the Supabase API key for the specified environment.
    
    Args:
        environment: Environment name
        
    Returns:
        API key string or None if not configured
    """
    return os.environ.get(f"SUPABASE_KEY_{environment.upper()}")

def get_environment_service_key(environment: str) -> Optional[str]:
    """
    Get the Supabase service role key for the specified environment.
    
    Args:
        environment: Environment name
        
    Returns:
        Service role key string or None if not configured
    """
    return os.environ.get(f"SUPABASE_SERVICE_KEY_{environment.upper()}")

def check_environment_config(environment: str) -> bool:
    """
    Check if an environment is properly configured.
    
    Args:
        environment: Environment name
        
    Returns:
        True if the environment has the required configuration, False otherwise
    """
    url = get_environment_url(environment)
    key = get_environment_key(environment)
    
    return bool(url and key)

def get_all_configured_environments() -> Dict[str, bool]:
    """
    Get a dictionary of all environments and their configuration status.
    
    Returns:
        Dict mapping environment names to boolean configuration status
    """
    return {
        'development': check_environment_config('development'),
        'training': check_environment_config('training'),
        'production': check_environment_config('production')
    }

def get_environment_details(environment: str) -> Dict[str, Any]:
    """
    Get details about a specific environment.
    
    Args:
        environment: Environment name
        
    Returns:
        Dict with environment details
    """
    if environment not in ['development', 'training', 'production']:
        return {'error': 'Invalid environment'}
    
    return {
        'url': get_environment_url(environment),
        'key': get_environment_key(environment),
        'has_service_key': bool(get_environment_service_key(environment)),
        'is_configured': check_environment_config(environment),
        'is_current': (environment == get_current_environment())
    }

def load_environment_from_env(environment: str = None) -> bool:
    """
    Load environment configuration from .env file.
    
    Args:
        environment: Optional environment name to load specifically
        
    Returns:
        True if successful, False otherwise
    """
    try:
        load_dotenv()
        
        if environment:
            if environment not in ['development', 'training', 'production']:
                logger.error(f"Invalid environment: {environment}")
                return False
            
            environments = [environment]
        else:
            environments = ['development', 'training', 'production']
        
        for env in environments:
            if check_environment_config(env):
                logger.info(f"Loaded {env} environment configuration from .env file")
        
        return True
    
    except Exception as e:
        logger.error(f"Error loading environment configuration: {str(e)}")
        return False