#!/usr/bin/env python3
"""
Supabase Environment Verification Script

This script verifies that the Supabase environment variables are correctly set
and loads them for other modules to use.
"""

import os
import sys
import logging
from set_supabase_env import ensure_supabase_env
from check_supabase import main as check_supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("verify_supabase_env")

def main():
    """Main function to verify and set Supabase environment variables."""
    logger.info("=== Supabase Environment Verification ===")
    
    # Make sure Supabase environment variables are set
    config = ensure_supabase_env()
    
    # Add Supabase URL to environment variables if needed
    if "url" in config and config["url"]:
        os.environ["SUPABASE_URL"] = config["url"]
        logger.info(f"SUPABASE_URL set to {config['url']}")
    else:
        logger.error("SUPABASE_URL is not available in configuration")
        sys.exit(1)
    
    # Log other Supabase settings (without showing the actual keys)
    logger.info(f"SUPABASE_KEY is {'available' if 'key' in config and config['key'] else 'missing'}")
    logger.info(f"SUPABASE_SERVICE_KEY is {'available' if 'service_key' in config and config['service_key'] else 'missing'}")
    logger.info(f"USE_SUPABASE is set to {config.get('use_supabase', False)}")
    
    # Run checks if environment variables are set
    if all(k in os.environ and os.environ[k] for k in ["SUPABASE_URL", "SUPABASE_KEY"]):
        logger.info("Running Supabase connection checks...")
        check_supabase()
    else:
        logger.warning("Skipping connection checks because environment variables are not set")
    
    logger.info("Verification complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())