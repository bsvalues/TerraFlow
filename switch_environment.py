#!/usr/bin/env python
"""
Switch Environment Script

This script allows you to easily switch between development, training, and
production environments for the GeoAssessmentPro application.
"""

import os
import sys
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
VALID_ENVIRONMENTS = ["development", "training", "production"]
ENV_FILE = ".env"

def save_environment_variables(variables):
    """
    Save environment variables to .env file.
    
    Args:
        variables: Dict of variables to save
    """
    # Read existing .env file if it exists
    existing_vars = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    existing_vars[key] = value

    # Update with new variables
    existing_vars.update(variables)
    
    # Write back to .env file
    with open(ENV_FILE, "w") as f:
        for key, value in existing_vars.items():
            f.write(f"{key}={value}\n")
    
    logger.info(f"Updated environment variables in {ENV_FILE}")

def switch_environment(environment):
    """
    Switch to the specified environment.
    
    Args:
        environment: The environment to switch to (development, training, production)
    
    Returns:
        True if successful, False otherwise
    """
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        logger.error(f"Valid environments are: {', '.join(VALID_ENVIRONMENTS)}")
        return False
    
    logger.info(f"Switching to {environment} environment")
    
    # Set the environment in the .env file
    save_environment_variables({
        "ENV_MODE": environment
    })
    
    # Set environment-specific variables
    if environment == "training":
        # Check if training URL is set
        if not os.environ.get("DATABASE_URL_TRAINING"):
            logger.warning("DATABASE_URL_TRAINING is not set")
            logger.warning("Please set it in the .env file or as an environment variable")
    elif environment == "production":
        # Check if production URL is set
        if not os.environ.get("DATABASE_URL_PRODUCTION"):
            logger.warning("DATABASE_URL_PRODUCTION is not set")
            logger.warning("Please set it in the .env file or as an environment variable")
    
    logger.info(f"Successfully switched to {environment} environment")
    return True

def get_current_environment():
    """
    Get the current environment from the .env file or environment variable.
    
    Returns:
        The current environment (development, training, production)
    """
    env_mode = os.environ.get("ENV_MODE")
    if not env_mode and os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ENV_MODE="):
                    env_mode = line.split("=", 1)[1]
                    break
    
    return env_mode.lower() if env_mode else "development"

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Switch between environments")
    parser.add_argument("environment", nargs="?", choices=VALID_ENVIRONMENTS,
                       help="The environment to switch to (development, training, production)")
    parser.add_argument("--status", action="store_true", 
                       help="Show the current environment status")
    
    args = parser.parse_args()
    
    if args.status or not args.environment:
        current_env = get_current_environment()
        print(f"Current environment: {current_env}")
        
        # Show database URLs
        dev_url = os.environ.get("DATABASE_URL", "Not set")
        train_url = os.environ.get("DATABASE_URL_TRAINING", "Not set")
        prod_url = os.environ.get("DATABASE_URL_PRODUCTION", "Not set")
        
        if len(dev_url) > 30:
            dev_url = f"{dev_url[:27]}..."
        if len(train_url) > 30:
            train_url = f"{train_url[:27]}..."
        if len(prod_url) > 30:
            prod_url = f"{prod_url[:27]}..."
        
        print("\nDatabase URLs:")
        print(f"  Development: {dev_url}")
        print(f"  Training:    {train_url}")
        print(f"  Production:  {prod_url}")
        
        # Show Supabase URLs
        supabase_url = os.environ.get("SUPABASE_URL", "Not set")
        supabase_train_url = os.environ.get("SUPABASE_URL_TRAINING", "Not set")
        supabase_prod_url = os.environ.get("SUPABASE_URL_PRODUCTION", "Not set")
        
        if len(supabase_url) > 30:
            supabase_url = f"{supabase_url[:27]}..."
        if len(supabase_train_url) > 30:
            supabase_train_url = f"{supabase_train_url[:27]}..."
        if len(supabase_prod_url) > 30:
            supabase_prod_url = f"{supabase_prod_url[:27]}..."
        
        print("\nSupabase URLs:")
        print(f"  Development: {supabase_url}")
        print(f"  Training:    {supabase_train_url}")
        print(f"  Production:  {supabase_prod_url}")
        
        return 0
        
    result = switch_environment(args.environment)
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())