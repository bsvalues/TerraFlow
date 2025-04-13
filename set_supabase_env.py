#!/usr/bin/env python3
"""
Set Supabase Environment Variables

This script allows setting Supabase environment variables for different environments
(development, training, production) from the command line. It updates the .env file
and can set the current active environment.
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("set_supabase_env")

def set_env_vars(environment: str, url: str, key: str, service_key: Optional[str] = None, save_to_env: bool = True) -> bool:
    """
    Set Supabase environment variables for a specific environment.
    
    Args:
        environment: Environment name (development, training, production)
        url: Supabase URL
        key: Supabase API key
        service_key: Optional Supabase service role key
        save_to_env: Whether to save to .env file
        
    Returns:
        True if successful, False otherwise
    """
    if environment not in ['development', 'training', 'production']:
        logger.error(f"Invalid environment: {environment}. Must be one of: development, training, production")
        return False
    
    # Load existing environment variables
    load_dotenv()
    
    # Set environment-specific variables
    env_var_url = f"SUPABASE_URL_{environment.upper()}"
    env_var_key = f"SUPABASE_KEY_{environment.upper()}"
    env_var_service_key = f"SUPABASE_SERVICE_KEY_{environment.upper()}"
    
    # Update environment variables
    os.environ[env_var_url] = url
    os.environ[env_var_key] = key
    
    if service_key:
        os.environ[env_var_service_key] = service_key
    elif env_var_service_key in os.environ:
        os.environ.pop(env_var_service_key)
    
    # If this is the development environment or we're setting the active environment,
    # also update the base variables
    if environment == 'development':
        os.environ['SUPABASE_URL'] = url
        os.environ['SUPABASE_KEY'] = key
        if service_key:
            os.environ['SUPABASE_SERVICE_KEY'] = service_key
        elif 'SUPABASE_SERVICE_KEY' in os.environ:
            os.environ.pop('SUPABASE_SERVICE_KEY')
    
    logger.info(f"Updated Supabase {environment} environment variables")
    
    # Save to .env file if requested
    if save_to_env:
        return update_env_file(environment, url, key, service_key)
    
    return True

def update_env_file(environment: str, url: str, key: str, service_key: Optional[str] = None) -> bool:
    """
    Update .env file with Supabase environment variables.
    
    Args:
        environment: Environment name
        url: Supabase URL
        key: Supabase API key
        service_key: Optional Supabase service role key
        
    Returns:
        True if successful, False otherwise
    """
    try:
        env_path = ".env"
        env_vars = {}
        
        # Read existing .env file
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        name, value = line.split('=', 1)
                        env_vars[name.strip()] = value.strip()
        
        # Update with new values
        env_vars[f"SUPABASE_URL_{environment.upper()}"] = url
        env_vars[f"SUPABASE_KEY_{environment.upper()}"] = key
        if service_key:
            env_vars[f"SUPABASE_SERVICE_KEY_{environment.upper()}"] = service_key
        elif f"SUPABASE_SERVICE_KEY_{environment.upper()}" in env_vars:
            del env_vars[f"SUPABASE_SERVICE_KEY_{environment.upper()}"]
        
        # If this is the development environment, also set the base variables
        if environment == "development":
            env_vars["SUPABASE_URL"] = url
            env_vars["SUPABASE_KEY"] = key
            if service_key:
                env_vars["SUPABASE_SERVICE_KEY"] = service_key
            elif "SUPABASE_SERVICE_KEY" in env_vars:
                del env_vars["SUPABASE_SERVICE_KEY"]
        
        # Write back to .env file
        with open(env_path, 'w') as f:
            for name, value in env_vars.items():
                f.write(f"{name}={value}\n")
        
        logger.info(f"Updated .env file with {environment} environment variables")
        return True
    
    except Exception as e:
        logger.error(f"Error updating .env file: {str(e)}")
        return False

def set_active_environment(environment: str) -> bool:
    """
    Set the active Supabase environment.
    
    Args:
        environment: Environment name
        
    Returns:
        True if successful, False otherwise
    """
    if environment not in ['development', 'training', 'production']:
        logger.error(f"Invalid environment: {environment}. Must be one of: development, training, production")
        return False
    
    # Load existing environment variables
    load_dotenv()
    
    # Get environment-specific variables
    url = os.environ.get(f"SUPABASE_URL_{environment.upper()}")
    key = os.environ.get(f"SUPABASE_KEY_{environment.upper()}")
    service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{environment.upper()}")
    
    if not url or not key:
        logger.error(f"Supabase {environment} environment is not configured. Set it up first.")
        return False
    
    # Set the base variables to the selected environment
    os.environ['SUPABASE_URL'] = url
    os.environ['SUPABASE_KEY'] = key
    if service_key:
        os.environ['SUPABASE_SERVICE_KEY'] = service_key
    elif 'SUPABASE_SERVICE_KEY' in os.environ:
        os.environ.pop('SUPABASE_SERVICE_KEY')
    
    logger.info(f"Set active Supabase environment to: {environment}")
    
    # Save to .env file
    env_path = ".env"
    env_vars = {}
    
    # Read existing .env file
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    name, value = line.split('=', 1)
                    env_vars[name.strip()] = value.strip()
    
    # Update base variables
    env_vars['SUPABASE_URL'] = url
    env_vars['SUPABASE_KEY'] = key
    if service_key:
        env_vars['SUPABASE_SERVICE_KEY'] = service_key
    elif 'SUPABASE_SERVICE_KEY' in env_vars:
        del env_vars['SUPABASE_SERVICE_KEY']
    
    # Add SUPABASE_ACTIVE_ENVIRONMENT variable
    env_vars['SUPABASE_ACTIVE_ENVIRONMENT'] = environment
    
    # Write back to .env file
    with open(env_path, 'w') as f:
        for name, value in env_vars.items():
            f.write(f"{name}={value}\n")
    
    # Reload environment
    try:
        from supabase_env_manager import load_environment_from_env
        load_environment_from_env()
    except ImportError:
        load_dotenv()
    
    return True

def display_environment_info():
    """Display information about all configured environments."""
    # Load existing environment variables
    load_dotenv()
    
    # Check which environments are configured
    environments = {}
    for env in ['development', 'training', 'production']:
        url = os.environ.get(f"SUPABASE_URL_{env.upper()}")
        key = os.environ.get(f"SUPABASE_KEY_{env.upper()}")
        service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{env.upper()}")
        
        environments[env] = {
            'configured': bool(url and key),
            'url': url,
            'key': key,
            'service_key': bool(service_key)
        }
    
    # Check active environment
    active_env = os.environ.get('SUPABASE_ACTIVE_ENVIRONMENT', 'development')
    
    # Display environment information
    print("=== Supabase Environment Status ===")
    for env, config in environments.items():
        status_color = "\033[92m" if config['configured'] else "\033[91m"
        active_marker = " (active)" if env == active_env else ""
        reset_color = "\033[0m"
        
        print(f"Environment: {env}{active_marker}")
        print(f"Status: {status_color}{'configured' if config['configured'] else 'not configured'}{reset_color}")
        if config['configured']:
            print(f"URL: {config['url']}")
            print(f"API Key: {'*' * 8}{config['key'][-5:] if config['key'] else ''}")
            print(f"Service Key: {'Available' if config['service_key'] else 'Not set'}")
        print("")
    
    print(f"Active Environment: {active_env}")

def ensure_supabase_env() -> dict:
    """
    Ensure Supabase environment variables are set.
    This function is called from main.py to set up the Supabase environment.
    
    Returns:
        Dict with environment configuration
    """
    # Load from .env if available
    load_dotenv()
    
    # Check if already set
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        logger.info("All Supabase environment variables are set")
        return {
            "url": os.environ.get("SUPABASE_URL"),
            "key": os.environ.get("SUPABASE_KEY"),
            "service_key": os.environ.get("SUPABASE_SERVICE_KEY"),
            "environment": os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
        }
    
    # If not set, check for environment-specific variables
    for env in ["DEVELOPMENT", "TRAINING", "PRODUCTION"]:
        url = os.environ.get(f"SUPABASE_URL_{env}")
        key = os.environ.get(f"SUPABASE_KEY_{env}")
        service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{env}")
        if url and key:
            # Use this environment as default
            os.environ["SUPABASE_URL"] = url
            os.environ["SUPABASE_KEY"] = key
            if service_key:
                os.environ["SUPABASE_SERVICE_KEY"] = service_key
            
            environment = env.lower()
            os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = environment
            logger.info(f"Using {environment} environment as default")
            
            return {
                "url": url,
                "key": key,
                "service_key": service_key,
                "environment": environment
            }
    
    # If no environment variables found, log warning
    logger.warning("No Supabase environment variables found. Default to development mode with incomplete configuration.")
    return {
        "url": None,
        "key": None,
        "service_key": None,
        "environment": "development"
    }

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Set Supabase Environment Variables")
    parser.add_argument("-e", "--environment", 
                        choices=["development", "training", "production"], 
                        help="Environment to configure")
    parser.add_argument("-u", "--url", 
                        help="Supabase URL")
    parser.add_argument("-k", "--key", 
                        help="Supabase API key")
    parser.add_argument("-s", "--service-key", 
                        help="Supabase service role key (optional)")
    parser.add_argument("-a", "--activate", 
                        choices=["development", "training", "production"], 
                        help="Set active environment")
    parser.add_argument("-d", "--display", action="store_true", 
                        help="Display environment information")
    parser.add_argument("--no-save", action="store_true", 
                        help="Don't save to .env file")
    
    args = parser.parse_args()
    
    # Display environment information
    if args.display:
        display_environment_info()
        return
    
    # Set active environment
    if args.activate:
        if set_active_environment(args.activate):
            print(f"Successfully set active environment to: {args.activate}")
        else:
            print(f"Failed to set active environment to: {args.activate}")
        return
    
    # Set environment variables
    if args.environment and args.url and args.key:
        save_to_env = not args.no_save
        if set_env_vars(args.environment, args.url, args.key, args.service_key, save_to_env):
            print(f"Successfully set {args.environment} environment variables")
            display_environment_info()
        else:
            print(f"Failed to set {args.environment} environment variables")
        return
    
    # If no arguments or incomplete arguments, show usage information
    if not (args.display or args.activate or (args.environment and args.url and args.key)):
        parser.print_help()

if __name__ == "__main__":
    main()