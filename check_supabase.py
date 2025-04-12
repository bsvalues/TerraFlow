#!/usr/bin/env python3
"""
Supabase Connection Checker

This script verifies Supabase configuration and connectivity.
"""

import os
import sys
import logging
import time
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("supabase_check")

# Check if Supabase package is available
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    logger.error("❌ Supabase package not installed. Run: pip install supabase")
    HAS_SUPABASE = False

def check_environment_variables():
    """Check if required environment variables are set."""
    logger.info("Checking environment variables...")
    
    required_vars = {
        "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
        "SUPABASE_KEY": os.environ.get("SUPABASE_KEY")
    }
    
    missing = [key for key, value in required_vars.items() if not value]
    
    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    logger.info("✅ All required environment variables found.")
    return True

def check_supabase_connection():
    """Check connection to Supabase."""
    if not HAS_SUPABASE:
        return False
    
    logger.info("Checking Supabase connection...")
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    try:
        start_time = time.time()
        client = create_client(supabase_url, supabase_key)
        
        # Test API with a simple query
        response = client.table("users").select("count").execute()
        
        duration = time.time() - start_time
        logger.info(f"✅ Successfully connected to Supabase (took {duration:.2f}s)")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {str(e)}")
        return False

def check_supabase_auth():
    """Check Supabase Auth functionality."""
    if not HAS_SUPABASE:
        return False
    
    logger.info("Checking Supabase Auth...")
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    try:
        client = create_client(supabase_url, supabase_key)
        
        # Get auth configuration
        response = client.auth.get_url()
        
        if response:
            logger.info("✅ Supabase Auth is working")
            return True
        else:
            logger.error("❌ Supabase Auth not properly configured")
            return False
    except Exception as e:
        logger.error(f"❌ Supabase Auth check failed: {str(e)}")
        return False

def check_supabase_storage():
    """Check Supabase Storage functionality."""
    if not HAS_SUPABASE:
        return False
    
    logger.info("Checking Supabase Storage...")
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    try:
        client = create_client(supabase_url, supabase_key)
        
        # List buckets
        response = client.storage.list_buckets()
        
        if response:
            bucket_count = len(response)
            if bucket_count > 0:
                logger.info(f"✅ Supabase Storage is working ({bucket_count} buckets found)")
            else:
                logger.warning("⚠️ Supabase Storage is working but no buckets found")
            return True
        else:
            logger.error("❌ Supabase Storage not properly configured")
            return False
    except Exception as e:
        logger.error(f"❌ Supabase Storage check failed: {str(e)}")
        return False

def check_postgis_extension():
    """Check if PostGIS extension is enabled."""
    if not HAS_SUPABASE:
        return False
    
    logger.info("Checking PostGIS extension...")
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    try:
        client = create_client(supabase_url, supabase_key)
        
        # Check if postgis extension is enabled
        response = client.rpc('check_extension', {'extension_name': 'postgis'}).execute()
        
        if response.data:
            logger.info("✅ PostGIS extension is enabled")
            return True
        else:
            logger.error("❌ PostGIS extension not enabled")
            return False
    except Exception as e:
        logger.error(f"❌ PostGIS check failed: {str(e)}")
        logger.info("ℹ️ You may need to enable PostGIS extension manually in Supabase SQL editor:")
        logger.info("    CREATE EXTENSION IF NOT EXISTS postgis;")
        return False

def setup_extension_check_function():
    """Create a function to check for extensions."""
    if not HAS_SUPABASE:
        return False
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    try:
        client = create_client(supabase_url, supabase_key)
        
        # Create function to check extensions
        sql = """
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
        
        client.rpc('as_root', {'sql': sql}).execute()
        logger.info("✅ Created extension check function")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create extension check function: {str(e)}")
        return False

def main():
    """Main function to run all checks."""
    if not HAS_SUPABASE:
        sys.exit(1)
    
    # Ensure Supabase environment variables are set for testing
    if "SUPABASE_URL" not in os.environ or not os.environ["SUPABASE_URL"]:
        logger.info("Setting SUPABASE_URL for testing...")
        os.environ["SUPABASE_URL"] = "https://romjfbwktyxljvgcthmk.supabase.co"
    
    logger.info("=== Supabase Connection Checker ===")
    logger.info(f"Using Supabase URL: {os.environ.get('SUPABASE_URL')}")
    
    checks = [
        check_environment_variables,
        check_supabase_connection,
        check_supabase_auth,
        check_supabase_storage,
        setup_extension_check_function,
        check_postgis_extension
    ]
    
    results = []
    for check in checks:
        result = check()
        results.append(result)
    
    # Print summary
    logger.info("\n=== Summary ===")
    success_count = sum(results)
    total_count = len(results)
    
    logger.info(f"Passed {success_count} out of {total_count} checks")
    
    if all(results):
        logger.info("✅ All checks passed! Your Supabase integration is ready.")
        return 0
    else:
        logger.warning("⚠️ Some checks failed. Review the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())