"""
Supabase Environment Variable Setter

This script helps set Supabase environment variables in the .env file
and also sets them in the current environment.
"""

import os
import sys
import logging
import argparse
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

def load_environment_variables():
    """
    Load environment variables from .env file if available.
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

def set_env_vars(environment: str, url: str, key: str, service_key: Optional[str] = None) -> bool:
    """
    Set Supabase environment variables in .env file and current environment.
    
    Args:
        environment: Environment name (development, training, production)
        url: Supabase URL
        key: Supabase API key
        service_key: Supabase service key (optional)
        
    Returns:
        True if successful, False otherwise
    """
    if not DOTENV_AVAILABLE:
        logger.warning("dotenv package not installed, cannot save to .env file")
        
        # Set in current environment only
        os.environ[f"SUPABASE_URL_{environment.upper()}"] = url
        os.environ[f"SUPABASE_KEY_{environment.upper()}"] = key
        if service_key:
            os.environ[f"SUPABASE_SERVICE_KEY_{environment.upper()}"] = service_key
        
        logger.info(f"Set Supabase environment variables for {environment} in current environment")
        return False
    
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        return False
    
    try:
        # Set environment variables in .env file
        dotenv.set_key(ENV_FILE, f"SUPABASE_URL_{environment.upper()}", url)
        dotenv.set_key(ENV_FILE, f"SUPABASE_KEY_{environment.upper()}", key)
        
        # Set service key if provided
        if service_key:
            dotenv.set_key(ENV_FILE, f"SUPABASE_SERVICE_KEY_{environment.upper()}", service_key)
        
        # Set in current environment too
        os.environ[f"SUPABASE_URL_{environment.upper()}"] = url
        os.environ[f"SUPABASE_KEY_{environment.upper()}"] = key
        if service_key:
            os.environ[f"SUPABASE_SERVICE_KEY_{environment.upper()}"] = service_key
        
        # If this is 'development', also set the base variables
        if environment == "development":
            dotenv.set_key(ENV_FILE, "SUPABASE_URL", url)
            dotenv.set_key(ENV_FILE, "SUPABASE_KEY", key)
            if service_key:
                dotenv.set_key(ENV_FILE, "SUPABASE_SERVICE_KEY", service_key)
            
            os.environ["SUPABASE_URL"] = url
            os.environ["SUPABASE_KEY"] = key
            if service_key:
                os.environ["SUPABASE_SERVICE_KEY"] = service_key
        
        # If this environment is set as the active one, update base variables
        active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT")
        if active_env == environment:
            dotenv.set_key(ENV_FILE, "SUPABASE_URL", url)
            dotenv.set_key(ENV_FILE, "SUPABASE_KEY", key)
            if service_key:
                dotenv.set_key(ENV_FILE, "SUPABASE_SERVICE_KEY", service_key)
            
            os.environ["SUPABASE_URL"] = url
            os.environ["SUPABASE_KEY"] = key
            if service_key:
                os.environ["SUPABASE_SERVICE_KEY"] = service_key
        
        logger.info(f"Set Supabase environment variables for {environment} in {ENV_FILE} and current environment")
        return True
    except Exception as e:
        logger.error(f"Error setting environment variables: {str(e)}")
        return False

def set_active_environment(environment: str) -> bool:
    """
    Set the active Supabase environment.
    
    Args:
        environment: Environment name (development, training, production)
        
    Returns:
        True if successful, False otherwise
    """
    if not DOTENV_AVAILABLE:
        logger.warning("dotenv package not installed, cannot save to .env file")
        
        # Set in current environment only
        os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = environment
        logger.info(f"Set active Supabase environment to {environment} in current environment")
        return False
    
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        return False
    
    # Check if environment is configured
    env_url_var = f"SUPABASE_URL_{environment.upper()}"
    env_key_var = f"SUPABASE_KEY_{environment.upper()}"
    env_service_key_var = f"SUPABASE_SERVICE_KEY_{environment.upper()}"
    
    url = os.environ.get(env_url_var)
    key = os.environ.get(env_key_var)
    service_key = os.environ.get(env_service_key_var)
    
    if not url or not key:
        logger.error(f"Environment {environment} is not configured, cannot set as active")
        return False
    
    try:
        # Set active environment in .env file
        dotenv.set_key(ENV_FILE, "SUPABASE_ACTIVE_ENVIRONMENT", environment)
        
        # Set in current environment too
        os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = environment
        
        # Set base variables to match active environment
        dotenv.set_key(ENV_FILE, "SUPABASE_URL", url)
        dotenv.set_key(ENV_FILE, "SUPABASE_KEY", key)
        
        os.environ["SUPABASE_URL"] = url
        os.environ["SUPABASE_KEY"] = key
        
        # Set service key if available
        if service_key:
            dotenv.set_key(ENV_FILE, "SUPABASE_SERVICE_KEY", service_key)
            os.environ["SUPABASE_SERVICE_KEY"] = service_key
        
        logger.info(f"Set active Supabase environment to {environment} in {ENV_FILE} and current environment")
        return True
    except Exception as e:
        logger.error(f"Error setting active environment: {str(e)}")
        return False

def list_environments() -> List[Dict[str, Any]]:
    """
    List all configured Supabase environments.
    
    Returns:
        List of environment dictionaries with details
    """
    environments = []
    active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
    
    for env in VALID_ENVIRONMENTS:
        url = os.environ.get(f"SUPABASE_URL_{env.upper()}")
        key = os.environ.get(f"SUPABASE_KEY_{env.upper()}")
        service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{env.upper()}")
        
        environments.append({
            "name": env,
            "url": url,
            "key_available": bool(key),
            "service_key_available": bool(service_key),
            "is_active": env == active_env,
            "configured": bool(url and key)
        })
    
    return environments

def print_environments():
    """
    Print information about all configured Supabase environments.
    """
    print("\nSupabase Environments:\n")
    environments = list_environments()
    
    for env in environments:
        active_marker = "✅ ACTIVE" if env["is_active"] else ""
        configured = "✓ Configured" if env["configured"] else "✗ Not configured"
        sk_status = "✓ Available" if env["service_key_available"] else "✗ Not available"
        
        print(f"{env['name'].upper()} {active_marker}")
        print(f"  Status: {configured}")
        print(f"  URL: {env['url'] or 'Not set'}")
        print(f"  API Key: {'Available' if env['key_available'] else 'Not set'}")
        print(f"  Service Key: {sk_status}")
        print("")

def create_parser():
    """
    Create command line argument parser.
    
    Returns:
        ArgumentParser object
    """
    parser = argparse.ArgumentParser(description="Set Supabase environment variables")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Set command
    set_parser = subparsers.add_parser("set", help="Set environment variables for a Supabase environment")
    set_parser.add_argument("--env", "-e", required=True, choices=VALID_ENVIRONMENTS, help="Environment name")
    set_parser.add_argument("--url", "-u", required=True, help="Supabase URL")
    set_parser.add_argument("--key", "-k", required=True, help="Supabase API key")
    set_parser.add_argument("--service-key", "-s", help="Supabase service key (optional)")
    
    # Active command
    active_parser = subparsers.add_parser("active", help="Set active Supabase environment")
    active_parser.add_argument("env", choices=VALID_ENVIRONMENTS, help="Environment name to set as active")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all configured Supabase environments")
    
    return parser

def main():
    """Main entry point for script."""
    if not DOTENV_AVAILABLE:
        print("Warning: python-dotenv package not installed, cannot load or save to .env file")
        print("Environment variables will only be set for current process")
    
    # Load existing environment variables
    load_environment_variables()
    
    # Parse command line arguments
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "set":
        success = set_env_vars(args.env, args.url, args.key, args.service_key)
        if success:
            print(f"Successfully set Supabase environment variables for {args.env}")
            
            # Ask user if they want to set this as the active environment
            if args.env != os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT"):
                response = input(f"Do you want to set {args.env} as the active environment? (y/n): ")
                if response.lower() in ["y", "yes"]:
                    if set_active_environment(args.env):
                        print(f"Successfully set {args.env} as the active Supabase environment")
                    else:
                        print(f"Failed to set {args.env} as the active Supabase environment")
        else:
            print(f"Failed to set Supabase environment variables for {args.env}")
    
    elif args.command == "active":
        success = set_active_environment(args.env)
        if success:
            print(f"Successfully set {args.env} as the active Supabase environment")
        else:
            print(f"Failed to set {args.env} as the active Supabase environment")
    
    elif args.command == "list":
        print_environments()
    
    else:
        parser.print_help()

def ensure_supabase_env() -> Dict[str, Any]:
    """
    Ensure Supabase environment variables are set. This function is called by main.py.
    
    Returns:
        Dictionary with Supabase configuration details
    """
    # Load existing environment variables
    load_environment_variables()
    
    # Get active environment
    active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
    
    # Check if we have the required variables for this environment
    env_url_var = f"SUPABASE_URL_{active_env.upper()}"
    env_key_var = f"SUPABASE_KEY_{active_env.upper()}"
    env_service_key_var = f"SUPABASE_SERVICE_KEY_{active_env.upper()}"
    
    url = os.environ.get(env_url_var) or os.environ.get("SUPABASE_URL")
    key = os.environ.get(env_key_var) or os.environ.get("SUPABASE_KEY")
    service_key = os.environ.get(env_service_key_var) or os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        logger.warning(f"Supabase environment variables not set for {active_env}")
        
        # For development/testing, use default test credentials if available
        if active_env == "development" and not (url and key):
            # Default development variables if none are set
            if not url:
                os.environ["SUPABASE_URL"] = "https://example-project.supabase.co"
            if not key:
                os.environ["SUPABASE_KEY"] = "eyJhbGciOiJI.eyJyb2xlIjoiYW5vbi.A123EXAMPLE"
            
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")
            
            logger.warning("Using placeholder Supabase credentials for development")
            logger.warning("Please set real credentials using set_supabase_env.py")
    
    # Update base variables to match active environment
    if url and active_env:
        os.environ["SUPABASE_URL"] = url
    if key and active_env:
        os.environ["SUPABASE_KEY"] = key
    if service_key and active_env:
        os.environ["SUPABASE_SERVICE_KEY"] = service_key
    
    return {
        "environment": active_env,
        "url": url,
        "key_available": bool(key),
        "service_key_available": bool(service_key),
        "configured": bool(url and key)
    }

if __name__ == "__main__":
    main()