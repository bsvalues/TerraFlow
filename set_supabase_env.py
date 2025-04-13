"""
Set Supabase Environment

This script sets up the Supabase environment variables for the application.
It is used by main.py to ensure that the Supabase environment is properly configured.
"""

import os
import sys
import logging
import json
from typing import Dict, Any, Optional, List, Tuple

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
    return os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")

def check_environment_configuration(environment: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if a Supabase environment is configured.
    
    Args:
        environment: Environment name (development, training, production)
        
    Returns:
        Tuple of (is_configured, config_details)
    """
    env_url_var = f"SUPABASE_URL_{environment.upper()}"
    env_key_var = f"SUPABASE_KEY_{environment.upper()}"
    env_service_key_var = f"SUPABASE_SERVICE_KEY_{environment.upper()}"
    
    env_url = os.environ.get(env_url_var)
    env_key = os.environ.get(env_key_var)
    env_service_key = os.environ.get(env_service_key_var)
    
    # Check base variables if environment is development
    base_url = os.environ.get("SUPABASE_URL")
    base_key = os.environ.get("SUPABASE_KEY")
    base_service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    # For development environment, use base variables if available
    if environment == "development" and (base_url or base_key):
        url = base_url
        key = base_key
        service_key = base_service_key
    else:
        url = env_url
        key = env_key
        service_key = env_service_key
    
    is_configured = bool(url and key)
    
    config_details = {
        "environment": environment,
        "url": url,
        "key_available": bool(key),
        "service_key_available": bool(service_key),
        "configured": is_configured,
        "url_var": env_url_var,
        "key_var": env_key_var,
        "service_key_var": env_service_key_var
    }
    
    return is_configured, config_details

def set_environment_variables(environment: str) -> bool:
    """
    Set the environment variables for the current environment.
    
    Args:
        environment: Environment name (development, training, production)
        
    Returns:
        True if successful, False otherwise
    """
    is_configured, config = check_environment_configuration(environment)
    
    if not is_configured:
        logger.warning(f"Environment {environment} is not configured")
        return False
    
    try:
        # Set active environment in .env file if available
        if DOTENV_AVAILABLE:
            dotenv.set_key(ENV_FILE, "SUPABASE_ACTIVE_ENVIRONMENT", environment)
        
        # Set in current environment
        os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = environment
        
        # Get environment-specific variables
        env_url_var = f"SUPABASE_URL_{environment.upper()}"
        env_key_var = f"SUPABASE_KEY_{environment.upper()}"
        env_service_key_var = f"SUPABASE_SERVICE_KEY_{environment.upper()}"
        
        url = os.environ.get(env_url_var)
        key = os.environ.get(env_key_var)
        service_key = os.environ.get(env_service_key_var)
        
        # For development, check base variables first
        if environment == "development":
            base_url = os.environ.get("SUPABASE_URL")
            base_key = os.environ.get("SUPABASE_KEY")
            base_service_key = os.environ.get("SUPABASE_SERVICE_KEY")
            
            if base_url:
                url = base_url
            if base_key:
                key = base_key
            if base_service_key:
                service_key = base_service_key
        
        # Update base variables to match active environment
        os.environ["SUPABASE_URL"] = url
        os.environ["SUPABASE_KEY"] = key
        
        if service_key:
            os.environ["SUPABASE_SERVICE_KEY"] = service_key
        
        # Log info
        logger.info(f"Set active Supabase environment to {environment}")
        logger.debug(f"Supabase URL: {url}")
        logger.debug(f"Supabase API key available: {bool(key)}")
        logger.debug(f"Supabase service key available: {bool(service_key)}")
        
        return True
    except Exception as e:
        logger.error(f"Error setting environment variables: {str(e)}")
        return False

def setup_default_environment() -> Dict[str, Any]:
    """
    Set up a default development environment if no environments are configured.
    
    Returns:
        Dictionary with environment details
    """
    # Check if any environment is already configured
    for env in VALID_ENVIRONMENTS:
        is_configured, config = check_environment_configuration(env)
        if is_configured:
            # Found a configured environment, set it as active
            set_environment_variables(env)
            return config
    
    # No environment is configured, set up development environment
    logger.warning("No Supabase environments configured, setting up development environment")
    
    # Build environment info
    return {
        "environment": "development",
        "configured": False,
        "message": "No Supabase environments configured"
    }

def ensure_supabase_env() -> Dict[str, Any]:
    """
    Ensure that the Supabase environment is properly set up.
    
    This function is called by main.py to ensure that the Supabase
    environment is properly configured before starting the application.
    
    Returns:
        Dictionary with environment details
    """
    # Load environment variables
    load_environment_variables()
    
    # Get current environment
    current_env = get_current_environment()
    
    # Check if current environment is configured
    is_configured, config = check_environment_configuration(current_env)
    
    if is_configured:
        # Current environment is configured, set it up
        set_environment_variables(current_env)
        return config
    else:
        # Current environment is not configured, try to find one that is
        for env in VALID_ENVIRONMENTS:
            is_configured, config = check_environment_configuration(env)
            if is_configured:
                # Found a configured environment, set it as active
                set_environment_variables(env)
                return config
        
        # No environment is configured, return development environment
        return setup_default_environment()

def create_environment_if_needed(create_env: bool = False) -> Dict[str, Any]:
    """
    Create a development environment if needed and requested.
    
    Args:
        create_env: Whether to create the environment if not found
        
    Returns:
        Dictionary with environment details
    """
    # Ensure environment
    env_config = ensure_supabase_env()
    
    if not env_config["configured"] and create_env:
        # Create a sample development environment
        logger.info("Creating sample development environment")
        
        # Check if .env file exists
        if DOTENV_AVAILABLE and os.path.exists(ENV_FILE):
            # Set sample values
            dotenv.set_key(ENV_FILE, "SUPABASE_URL", "https://sample-project.supabase.co")
            dotenv.set_key(ENV_FILE, "SUPABASE_KEY", "your-anon-key")
            dotenv.set_key(ENV_FILE, "SUPABASE_SERVICE_KEY", "your-service-key")
            dotenv.set_key(ENV_FILE, "SUPABASE_ACTIVE_ENVIRONMENT", "development")
            
            # Set in current environment
            os.environ["SUPABASE_URL"] = "https://sample-project.supabase.co"
            os.environ["SUPABASE_KEY"] = "your-anon-key"
            os.environ["SUPABASE_SERVICE_KEY"] = "your-service-key"
            os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = "development"
            
            # Update config
            env_config = {
                "environment": "development",
                "configured": False,  # Still not properly configured with real values
                "message": "Sample development environment created, please update with real values"
            }
    
    return env_config

def main():
    """Command-line interface for setting up Supabase environment."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Set up Supabase environment")
    parser.add_argument("--env", choices=VALID_ENVIRONMENTS, default=None, help="Environment to set up")
    parser.add_argument("--create", action="store_true", help="Create sample environment if none exists")
    parser.add_argument("--status", action="store_true", help="Show current environment status")
    
    args = parser.parse_args()
    
    if args.env:
        # Set up specific environment
        is_configured, config = check_environment_configuration(args.env)
        
        if is_configured:
            set_environment_variables(args.env)
            print(f"Successfully set up {args.env} environment")
        else:
            print(f"Environment {args.env} is not configured")
    elif args.create:
        # Create environment if needed
        config = create_environment_if_needed(create_env=True)
        print(f"Environment {config['environment']} setup: {'Success' if config['configured'] else 'Failed'}")
        if not config['configured'] and 'message' in config:
            print(f"Message: {config['message']}")
    elif args.status:
        # Show current environment status
        config = ensure_supabase_env()
        print(f"Current environment: {config['environment']}")
        print(f"Configured: {config['configured']}")
        if 'url' in config:
            print(f"URL: {config['url']}")
        if 'key_available' in config:
            print(f"API key available: {config['key_available']}")
        if 'service_key_available' in config:
            print(f"Service key available: {config['service_key_available']}")
    else:
        # Default behavior: ensure environment is set up
        config = ensure_supabase_env()
        print(f"Current environment: {config['environment']}")
        print(f"Configured: {config['configured']}")

if __name__ == "__main__":
    main()