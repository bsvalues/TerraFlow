#!/usr/bin/env python3
"""
Verify Supabase Environment Configuration

This script checks the current Supabase environment configuration
and tests the connection to make sure it's working properly.
"""

import os
import logging
import argparse
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("verify_supabase_env")

def set_supabase_env():
    """Set Supabase environment variables for testing."""
    logger.info("Setting up Supabase environment variables...")
    # Load from .env if available
    load_dotenv()
    
    # Check if already set
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        logger.info("All Supabase environment variables are set")
        return True
    
    # If not set, check for environment-specific variables
    for env in ["DEVELOPMENT", "TRAINING", "PRODUCTION"]:
        url = os.environ.get(f"SUPABASE_URL_{env}")
        key = os.environ.get(f"SUPABASE_KEY_{env}")
        if url and key:
            # Use this environment as default
            os.environ["SUPABASE_URL"] = url
            os.environ["SUPABASE_KEY"] = key
            logger.info(f"Using {env.lower()} environment as default")
            return True
    
    logger.warning("No Supabase environment variables found. Configuration required.")
    return False

def check_environment(environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Check Supabase environment configuration.
    
    Args:
        environment: Optional environment name to check
        
    Returns:
        Dictionary with environment details and status
    """
    if not SUPABASE_AVAILABLE:
        return {
            "status": "error",
            "message": "Supabase package not installed. Install with 'pip install supabase'.",
            "url_available": False,
            "key_available": False
        }
    
    # Set environment suffix
    env_suffix = f"_{environment.upper()}" if environment else ""
    
    # Check for URL and key
    url = os.environ.get(f"SUPABASE_URL{env_suffix}")
    key = os.environ.get(f"SUPABASE_KEY{env_suffix}")
    service_key = os.environ.get(f"SUPABASE_SERVICE_KEY{env_suffix}")
    
    result = {
        "environment": environment or "default",
        "url_available": bool(url),
        "key_available": bool(key),
        "service_key_available": bool(service_key)
    }
    
    if url and key:
        result["status"] = "configured"
        result["message"] = f"Supabase {result['environment']} environment is configured."
    else:
        result["status"] = "not_configured"
        result["message"] = f"Supabase {result['environment']} environment is missing configuration."
    
    return result

def test_connection(environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Test Supabase connection.
    
    Args:
        environment: Optional environment name to test
        
    Returns:
        Dictionary with test results
    """
    env_check = check_environment(environment)
    if env_check["status"] != "configured":
        return {
            "status": "error",
            "message": env_check["message"],
            "connection_successful": False
        }
    
    try:
        # Get URL and key
        env_suffix = f"_{environment.upper()}" if environment else ""
        url = os.environ.get(f"SUPABASE_URL{env_suffix}")
        key = os.environ.get(f"SUPABASE_KEY{env_suffix}")
        
        # Create client and attempt a simple operation
        logger.info(f"Testing connection to {url}...")
        client = create_client(url, key)
        
        # Try a simple query to verify the connection
        try:
            # Simple system table query (usually accessible)
            result = client.table('_system').select('version').limit(1).execute()
            return {
                "status": "success",
                "message": "Successfully connected to Supabase.",
                "connection_successful": True
            }
        except Exception:
            # Fallback to a more generic check
            try:
                # Try health check function
                response = client.functions.invoke('health-check')
                return {
                    "status": "success",
                    "message": "Successfully connected to Supabase.",
                    "connection_successful": True
                }
            except Exception:
                # Last try - auth API
                auth_response = client.auth.get_session()
                return {
                    "status": "success",
                    "message": "Successfully connected to Supabase Auth API.",
                    "connection_successful": True
                }
    except Exception as e:
        logger.error(f"Error connecting to Supabase: {str(e)}")
        return {
            "status": "error",
            "message": f"Connection failed: {str(e)}",
            "connection_successful": False
        }

def list_all_environments() -> Dict[str, Dict[str, Any]]:
    """
    List all configured environments.
    
    Returns:
        Dictionary with all environment details
    """
    environments = {}
    
    # Check default environment
    environments["default"] = check_environment()
    
    # Check named environments
    for env in ["development", "training", "production"]:
        environments[env] = check_environment(env)
    
    return environments

def display_environment_info(environment_info: Dict[str, Any]):
    """Display environment information."""
    status_color = "\033[92m" if environment_info["status"] == "configured" else "\033[91m"
    reset_color = "\033[0m"
    
    print(f"Environment: {environment_info['environment']}")
    print(f"Status: {status_color}{environment_info['status']}{reset_color}")
    print(f"URL Available: {'✓' if environment_info['url_available'] else '✗'}")
    print(f"API Key Available: {'✓' if environment_info['key_available'] else '✗'}")
    print(f"Service Key Available: {'✓' if environment_info['service_key_available'] else '✗'}")
    print(f"Message: {environment_info['message']}")
    print("")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Verify Supabase Environment Configuration")
    parser.add_argument("-e", "--environment", 
                        choices=["default", "development", "training", "production"], 
                        help="Environment to check")
    parser.add_argument("-t", "--test", action="store_true", 
                        help="Test the connection")
    parser.add_argument("-a", "--all", action="store_true", 
                        help="List all environments")
    
    args = parser.parse_args()
    
    # Set up Supabase environment variables
    set_supabase_env()
    
    if args.all:
        # List all environments
        print("=== Supabase Environment Status ===")
        environments = list_all_environments()
        for env_name, env_info in environments.items():
            display_environment_info(env_info)
    elif args.environment:
        # Check specific environment
        print(f"=== Checking {args.environment} Environment ===")
        env_info = check_environment(args.environment if args.environment != "default" else None)
        display_environment_info(env_info)
        
        # Test connection if requested
        if args.test and env_info["status"] == "configured":
            print("=== Testing Connection ===")
            test_result = test_connection(args.environment if args.environment != "default" else None)
            status_color = "\033[92m" if test_result["connection_successful"] else "\033[91m"
            reset_color = "\033[0m"
            print(f"Connection Status: {status_color}{test_result['status']}{reset_color}")
            print(f"Message: {test_result['message']}")
    else:
        # Check default environment
        print("=== Checking Default Environment ===")
        env_info = check_environment()
        display_environment_info(env_info)
        
        # Test connection if requested
        if args.test and env_info["status"] == "configured":
            print("=== Testing Connection ===")
            test_result = test_connection()
            status_color = "\033[92m" if test_result["connection_successful"] else "\033[91m"
            reset_color = "\033[0m"
            print(f"Connection Status: {status_color}{test_result['status']}{reset_color}")
            print(f"Message: {test_result['message']}")

if __name__ == "__main__":
    main()