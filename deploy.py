#!/usr/bin/env python
"""
Deployment Script for GeoAssessmentPro

This script automates the deployment process for different environments
(development, training, production).
"""

import os
import sys
import logging
import argparse
import time
import subprocess
import datetime
import requests
from typing import Dict, Any, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
VALID_ENVIRONMENTS = ["development", "training", "production"]
APP_PORT = 5000
APP_HOST = "0.0.0.0"
MAX_RESTART_ATTEMPTS = 3
RESTART_WAIT_TIME = 5  # seconds
VERIFY_TIMEOUT = 30    # seconds

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
    logger.info(f"Running command: {' '.join(command) if not shell else command}")
    try:
        if shell:
            result = subprocess.run(command, check=check, shell=shell, 
                                  capture_output=True, text=True)
        else:
            result = subprocess.run(command, check=check, 
                                  capture_output=True, text=True)
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
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        logger.error(f"Valid environments are: {', '.join(VALID_ENVIRONMENTS)}")
        return False
    
    # Check if the switch_environment.py script exists
    if not os.path.exists("switch_environment.py"):
        logger.error("switch_environment.py script not found")
        return False
    
    # Run the switch_environment.py script
    logger.info(f"Switching to {environment} environment")
    exit_code, stdout, stderr = run_command(["python", "switch_environment.py", environment])
    
    if exit_code != 0:
        logger.error(f"Failed to switch to {environment} environment")
        return False
    
    logger.info(f"Successfully switched to {environment} environment")
    return True

def run_database_migrations() -> bool:
    """
    Run all database migrations.
    
    Returns:
        True if successful, False otherwise
    """
    # Run the migrate_database.py script
    logger.info("Running database migrations")
    exit_code, stdout, stderr = run_command(["python", "migrate_database.py"])
    
    if exit_code != 0:
        logger.error("Failed to run database migrations")
        return False
    
    # Run the migrate_data_quality.py script if it exists
    if os.path.exists("migrate_data_quality.py"):
        logger.info("Running data quality migrations")
        exit_code, stdout, stderr = run_command(["python", "migrate_data_quality.py"])
        
        if exit_code != 0:
            logger.error("Failed to run data quality migrations")
            return False
    
    # Run the migrate_report_schema.py script if it exists
    if os.path.exists("migrate_report_schema.py"):
        logger.info("Running report schema migrations")
        exit_code, stdout, stderr = run_command(["python", "migrate_report_schema.py"])
        
        if exit_code != 0:
            logger.error("Failed to run report schema migrations")
            return False
    
    logger.info("All database migrations completed successfully")
    return True

def restart_application(wait_seconds: int = 5) -> bool:
    """
    Restart the application.
    
    Args:
        wait_seconds: Number of seconds to wait after stopping the application
        
    Returns:
        True if successful, False otherwise
    """
    # For now, we'll assume that the application is managed by an external system.
    # In a production environment, this would be done through systemd, supervisord, etc.
    # Since we're using Replit's workflows, this function is mostly a placeholder.
    
    logger.info("Application restart requested")
    
    # In a real-world scenario, you might call a restart endpoint, 
    # use system commands, or touch a file to trigger a reload
    
    # Simulate waiting for the application to restart
    logger.info(f"Waiting {wait_seconds} seconds for the application to restart")
    time.sleep(wait_seconds)
    
    logger.info("Application restart requested successfully")
    return True

def verify_deployment() -> bool:
    """
    Verify the deployment.
    
    Returns:
        True if successful, False otherwise
    """
    # In a real deployment, you would check endpoints or run tests
    # to verify that the deployment was successful.
    
    logger.info("Verifying deployment")
    
    # Try to access the application's health check endpoint
    try:
        # Use a timeout to prevent hanging if the application is not running
        response = requests.get(f"http://{APP_HOST}:{APP_PORT}/health", 
                             timeout=VERIFY_TIMEOUT)
        
        if response.status_code == 200:
            logger.info("Deployment verification successful")
            return True
        else:
            logger.error(f"Deployment verification failed with status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Deployment verification failed: {str(e)}")
        return False

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
    if environment not in VALID_ENVIRONMENTS:
        logger.error(f"Invalid environment: {environment}")
        logger.error(f"Valid environments are: {', '.join(VALID_ENVIRONMENTS)}")
        return False
    
    logger.info(f"Starting deployment to {environment} environment")
    
    # Switch to the specified environment
    if not switch_environment(environment):
        return False
    
    # Run database migrations
    if not skip_migrations:
        if not run_database_migrations():
            return False
    else:
        logger.info("Skipping database migrations")
    
    # Restart the application
    if not skip_restart:
        if not restart_application(RESTART_WAIT_TIME):
            return False
    else:
        logger.info("Skipping application restart")
    
    # Verify the deployment
    if not skip_verify:
        if not verify_deployment():
            return False
    else:
        logger.info("Skipping deployment verification")
    
    logger.info(f"Deployment to {environment} environment completed successfully")
    
    # Log deployment timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # In a production system, you would log this to a deployment history table or file
    logger.info(f"Deployment timestamp: {timestamp}")
    
    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Deploy the application to a specific environment")
    parser.add_argument("environment", choices=VALID_ENVIRONMENTS,
                      help="The environment to deploy to")
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