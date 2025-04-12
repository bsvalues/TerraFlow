#!/usr/bin/env python3
"""
Script to set up Supabase environment variables.
This script prompts the user for Supabase credentials and saves them to the environment.
"""

import os
import sys
import logging
import json
from getpass import getpass
import dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("set_supabase_env")

def ensure_supabase_env():
    """
    Ensure Supabase environment variables are set.
    If running non-interactively (e.g., in a server context), this will
    attempt to load from .env file or environment without prompting.
    
    Returns:
        dict: Dictionary with Supabase configuration
    """
    # Load from .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        dotenv.load_dotenv(env_file)
    
    # Check if all required variables are set
    missing_vars = []
    supabase_config = {}
    
    for var in REQUIRED_VARS.keys():
        value = os.environ.get(var)
        if value:
            supabase_config[var] = value
        else:
            missing_vars.append(var)
    
    # If all variables are present, return the config
    if not missing_vars:
        logger.info("All Supabase environment variables are set")
        return supabase_config
    
    # If server mode, log a warning about missing variables
    logger.warning(f"Missing Supabase environment variables: {', '.join(missing_vars)}")
    logger.info("Using development fallback values for Supabase integration")
    
    # Set development fallback values (not for production use)
    for var in missing_vars:
        if var == "SUPABASE_URL":
            # Use a placeholder URL that won't connect
            supabase_config[var] = "https://example.supabase.co"
        elif var in ["SUPABASE_KEY", "SUPABASE_SERVICE_KEY"]:
            # Use placeholder keys that won't authenticate
            supabase_config[var] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV4YW1wbGUiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYxNjQxMjQ5MiwiZXhwIjoxOTMyMDg4NDkyfQ.development_fallback"
    
    # Set the environment variables
    for var, value in supabase_config.items():
        os.environ[var] = value
    
    return supabase_config

# Required environment variables
REQUIRED_VARS = {
    "SUPABASE_URL": "Supabase project URL (e.g., https://your-project-id.supabase.co)",
    "SUPABASE_KEY": "Supabase anon/public key (from API settings)",
    "SUPABASE_SERVICE_KEY": "Supabase service role key (from API settings)"
}

def get_current_env():
    """
    Get current environment variables.
    
    Returns:
        dict: Dictionary with current values
    """
    current_values = {}
    for var in REQUIRED_VARS:
        value = os.environ.get(var)
        if value:
            masked_value = value[:5] + "*" * (len(value) - 8) + value[-3:] if len(value) > 10 else "********"
            current_values[var] = {
                "set": True,
                "value_sample": masked_value
            }
        else:
            current_values[var] = {
                "set": False
            }
    return current_values

def prompt_for_values(current_values):
    """
    Prompt user for Supabase credentials.
    
    Args:
        current_values (dict): Dictionary with current values
        
    Returns:
        dict: Dictionary with new values
    """
    new_values = {}
    
    logger.info("Please enter the following Supabase credentials.")
    logger.info("You can find these in your Supabase project settings > API.")
    logger.info("(Press Enter to keep current value if one exists)\n")
    
    for var, description in REQUIRED_VARS.items():
        prompt = f"{var} [{description}]"
        
        if var in current_values and current_values[var].get("set"):
            prompt += f" (current: {current_values[var].get('value_sample')})"
        
        # Use getpass for sensitive information
        if "KEY" in var:
            value = getpass(f"{prompt}: ")
        else:
            value = input(f"{prompt}: ")
        
        # Keep current value if user just presses Enter
        if not value and var in current_values and current_values[var].get("set"):
            value = os.environ.get(var)
            logger.info(f"Keeping current value for {var}")
        
        if value:
            new_values[var] = value
    
    return new_values

def save_to_env_file(env_vars, env_file=".env"):
    """
    Save environment variables to .env file.
    
    Args:
        env_vars (dict): Dictionary with environment variables
        env_file (str): Path to .env file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load existing .env file if it exists
        if os.path.exists(env_file):
            dotenv.load_dotenv(env_file)
        
        # Update with new values
        for var, value in env_vars.items():
            dotenv.set_key(env_file, var, value)
        
        logger.info(f"✅ Environment variables saved to {env_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving to .env file: {str(e)}")
        return False

def save_to_replit_secrets(env_vars):
    """
    Save environment variables to Replit Secrets.
    
    Args:
        env_vars (dict): Dictionary with environment variables
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if we're running on Replit
        if "REPL_ID" not in os.environ:
            logger.info("Not running on Replit, skipping Replit Secrets")
            return False
        
        # Import Replit DB module
        try:
            from replit import db
            has_replit_db = True
        except ImportError:
            logger.warning("Replit DB module not available, can't save to Replit Secrets")
            return False
        
        if has_replit_db:
            for var, value in env_vars.items():
                db[var] = value
            
            logger.info("✅ Environment variables saved to Replit Secrets")
            return True
    except Exception as e:
        logger.error(f"Error saving to Replit Secrets: {str(e)}")
        return False

def main():
    """Main function"""
    logger.info("=== Supabase Environment Setup ===")
    
    # Get current environment
    current_values = get_current_env()
    
    # Prompt for values
    env_vars = prompt_for_values(current_values)
    
    if not env_vars:
        logger.warning("No environment variables were entered. Exiting.")
        return 1
    
    # Export to environment
    for var, value in env_vars.items():
        os.environ[var] = value
    
    logger.info("✅ Environment variables set for current session")
    
    # Save to .env file
    save_to_env_file(env_vars)
    
    # Try to save to Replit Secrets
    save_to_replit_secrets(env_vars)
    
    logger.info("\n=== Next Steps ===")
    logger.info("1. Run 'python verify_supabase_env.py' to verify the environment variables")
    logger.info("2. Run 'python test_supabase_connection.py' to test the connection")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())