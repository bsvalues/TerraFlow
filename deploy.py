#!/usr/bin/env python
"""
Deployment Script for GeoAssessmentPro

This script automates the deployment process for different environments
(development, training, production).
"""

import os
import sys
import subprocess
import logging
import argparse
import time
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
VALID_ENVIRONMENTS = ["development", "training", "production"]
MIGRATION_SCRIPTS = [
    "migrate_database.py",
    "migrate_data_quality.py",
    "migrate_report_schema.py"
]

def run_command(command: List[str], 
                check: bool = True, 
                shell: bool = False) -> Tuple[int, str, str]:
    """
    Run a command and return the exit code, stdout, and stderr.
    
    Args:
        command: Command to run (list of strings)
        check: Whether to check for non-zero exit code
        shell: Whether to run the command in a shell
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    logger.info(f"Running command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command if not shell else ' '.join(command),
            check=check,
            shell=shell,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return e.returncode, e.stdout, e.stderr

def switch_environment(environment: str) -> bool:
    """
    Switch to the specified environment.
    
    Args:
        environment: The environment to switch to (development, training, production)
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Switching to {environment} environment")
    
    # Set the environment in the system environment
    os.environ["ENV_MODE"] = environment
    
    # Also use the switch_environment.py script if available
    if os.path.exists("switch_environment.py"):
        exit_code, stdout, stderr = run_command(
            ["python", "switch_environment.py", environment], 
            check=False
        )
        if exit_code != 0:
            logger.error(f"Failed to switch to {environment} environment")
            logger.error(f"STDERR: {stderr}")
            return False
            
    logger.info(f"Successfully switched to {environment} environment")
    return True

def run_database_migrations() -> bool:
    """
    Run all database migrations.
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Running database migrations")
    
    for migration_script in MIGRATION_SCRIPTS:
        if os.path.exists(migration_script):
            logger.info(f"Running migration script: {migration_script}")
            exit_code, stdout, stderr = run_command(
                ["python", migration_script], 
                check=False
            )
            if exit_code != 0:
                logger.error(f"Migration script {migration_script} failed")
                logger.error(f"STDERR: {stderr}")
                return False
    
    logger.info("Database migrations completed successfully")
    return True

def restart_application(wait_seconds: int = 5) -> bool:
    """
    Restart the application.
    
    Args:
        wait_seconds: Number of seconds to wait after stopping the application
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Restarting application")
    
    # Use Gunicorn to restart the application
    exit_code, stdout, stderr = run_command(
        ["pkill", "-f", "gunicorn"],
        check=False
    )
    
    # Wait for the application to stop
    logger.info(f"Waiting {wait_seconds} seconds for application to stop")
    time.sleep(wait_seconds)
    
    # Start the application
    logger.info("Starting application")
    exit_code, stdout, stderr = run_command(
        ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"],
        check=False,
        shell=True
    )
    
    if exit_code != 0:
        logger.error("Failed to start application")
        logger.error(f"STDERR: {stderr}")
        return False
    
    logger.info("Application restarted successfully")
    return True

def verify_deployment() -> bool:
    """
    Verify the deployment.
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Verifying deployment")
    
    # Wait for the application to start
    logger.info("Waiting 5 seconds for application to start")
    time.sleep(5)
    
    # Check if the application is running
    logger.info("Checking if application is running")
    exit_code, stdout, stderr = run_command(
        ["curl", "-s", "http://localhost:5000/"],
        check=False
    )
    
    if exit_code != 0:
        logger.error("Application is not running")
        logger.error(f"STDERR: {stderr}")
        return False
    
    logger.info("Application is running")
    return True

def deploy(environment: str, skip_migrations: bool = False, 
           skip_restart: bool = False, skip_verify: bool = False) -> bool:
    """
    Deploy the application to the specified environment.
    
    Args:
        environment: The environment to deploy to (development, training, production)
        skip_migrations: Whether to skip database migrations
        skip_restart: Whether to skip restarting the application
        skip_verify: Whether to skip verifying the deployment
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Deploying to {environment} environment")
    
    # Switch to the specified environment
    if not switch_environment(environment):
        return False
    
    # Run database migrations if not skipped
    if not skip_migrations:
        if not run_database_migrations():
            return False
    
    # Restart the application if not skipped
    if not skip_restart:
        if not restart_application():
            return False
    
    # Verify the deployment if not skipped
    if not skip_verify:
        if not verify_deployment():
            return False
    
    logger.info(f"Successfully deployed to {environment} environment")
    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Deploy GeoAssessmentPro")
    parser.add_argument("environment", choices=VALID_ENVIRONMENTS,
                       help="The environment to deploy to (development, training, production)")
    parser.add_argument("--skip-migrations", action="store_true",
                       help="Skip database migrations")
    parser.add_argument("--skip-restart", action="store_true",
                       help="Skip restarting the application")
    parser.add_argument("--skip-verify", action="store_true",
                       help="Skip verifying the deployment")
    
    args = parser.parse_args()
    
    result = deploy(
        args.environment,
        skip_migrations=args.skip_migrations,
        skip_restart=args.skip_restart,
        skip_verify=args.skip_verify
    )
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())