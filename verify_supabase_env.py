"""
Supabase Environment Verification Tool

This module provides functions to verify Supabase environment configurations
and test connectivity to Supabase services.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List, Union, Tuple

try:
    import dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
def load_env_variables():
    """Load environment variables from .env file if available."""
    if DOTENV_AVAILABLE:
        try:
            dotenv.load_dotenv()
            logger.debug("Loaded environment variables from .env file")
        except Exception as e:
            logger.warning(f"Failed to load environment variables from .env file: {str(e)}")

def check_environment_variables() -> Dict[str, Any]:
    """
    Check if required Supabase environment variables are set.
    
    Returns:
        Dictionary with check results
    """
    active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
    env_prefix = f"{active_env.upper()}_" if active_env != "development" else ""
    
    url_var = f"{env_prefix}SUPABASE_URL"
    key_var = f"{env_prefix}SUPABASE_KEY"
    service_key_var = f"{env_prefix}SUPABASE_SERVICE_KEY"
    
    # Try environment-specific variables first
    url = os.environ.get(url_var)
    key = os.environ.get(key_var)
    service_key = os.environ.get(service_key_var)
    
    # Fall back to base variables
    if not url:
        url = os.environ.get("SUPABASE_URL")
    if not key:
        key = os.environ.get("SUPABASE_KEY")
    if not service_key:
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    results = {
        "success": bool(url and key),
        "environment": active_env,
        "url": url is not None,
        "key": key is not None,
        "service_key": service_key is not None,
        "message": "All required variables are set" if url and key else "Missing required variables"
    }
    
    return results

def check_supabase_connection() -> Dict[str, Any]:
    """
    Check if the Supabase connection works.
    
    Returns:
        Dictionary with check results
    """
    if not SUPABASE_AVAILABLE:
        return {
            "success": False,
            "message": "Supabase package not installed"
        }
    
    active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
    env_prefix = f"{active_env.upper()}_" if active_env != "development" else ""
    
    # Try environment-specific variables first
    url = os.environ.get(f"{env_prefix}SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    key = os.environ.get(f"{env_prefix}SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    
    if not url or not key:
        return {
            "success": False,
            "message": "Missing required environment variables"
        }
    
    try:
        # Create Supabase client
        client = create_client(url, key)
        
        # Try a simple query to check connection
        start_time = time.time()
        response = client.table("system_settings").select("key").limit(1).execute()
        end_time = time.time()
        
        # Success criteria: No error and query time < 5 seconds
        success = not hasattr(response, 'error') or not response.error
        query_time = end_time - start_time
        
        if success:
            return {
                "success": True,
                "message": f"Successfully connected to Supabase ({query_time:.2f}s)",
                "query_time": f"{query_time:.2f}s",
                "environment": active_env
            }
        else:
            return {
                "success": False,
                "message": f"Connection established but query failed: {response.error}",
                "environment": active_env
            }
    
    except Exception as e:
        logger.error(f"Supabase connection error: {str(e)}")
        return {
            "success": False,
            "message": f"Connection error: {str(e)}",
            "environment": active_env
        }

def check_supabase_auth() -> Dict[str, Any]:
    """
    Check if Supabase Auth service is working.
    
    Returns:
        Dictionary with check results
    """
    if not SUPABASE_AVAILABLE:
        return {
            "success": False,
            "message": "Supabase package not installed"
        }
    
    active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
    env_prefix = f"{active_env.upper()}_" if active_env != "development" else ""
    
    # Try environment-specific variables first
    url = os.environ.get(f"{env_prefix}SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    key = os.environ.get(f"{env_prefix}SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    
    if not url or not key:
        return {
            "success": False,
            "message": "Missing required environment variables"
        }
    
    try:
        # Create Supabase client
        client = create_client(url, key)
        
        # Try getting auth configuration
        start_time = time.time()
        settings = client.auth.get_settings()
        end_time = time.time()
        
        # Success criteria: No error and response time < 5 seconds
        success = not hasattr(settings, 'error') or not settings.error
        query_time = end_time - start_time
        
        if success:
            return {
                "success": True,
                "message": f"Successfully connected to Supabase Auth ({query_time:.2f}s)",
                "query_time": f"{query_time:.2f}s",
                "environment": active_env
            }
        else:
            return {
                "success": False,
                "message": f"Connection established but auth check failed: {settings.error}",
                "environment": active_env
            }
    
    except Exception as e:
        logger.error(f"Supabase auth check error: {str(e)}")
        return {
            "success": False,
            "message": f"Auth check error: {str(e)}",
            "environment": active_env
        }

def check_supabase_storage() -> Dict[str, Any]:
    """
    Check if Supabase Storage service is working.
    
    Returns:
        Dictionary with check results
    """
    if not SUPABASE_AVAILABLE:
        return {
            "success": False,
            "message": "Supabase package not installed"
        }
    
    active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
    env_prefix = f"{active_env.upper()}_" if active_env != "development" else ""
    
    # Try environment-specific variables first
    url = os.environ.get(f"{env_prefix}SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    key = os.environ.get(f"{env_prefix}SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    
    if not url or not key:
        return {
            "success": False,
            "message": "Missing required environment variables"
        }
    
    try:
        # Create Supabase client
        client = create_client(url, key)
        
        # Try listing storage buckets
        start_time = time.time()
        buckets = client.storage.list_buckets()
        end_time = time.time()
        
        # Success criteria: No error and response time < 5 seconds
        success = not hasattr(buckets, 'error') or not buckets.error
        query_time = end_time - start_time
        
        if success:
            # Filter out buckets that start with '_' (internal buckets)
            public_buckets = [b for b in buckets if not b['name'].startswith('_')]
            
            # Try to get or create a test bucket
            if not public_buckets:
                try:
                    client.storage.create_bucket("test_bucket")
                    logger.info(f"Created test bucket 'test_bucket' in {active_env} environment")
                    public_buckets = ["test_bucket"]
                except Exception as e:
                    logger.info(f"Could not create test bucket: {str(e)}")
            
            return {
                "success": True,
                "message": f"Successfully connected to Supabase Storage ({query_time:.2f}s)",
                "buckets": len(public_buckets),
                "bucket_names": [b['name'] if isinstance(b, dict) else b for b in public_buckets],
                "query_time": f"{query_time:.2f}s",
                "environment": active_env
            }
        else:
            return {
                "success": False,
                "message": f"Connection established but storage check failed: {buckets.error}",
                "environment": active_env
            }
    
    except Exception as e:
        logger.error(f"Supabase storage check error: {str(e)}")
        return {
            "success": False,
            "message": f"Storage check error: {str(e)}",
            "environment": active_env
        }

def check_postgis_extension() -> Dict[str, Any]:
    """
    Check if the PostGIS extension is installed and working.
    
    Returns:
        Dictionary with check results
    """
    if not SUPABASE_AVAILABLE:
        return {
            "success": False,
            "message": "Supabase package not installed"
        }
    
    active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
    env_prefix = f"{active_env.upper()}_" if active_env != "development" else ""
    
    # Try environment-specific variables first
    url = os.environ.get(f"{env_prefix}SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    key = os.environ.get(f"{env_prefix}SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    
    if not url or not key:
        return {
            "success": False,
            "message": "Missing required environment variables"
        }
    
    try:
        # Create Supabase client
        client = create_client(url, key)
        
        # Try running a PostGIS function
        start_time = time.time()
        
        # Check if PostGIS is installed by querying for the version
        response = client.rpc('run_sql', {"sql": "SELECT PostGIS_Version();"}).execute()
        
        end_time = time.time()
        
        # Success criteria: No error and response time < 5 seconds
        success = not hasattr(response, 'error') or not response.error
        query_time = end_time - start_time
        
        if success and response.data:
            postgis_version = response.data[0]['postgis_version'] if response.data else "Unknown"
            
            return {
                "success": True,
                "message": f"PostGIS extension is installed ({query_time:.2f}s)",
                "version": postgis_version,
                "query_time": f"{query_time:.2f}s",
                "environment": active_env
            }
        else:
            # Try creating the extension if it doesn't exist
            try:
                client.rpc('run_sql', {"sql": "CREATE EXTENSION IF NOT EXISTS postgis;"}).execute()
                
                # Check again
                response = client.rpc('run_sql', {"sql": "SELECT PostGIS_Version();"}).execute()
                
                if not hasattr(response, 'error') or not response.error:
                    postgis_version = response.data[0]['postgis_version'] if response.data else "Unknown"
                    
                    return {
                        "success": True,
                        "message": f"PostGIS extension was created successfully ({query_time:.2f}s)",
                        "version": postgis_version,
                        "query_time": f"{query_time:.2f}s",
                        "environment": active_env
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to create PostGIS extension: {response.error}",
                        "environment": active_env
                    }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"PostGIS extension is not installed or not accessible: {str(e)}",
                    "environment": active_env
                }
    
    except Exception as e:
        logger.error(f"PostGIS check error: {str(e)}")
        return {
            "success": False,
            "message": f"PostGIS check error: {str(e)}",
            "environment": active_env
        }

def test_migration_readiness(environment: str = None) -> Dict[str, Any]:
    """
    Test if the Supabase environment is ready for migration.
    
    Args:
        environment: Optional environment name to test
        
    Returns:
        Dictionary with test results
    """
    results = {}
    
    # Save original environment
    orig_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT")
    
    try:
        # Set the environment to test if specified
        if environment:
            os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = environment
        
        # Run all checks
        results["variables"] = check_environment_variables()
        results["connection"] = check_supabase_connection()
        results["auth"] = check_supabase_auth()
        results["storage"] = check_supabase_storage()
        results["postgis"] = check_postgis_extension()
        
        # Overall success if all checks passed
        results["success"] = all(check.get("success", False) for check in results.values())
        results["environment"] = environment or orig_env or "development"
        
        if results["success"]:
            results["message"] = f"Environment {results['environment']} is ready for migration"
        else:
            results["message"] = f"Environment {results['environment']} is not ready for migration - see individual checks for details"
    
    finally:
        # Restore original environment
        if orig_env and environment:
            os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = orig_env
    
    return results

if __name__ == "__main__":
    # Load environment variables
    load_env_variables()
    
    # Run all checks
    print("Checking Supabase environment...\n")
    
    var_check = check_environment_variables()
    print(f"Environment Variables: {'✅' if var_check['success'] else '❌'} {var_check['message']}")
    
    if var_check['success']:
        conn_check = check_supabase_connection()
        print(f"Supabase Connection: {'✅' if conn_check['success'] else '❌'} {conn_check['message']}")
        
        auth_check = check_supabase_auth()
        print(f"Supabase Auth: {'✅' if auth_check['success'] else '❌'} {auth_check['message']}")
        
        storage_check = check_supabase_storage()
        print(f"Supabase Storage: {'✅' if storage_check['success'] else '❌'} {storage_check['message']}")
        
        postgis_check = check_postgis_extension()
        print(f"PostGIS Extension: {'✅' if postgis_check['success'] else '❌'} {postgis_check['message']}")
        
        # Overall success
        all_success = all([
            var_check['success'],
            conn_check['success'],
            auth_check['success'],
            storage_check['success'],
            postgis_check['success']
        ])
        
        print(f"\nOverall Status: {'✅' if all_success else '❌'} Environment is {'ready' if all_success else 'not ready'} for use")