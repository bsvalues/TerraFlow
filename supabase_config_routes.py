"""
Supabase Configuration Routes

This module provides Flask routes for managing Supabase environments
and configuration through a web interface.
"""

import os
import logging
from typing import Dict, Any, Optional, List

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

from config_loader import get_config
from auth import login_required, permission_required

# Import environment managers
try:
    from supabase_env_manager import (
        get_all_environments,
        get_current_environment,
        get_environment_url,
        get_environment_key,
        set_current_environment
    )
    ENV_MANAGER_AVAILABLE = True
except ImportError:
    ENV_MANAGER_AVAILABLE = False

# Import verification tools
try:
    from verify_supabase_env import (
        check_environment_variables,
        check_supabase_connection,
        check_supabase_auth,
        check_supabase_storage,
        check_postgis_extension
    )
    VERIFY_TOOLS_AVAILABLE = True
except ImportError:
    VERIFY_TOOLS_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint
supabase_config = Blueprint("supabase_config", __name__)

@supabase_config.route("/supabase/environments", methods=["GET"])
@login_required
@permission_required("admin")
def environments_page():
    """
    Display Supabase environments configuration page.
    """
    # Get all environment information
    environments = {}
    active_env = "development"
    
    if ENV_MANAGER_AVAILABLE:
        environments = get_all_environments()
        active_env = get_current_environment()
    else:
        # Fallback to environment variables
        for env in ["development", "training", "production"]:
            url = os.environ.get(f"SUPABASE_URL_{env.upper()}")
            key = os.environ.get(f"SUPABASE_KEY_{env.upper()}")
            service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{env.upper()}")
            
            environments[env] = {
                "configured": bool(url and key),
                "url": url,
                "key": key[:5] + "..." + key[-5:] if key else None,
                "service_key": bool(service_key)
            }
        
        active_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development")
    
    return render_template(
        "supabase/environments.html",
        environments=environments,
        active_env=active_env,
        env_manager_available=ENV_MANAGER_AVAILABLE,
        verify_tools_available=VERIFY_TOOLS_AVAILABLE
    )

@supabase_config.route("/supabase/environments/set", methods=["POST"])
@login_required
@permission_required("admin")
def set_environment():
    """
    Set the active Supabase environment.
    """
    environment = request.form.get("environment")
    if not environment or environment not in ["development", "training", "production"]:
        flash("Invalid environment specified", "error")
        return redirect(url_for("supabase_config.environments_page"))
    
    if ENV_MANAGER_AVAILABLE:
        success = set_current_environment(environment)
        if success:
            flash(f"Active environment changed to {environment}", "success")
        else:
            flash(f"Failed to change active environment to {environment}", "error")
    else:
        try:
            # Get environment-specific variables
            url = os.environ.get(f"SUPABASE_URL_{environment.upper()}")
            key = os.environ.get(f"SUPABASE_KEY_{environment.upper()}")
            service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{environment.upper()}")
            
            if not url or not key:
                flash(f"Environment {environment} is not configured", "error")
                return redirect(url_for("supabase_config.environments_page"))
            
            # Update the base variables
            os.environ["SUPABASE_URL"] = url
            os.environ["SUPABASE_KEY"] = key
            if service_key:
                os.environ["SUPABASE_SERVICE_KEY"] = service_key
            elif "SUPABASE_SERVICE_KEY" in os.environ:
                del os.environ["SUPABASE_SERVICE_KEY"]
            
            # Set the active environment
            os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = environment
            
            flash(f"Active environment changed to {environment}", "success")
        except Exception as e:
            logger.error(f"Error setting environment: {str(e)}")
            flash(f"Error setting environment: {str(e)}", "error")
    
    return redirect(url_for("supabase_config.environments_page"))

@supabase_config.route("/supabase/environments/configure", methods=["POST"])
@login_required
@permission_required("admin")
def configure_environment():
    """
    Configure a Supabase environment with URL and keys.
    """
    environment = request.form.get("environment")
    url = request.form.get("url")
    key = request.form.get("key")
    service_key = request.form.get("service_key")
    
    if not environment or environment not in ["development", "training", "production"]:
        flash("Invalid environment specified", "error")
        return redirect(url_for("supabase_config.environments_page"))
    
    if not url or not key:
        flash("URL and API key are required", "error")
        return redirect(url_for("supabase_config.environments_page"))
    
    try:
        # Set environment-specific variables
        os.environ[f"SUPABASE_URL_{environment.upper()}"] = url
        os.environ[f"SUPABASE_KEY_{environment.upper()}"] = key
        if service_key:
            os.environ[f"SUPABASE_SERVICE_KEY_{environment.upper()}"] = service_key
        elif f"SUPABASE_SERVICE_KEY_{environment.upper()}" in os.environ:
            del os.environ[f"SUPABASE_SERVICE_KEY_{environment.upper()}"]
        
        # If this is the active environment, also update the base variables
        if environment == os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT", "development"):
            os.environ["SUPABASE_URL"] = url
            os.environ["SUPABASE_KEY"] = key
            if service_key:
                os.environ["SUPABASE_SERVICE_KEY"] = service_key
            elif "SUPABASE_SERVICE_KEY" in os.environ:
                del os.environ["SUPABASE_SERVICE_KEY"]
        
        flash(f"Environment {environment} configured successfully", "success")
        
        # Try to save to .env file if we have the env manager
        if ENV_MANAGER_AVAILABLE:
            try:
                from set_supabase_env import set_env_vars
                if set_env_vars(environment, url, key, service_key):
                    flash("Environment variables saved to .env file", "success")
                else:
                    flash("Failed to save environment variables to .env file", "warning")
            except ImportError:
                flash("set_supabase_env module not available for saving to .env file", "warning")
        
    except Exception as e:
        logger.error(f"Error configuring environment: {str(e)}")
        flash(f"Error configuring environment: {str(e)}", "error")
    
    return redirect(url_for("supabase_config.environments_page"))

@supabase_config.route("/supabase/environments/verify", methods=["POST"])
@login_required
@permission_required("admin")
def verify_environment():
    """
    Verify a Supabase environment's connection and functionality.
    """
    environment = request.form.get("environment")
    verify_type = request.form.get("verify_type", "connection")
    
    if not environment or environment not in ["development", "training", "production"]:
        flash("Invalid environment specified", "error")
        return redirect(url_for("supabase_config.environments_page"))
    
    results = {}
    
    if not VERIFY_TOOLS_AVAILABLE:
        flash("Verification tools are not available", "error")
        return redirect(url_for("supabase_config.environments_page"))
    
    try:
        # Set the active environment for the duration of the verification
        orig_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT")
        
        # Get environment-specific variables
        url = os.environ.get(f"SUPABASE_URL_{environment.upper()}")
        key = os.environ.get(f"SUPABASE_KEY_{environment.upper()}")
        service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{environment.upper()}")
        
        # Temporarily set the environment for testing
        os.environ["SUPABASE_URL"] = url
        os.environ["SUPABASE_KEY"] = key
        if service_key:
            os.environ["SUPABASE_SERVICE_KEY"] = service_key
        elif "SUPABASE_SERVICE_KEY" in os.environ:
            del os.environ["SUPABASE_SERVICE_KEY"]
        os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = environment
        
        try:
            if verify_type == "variables":
                results = check_environment_variables()
            elif verify_type == "connection":
                results = check_supabase_connection()
            elif verify_type == "auth":
                results = check_supabase_auth()
            elif verify_type == "storage":
                results = check_supabase_storage()
            elif verify_type == "postgis":
                results = check_postgis_extension()
            elif verify_type == "all":
                results = {
                    "variables": check_environment_variables(),
                    "connection": check_supabase_connection(),
                    "auth": check_supabase_auth(),
                    "storage": check_supabase_storage(),
                    "postgis": check_postgis_extension()
                }
            else:
                flash(f"Invalid verification type: {verify_type}", "error")
        finally:
            # Restore original environment
            if orig_env:
                os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = orig_env
                
                # Restore original base variables
                orig_url = os.environ.get(f"SUPABASE_URL_{orig_env.upper()}")
                orig_key = os.environ.get(f"SUPABASE_KEY_{orig_env.upper()}")
                orig_service_key = os.environ.get(f"SUPABASE_SERVICE_KEY_{orig_env.upper()}")
                
                if orig_url:
                    os.environ["SUPABASE_URL"] = orig_url
                if orig_key:
                    os.environ["SUPABASE_KEY"] = orig_key
                if orig_service_key:
                    os.environ["SUPABASE_SERVICE_KEY"] = orig_service_key
                elif "SUPABASE_SERVICE_KEY" in os.environ:
                    del os.environ["SUPABASE_SERVICE_KEY"]
        
        # Store results in session for display
        if not results:
            flash(f"No verification results for {environment}", "warning")
        else:
            flash(f"Verification completed for {environment}", "success")
            if isinstance(results, dict):
                verification_status = "success"
                for k, v in results.items():
                    if isinstance(v, dict) and not v.get("success", False):
                        verification_status = "error"
                        break
                    elif not v:
                        verification_status = "error"
                        break
                
                flash(f"Verification status: {verification_status}", verification_status)
    
    except Exception as e:
        logger.error(f"Error verifying environment: {str(e)}")
        flash(f"Error verifying environment: {str(e)}", "error")
    
    return redirect(url_for("supabase_config.environments_page"))

@supabase_config.route("/supabase/wizard", methods=["GET"])
@login_required
@permission_required("admin")
def setup_wizard():
    """
    Show Supabase setup wizard.
    """
    return render_template("supabase/setup_wizard.html")

def register_routes(app):
    """
    Register all routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(supabase_config)
    logger.info("Supabase config routes registered successfully")