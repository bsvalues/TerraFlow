"""
Supabase Environment Verification

This script verifies that Supabase environment variables are set correctly
and that connections to Supabase services are working properly.
"""

import os
import sys
import logging
import json
from typing import Dict, Any, Optional, List, Tuple

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

def load_environment_variables() -> bool:
    """
    Load environment variables from .env file if available.
    
    Returns:
        True if successful, False otherwise
    """
    if DOTENV_AVAILABLE:
        try:
            dotenv.load_dotenv(".env")
            logger.debug("Loaded environment variables from .env")
            return True
        except Exception as e:
            logger.warning(f"Failed to load environment variables from .env: {str(e)}")
            return False
    else:
        logger.warning("dotenv package not installed, cannot load from .env file")
        return False

def check_environment_variables() -> Dict[str, Any]:
    """
    Check if required Supabase environment variables are set.
    
    Returns:
        Dictionary with check results
    """
    load_environment_variables()
    
    # Get active environment
    active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
    
    # Check for environment-specific variables
    env_url_var = f"SUPABASE_URL_{active_env.upper()}"
    env_key_var = f"SUPABASE_KEY_{active_env.upper()}"
    env_service_key_var = f"SUPABASE_SERVICE_KEY_{active_env.upper()}"
    
    env_url = os.environ.get(env_url_var)
    env_key = os.environ.get(env_key_var)
    env_service_key = os.environ.get(env_service_key_var)
    
    # Check for base variables
    base_url = os.environ.get("SUPABASE_URL")
    base_key = os.environ.get("SUPABASE_KEY")
    base_service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    # Use environment-specific variables if available, otherwise fall back to base variables
    url = env_url or base_url
    key = env_key or base_key
    service_key = env_service_key or base_service_key
    
    # Run checks
    checks = {
        "base_vars": {
            "url": bool(base_url),
            "key": bool(base_key),
            "service_key": bool(base_service_key)
        },
        "env_vars": {
            "url": bool(env_url),
            "key": bool(env_key),
            "service_key": bool(env_service_key)
        },
        "active_vars": {
            "url": bool(url),
            "key": bool(key),
            "service_key": bool(service_key)
        },
        "active_environment": active_env
    }
    
    # Overall success
    success = bool(url and key)
    
    return {
        "success": success,
        "message": "Environment variables are set correctly" if success else "Missing required environment variables",
        "details": checks
    }

def check_supabase_connection() -> Dict[str, Any]:
    """
    Check if we can establish a connection to Supabase.
    
    Returns:
        Dictionary with check results
    """
    if not SUPABASE_AVAILABLE:
        return {
            "success": False,
            "message": "Supabase package is not installed",
            "details": {"supabase_available": False}
        }
    
    # Get Supabase URL and key
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        return {
            "success": False,
            "message": "Supabase URL or key not set",
            "details": {"url_set": bool(url), "key_set": bool(key)}
        }
    
    try:
        # Try to create a client
        client = create_client(url, key)
        
        # Try to make a simple query
        response = client.table("_schema").select("*").limit(1).execute()
        
        return {
            "success": True,
            "message": "Successfully connected to Supabase",
            "details": {"connection": "success", "url": url}
        }
    except Exception as e:
        logger.warning(f"Failed to connect to Supabase: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to connect to Supabase: {str(e)}",
            "details": {"connection": "failed", "error": str(e), "url": url}
        }

def check_supabase_auth() -> Dict[str, Any]:
    """
    Check if Supabase Auth is working.
    
    Returns:
        Dictionary with check results
    """
    if not SUPABASE_AVAILABLE:
        return {
            "success": False,
            "message": "Supabase package is not installed",
            "details": {"supabase_available": False}
        }
    
    # Get Supabase URL and key
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        return {
            "success": False,
            "message": "Supabase URL or key not set",
            "details": {"url_set": bool(url), "key_set": bool(key)}
        }
    
    try:
        # Try to create a client
        client = create_client(url, key)
        
        # Check if auth API is available
        response = client.auth.get_user("fake-jwt-token")
        
        # This should actually fail with an error about invalid JWT,
        # but that means the auth API is working
        return {
            "success": True,
            "message": "Supabase Auth is working",
            "details": {"auth": "success"}
        }
    except Exception as e:
        error_str = str(e)
        
        # If we get an error about invalid JWT, that's actually good
        if "invalid jwt" in error_str.lower():
            return {
                "success": True,
                "message": "Supabase Auth is working",
                "details": {"auth": "success", "error": error_str}
            }
        
        logger.warning(f"Failed to check Supabase Auth: {error_str}")
        return {
            "success": False,
            "message": f"Failed to check Supabase Auth: {error_str}",
            "details": {"auth": "failed", "error": error_str}
        }

def check_supabase_storage() -> Dict[str, Any]:
    """
    Check if Supabase Storage is working.
    
    Returns:
        Dictionary with check results
    """
    if not SUPABASE_AVAILABLE:
        return {
            "success": False,
            "message": "Supabase package is not installed",
            "details": {"supabase_available": False}
        }
    
    # Get Supabase URL and key
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        return {
            "success": False,
            "message": "Supabase URL or key not set",
            "details": {"url_set": bool(url), "key_set": bool(key)}
        }
    
    try:
        # Try to create a client
        client = create_client(url, key)
        
        # List buckets to check if storage is working
        response = client.storage.list_buckets()
        
        return {
            "success": True,
            "message": "Supabase Storage is working",
            "details": {"storage": "success", "buckets": len(response)}
        }
    except Exception as e:
        logger.warning(f"Failed to check Supabase Storage: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to check Supabase Storage: {str(e)}",
            "details": {"storage": "failed", "error": str(e)}
        }

def check_postgis_extension() -> Dict[str, Any]:
    """
    Check if the PostGIS extension is enabled in the Supabase database.
    
    Returns:
        Dictionary with check results
    """
    if not SUPABASE_AVAILABLE:
        return {
            "success": False,
            "message": "Supabase package is not installed",
            "details": {"supabase_available": False}
        }
    
    # Get Supabase URL and key
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        return {
            "success": False,
            "message": "Supabase URL or key not set",
            "details": {"url_set": bool(url), "key_set": bool(key)}
        }
    
    try:
        # Try to create a client
        client = create_client(url, key)
        
        # Query pg_extension to check if PostGIS is installed
        response = client.table("pg_extension").select("*").eq("extname", "postgis").execute()
        
        # Check if PostGIS was found
        if len(response.data) > 0:
            # Try to run a simple PostGIS query to make sure it's working
            test_query = """
            SELECT 'POINT(0 0)'::geometry;
            """
            
            result = client.rpc("test_postgis_query", {"query": test_query}).execute()
            
            return {
                "success": True,
                "message": "PostGIS extension is enabled and working",
                "details": {"postgis": "enabled", "version": response.data[0].get("extversion")}
            }
        else:
            return {
                "success": False,
                "message": "PostGIS extension is not enabled",
                "details": {"postgis": "not_enabled"}
            }
    except Exception as e:
        logger.warning(f"Failed to check PostGIS extension: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to check PostGIS extension: {str(e)}",
            "details": {"postgis": "failed", "error": str(e)}
        }

def test_migration_readiness() -> Dict[str, Any]:
    """
    Test if the database is ready for migration.
    
    Returns:
        Dictionary with check results
    """
    if not SUPABASE_AVAILABLE:
        return {
            "success": False,
            "message": "Supabase package is not installed",
            "details": {"supabase_available": False}
        }
    
    # Get Supabase URL and key
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        return {
            "success": False,
            "message": "Supabase URL or key not set",
            "details": {"url_set": bool(url), "key_set": bool(key)}
        }
    
    try:
        # Try to create a client
        client = create_client(url, key)
        
        # Check if we have the service key
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        # Check if we have write access
        try:
            # First, check if the schema exists
            schema_check = client.rpc("schema_exists", {"schema_name": "property"}).execute()
            schema_exists = schema_check.data if schema_check.data is not None else False
            
            if not schema_exists:
                # Try to create a test schema
                client.rpc("create_schema", {"schema_name": "property"}).execute()
            
            # Try to create a test table
            test_table_query = """
            CREATE TABLE IF NOT EXISTS property.test_migration (
                id SERIAL PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
            client.rpc("run_sql", {"query": test_table_query}).execute()
            
            # Drop the test table
            client.rpc("run_sql", {"query": "DROP TABLE property.test_migration;"}).execute()
            
            return {
                "success": True,
                "message": "Database is ready for migration",
                "details": {
                    "write_access": True,
                    "service_key_available": bool(service_key),
                    "schema_exists": bool(schema_exists)
                }
            }
        except Exception as e:
            error_str = str(e)
            
            if "permission denied" in error_str.lower():
                return {
                    "success": False,
                    "message": "Insufficient permissions for migration",
                    "details": {
                        "write_access": False,
                        "service_key_available": bool(service_key),
                        "error": error_str
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Error testing migration readiness: {error_str}",
                    "details": {
                        "write_access": False,
                        "service_key_available": bool(service_key),
                        "error": error_str
                    }
                }
    except Exception as e:
        logger.warning(f"Failed to test migration readiness: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to test migration readiness: {str(e)}",
            "details": {"error": str(e)}
        }

def run_all_checks() -> Dict[str, Any]:
    """
    Run all Supabase environment checks.
    
    Returns:
        Dictionary with all check results
    """
    results = {
        "environment_variables": check_environment_variables(),
        "connection": check_supabase_connection(),
        "auth": check_supabase_auth(),
        "storage": check_supabase_storage(),
        "postgis": check_postgis_extension(),
        "migration_readiness": test_migration_readiness()
    }
    
    # Overall success
    success = all(check["success"] for check in results.values())
    
    return {
        "success": success,
        "message": "All checks passed" if success else "Some checks failed",
        "details": results
    }

def main():
    """Main entry point for script."""
    # Load environment variables
    load_environment_variables()
    
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify Supabase environment")
    parser.add_argument("--check", choices=["all", "env", "connection", "auth", "storage", "postgis", "migration"], default="all", help="Check to run")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    
    args = parser.parse_args()
    
    # Run checks
    if args.check == "all":
        results = run_all_checks()
    elif args.check == "env":
        results = check_environment_variables()
    elif args.check == "connection":
        results = check_supabase_connection()
    elif args.check == "auth":
        results = check_supabase_auth()
    elif args.check == "storage":
        results = check_supabase_storage()
    elif args.check == "postgis":
        results = check_postgis_extension()
    elif args.check == "migration":
        results = test_migration_readiness()
    
    # Print results
    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(f"Check: {args.check}")
        print(f"Success: {results['success']}")
        print(f"Message: {results['message']}")
        
        if "details" in results:
            print("\nDetails:")
            for key, value in results["details"].items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"    {sub_key}: {sub_value}")
                else:
                    print(f"  {key}: {value}")

if __name__ == "__main__":
    main()