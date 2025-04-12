#!/usr/bin/env python3
"""
Script to verify Supabase environment variables.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("verify_supabase_env")

def check_env_vars():
    """
    Check if required Supabase environment variables are set.
    
    Returns:
        dict: Dictionary with status of each environment variable
    """
    required_vars = {
        "SUPABASE_URL": "The URL of your Supabase project",
        "SUPABASE_KEY": "The public anon key for client-side auth",
        "SUPABASE_SERVICE_KEY": "The service role key for admin operations"
    }
    
    results = {}
    all_present = True
    
    logger.info("Checking Supabase environment variables...")
    
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            # Only show first 10 chars for security
            masked_value = value[:5] + "*" * (len(value) - 8) + value[-3:] if len(value) > 10 else "********"
            results[var] = {
                "present": True,
                "value_sample": masked_value
            }
            logger.info(f"✅ {var} is set")
        else:
            results[var] = {
                "present": False
            }
            all_present = False
            logger.error(f"❌ {var} is not set - {description}")
    
    return {
        "all_present": all_present,
        "details": results
    }

def suggest_next_steps(status):
    """
    Suggest next steps based on environment variable status.
    
    Args:
        status (dict): Status of environment variables
    """
    if status["all_present"]:
        logger.info("All required Supabase environment variables are set.")
        logger.info("Next steps:")
        logger.info("1. Run 'python test_supabase_connection.py' to test the connection")
        logger.info("2. Follow SQL setup instructions in docs/supabase_sql_scripts.md")
        logger.info("3. Verify storage buckets exist in the Supabase Dashboard")
    else:
        logger.info("Please set the missing environment variables to enable Supabase integration.")
        logger.info("You can set them by running:")
        logger.info("python set_supabase_env.py")
        logger.info("\nOr set them manually:")
        
        for var, details in status["details"].items():
            if not details["present"]:
                if var == "SUPABASE_URL":
                    logger.info(f"export {var}=https://your-project-id.supabase.co")
                elif var == "SUPABASE_KEY":
                    logger.info(f"export {var}=your-anon-key")
                elif var == "SUPABASE_SERVICE_KEY":
                    logger.info(f"export {var}=your-service-role-key")

def main():
    """Main function"""
    logger.info("=== Supabase Environment Verification ===")
    
    status = check_env_vars()
    
    logger.info("\n=== Summary ===")
    if status["all_present"]:
        logger.info("✅ All required Supabase environment variables are set")
    else:
        logger.warning("⚠️ Some required Supabase environment variables are missing")
    
    logger.info("\n=== Next Steps ===")
    suggest_next_steps(status)
    
    return 0 if status["all_present"] else 1

if __name__ == "__main__":
    sys.exit(main())