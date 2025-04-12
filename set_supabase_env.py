#!/usr/bin/env python3
"""
Supabase Environment Setup Script

This script ensures that Supabase environment variables are set properly
across the application. It can be imported at application startup or
run directly.
"""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("supabase_env")

# Default Supabase credentials
DEFAULT_SUPABASE_URL = "https://romjfbwktyxljvgcthmk.supabase.co"

def ensure_supabase_env():
    """Ensure Supabase environment variables are set."""
    # Set SUPABASE_URL if not already set
    if "SUPABASE_URL" not in os.environ or not os.environ["SUPABASE_URL"]:
        os.environ["SUPABASE_URL"] = DEFAULT_SUPABASE_URL
        logger.info(f"Set SUPABASE_URL to {DEFAULT_SUPABASE_URL}")
    else:
        logger.info(f"Using existing SUPABASE_URL: {os.environ['SUPABASE_URL']}")
    
    # Check if keys are available
    if "SUPABASE_KEY" not in os.environ or not os.environ["SUPABASE_KEY"]:
        logger.warning("SUPABASE_KEY is not set in environment")
    else:
        logger.info("SUPABASE_KEY is available in environment")
        
    if "SUPABASE_SERVICE_KEY" not in os.environ or not os.environ["SUPABASE_SERVICE_KEY"]:
        logger.warning("SUPABASE_SERVICE_KEY is not set in environment")
    else:
        logger.info("SUPABASE_SERVICE_KEY is available in environment")
    
    # Set explicit USE_SUPABASE flag
    if all(k in os.environ and os.environ[k] for k in ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_KEY"]):
        os.environ["USE_SUPABASE"] = "true"
        logger.info("Set USE_SUPABASE=true based on available credentials")
    else:
        os.environ["USE_SUPABASE"] = "false"
        logger.warning("Set USE_SUPABASE=false due to missing credentials")
    
    return {
        "url": os.environ.get("SUPABASE_URL"),
        "key": os.environ.get("SUPABASE_KEY", ""),
        "service_key": os.environ.get("SUPABASE_SERVICE_KEY", ""),
        "use_supabase": os.environ.get("USE_SUPABASE", "false") == "true"
    }

if __name__ == "__main__":
    config = ensure_supabase_env()
    logger.info(f"Supabase configuration: URL={config['url']}, USE_SUPABASE={config['use_supabase']}")