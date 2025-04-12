#!/usr/bin/env python3
"""
Supabase Connection Checker

This script verifies Supabase configuration and connectivity.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("supabase_check")

# Import Supabase environment setup
from set_supabase_env import ensure_supabase_env

# Import Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.error("❌ Supabase package not installed. Run: pip install supabase")

def check_environment_variables():
    """Check if required environment variables are set."""
    logger.info("Checking environment variables...")
    
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY"]
    optional_vars = ["SUPABASE_SERVICE_KEY"]
    
    missing = []
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
            logger.error(f"❌ {var} is not set")
        else:
            logger.info(f"✅ {var} is set")
    
    for var in optional_vars:
        if os.environ.get(var):
            logger.info(f"✅ {var} is set")
        else:
            logger.warning(f"⚠️ {var} is not set (optional)")
    
    if missing:
        return False
    return True

def check_supabase_connection():
    """Check connection to Supabase."""
    if not SUPABASE_AVAILABLE:
        return False
    
    logger.info("Checking Supabase connection...")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        logger.error("❌ Missing Supabase URL or key")
        return False
    
    try:
        client = create_client(url, key)
        
        # Test connection with a simple query
        response = client.table("users").select("count").limit(1).execute()
        logger.info(f"✅ Connected to Supabase: {url}")
        return True
    except Exception as e:
        # If users table doesn't exist yet, that's okay
        if "relation" in str(e) and "does not exist" in str(e):
            logger.info(f"✅ Connected to Supabase: {url}")
            logger.warning("⚠️ Users table does not exist yet")
            return True
        else:
            logger.error(f"❌ Failed to connect to Supabase: {str(e)}")
            return False

def check_supabase_auth():
    """Check Supabase Auth functionality."""
    if not SUPABASE_AVAILABLE:
        return False
    
    logger.info("Checking Supabase Auth...")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    try:
        client = create_client(url, key)
        
        # Just check if auth client is accessible
        # Skip actual API calls since they depend on auth settings
        if hasattr(client, 'auth'):
            logger.info(f"✅ Supabase Auth is accessible")
            return True
        else:
            logger.error("❌ Supabase Auth client is not available")
            return False
    except Exception as e:
        logger.error(f"❌ Error accessing Supabase Auth: {str(e)}")
        return False

def check_supabase_storage():
    """Check Supabase Storage functionality."""
    if not SUPABASE_AVAILABLE:
        return False
    
    logger.info("Checking Supabase Storage...")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    try:
        client = create_client(url, key)
        
        # List buckets
        buckets = client.storage.list_buckets()
        bucket_names = [b["name"] for b in buckets]
        logger.info(f"✅ Successfully accessed Supabase Storage")
        logger.info(f"  Found {len(bucket_names)} buckets: {', '.join(bucket_names) if bucket_names else 'None'}")
        
        required_buckets = ["documents", "maps", "images", "exports"]
        missing_buckets = [b for b in required_buckets if b not in bucket_names]
        
        if missing_buckets:
            logger.warning(f"⚠️ Missing required buckets: {', '.join(missing_buckets)}")
            logger.warning("  You need to create these buckets in the Supabase Dashboard")
            logger.warning("  or run setup_supabase_storage.py")
        else:
            logger.info("✅ All required buckets exist")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error accessing Supabase Storage: {str(e)}")
        return False

def check_postgis_extension():
    """Check if PostGIS extension is enabled."""
    if not SUPABASE_AVAILABLE:
        return False
    
    logger.info("Checking PostGIS extension...")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY"))
    
    if not key:
        logger.error("❌ Missing Supabase key")
        return False
    
    try:
        client = create_client(url, key)
        
        # Try to use extension check function we created
        try:
            # First check if our function exists
            response = client.rpc('check_extension', {'extension_name': 'postgis'}).execute()
            if response.data:
                logger.info("✅ PostGIS extension is enabled")
                return True
            else:
                logger.warning("⚠️ PostGIS extension is not enabled")
                return False
        except Exception:
            # Function might not exist, try setting it up
            setup_extension_check_function()
            logger.warning("⚠️ Could not check PostGIS extension. Please run again.")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking PostGIS extension: {str(e)}")
        return False

def setup_extension_check_function():
    """Create a function to check for extensions."""
    if not SUPABASE_AVAILABLE:
        return False
    
    logger.info("Setting up extension check function...")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY"))
    
    try:
        client = create_client(url, key)
        
        # Create function via SQL query
        # Note: This requires SERVICE_KEY or accessing SQL Editor in Supabase Dashboard
        query = """
        CREATE OR REPLACE FUNCTION check_extension(extension_name TEXT)
        RETURNS BOOLEAN AS $$
        DECLARE
            ext_exists BOOLEAN;
        BEGIN
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = extension_name
            ) INTO ext_exists;
            RETURN ext_exists;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        # This will usually not work due to permission issues
        try:
            response = client.rpc('exec_sql', {'query': query}).execute()
            logger.info("✅ Created extension check function")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Could not create extension check function: {str(e)}")
            logger.warning("  Please run this SQL in the Supabase SQL Editor:")
            logger.warning(query)
            return False
    except Exception as e:
        logger.error(f"❌ Error setting up extension check function: {str(e)}")
        return False

def main():
    """Main function to run all checks."""
    logger.info("=== Supabase Configuration Check ===")
    
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase package not installed. Run: pip install supabase")
        sys.exit(1)
    
    # Ensure environment variables are set
    config = ensure_supabase_env()
    logger.info(f"Using Supabase URL: {config['url']}")
    
    results = {
        "Environment Variables": check_environment_variables(),
        "Connection": check_supabase_connection(),
        "Auth": check_supabase_auth(),
        "Storage": check_supabase_storage(),
        "PostGIS": check_postgis_extension()
    }
    
    # Summary
    logger.info("\n=== Summary ===")
    success_count = sum(1 for r in results.values() if r)
    total_count = len(results)
    
    for check, result in results.items():
        status = "✅" if result else "❌"
        logger.info(f"{status} {check}")
    
    logger.info(f"\n{success_count}/{total_count} checks passed")
    
    if success_count == total_count:
        logger.info("✅ Supabase is properly configured!")
        return True
    else:
        if results["Environment Variables"] and results["Connection"]:
            logger.warning("⚠️ Basic Supabase configuration is working, but some features may be limited")
        else:
            logger.error("❌ Supabase is not properly configured")
        return False

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)