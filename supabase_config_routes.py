"""
Supabase Configuration Routes

This module provides Flask routes for configuring Supabase environments
and checking connection status.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List, Tuple

try:
    from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
    from werkzeug.security import generate_password_hash, check_password_hash
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Import Supabase environment manager
from supabase_env_manager import (
    get_all_environments,
    get_current_environment,
    set_current_environment,
    configure_environment
)

# Import Supabase verification tools
from verify_supabase_env import (
    check_environment_variables,
    check_supabase_connection,
    check_supabase_auth,
    check_supabase_storage,
    check_postgis_extension,
    test_migration_readiness
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Blueprint
bp = Blueprint('supabase_config', __name__, url_prefix='/supabase')

@bp.route('/')
def index():
    """Supabase configuration dashboard"""
    if not FLASK_AVAILABLE:
        return "Flask is not installed, cannot render templates"
    
    # Get environment information
    environments = get_all_environments()
    current_env = get_current_environment()
    
    return render_template(
        'supabase/index.html',
        environments=environments,
        current_env=current_env,
        title="Supabase Configuration"
    )

@bp.route('/environment/<env_name>')
def environment_details(env_name):
    """Environment details page"""
    if not FLASK_AVAILABLE:
        return "Flask is not installed, cannot render templates"
    
    # Get environment information
    environments = get_all_environments()
    current_env = get_current_environment()
    
    # Find the specific environment
    env_info = None
    for env, info in environments.items():
        if env == env_name:
            env_info = info
            break
    
    if not env_info:
        flash(f"Environment {env_name} not found", "danger")
        return redirect(url_for('supabase_config.index'))
    
    return render_template(
        'supabase/environment.html',
        environment=env_name,
        env_info=env_info,
        is_current=(env_name == current_env),
        title=f"Supabase {env_name} Environment"
    )

@bp.route('/set_active', methods=['POST'])
def set_active():
    """Set active Supabase environment"""
    if not FLASK_AVAILABLE:
        return "Flask is not installed, cannot process request"
    
    env_name = request.form.get('environment')
    
    if not env_name:
        flash("No environment specified", "danger")
        return redirect(url_for('supabase_config.index'))
    
    success = set_current_environment(env_name)
    
    if success:
        flash(f"Successfully set {env_name} as the active Supabase environment", "success")
    else:
        flash(f"Failed to set {env_name} as the active Supabase environment", "danger")
    
    return redirect(url_for('supabase_config.index'))

@bp.route('/configure', methods=['GET', 'POST'])
def configure():
    """Configure Supabase environment"""
    if not FLASK_AVAILABLE:
        return "Flask is not installed, cannot render templates"
    
    if request.method == 'POST':
        env_name = request.form.get('environment')
        url = request.form.get('url')
        key = request.form.get('key')
        service_key = request.form.get('service_key')
        set_active = request.form.get('set_active') == 'on'
        
        if not env_name or not url or not key:
            flash("Environment name, URL, and API key are required", "danger")
            return redirect(url_for('supabase_config.configure'))
        
        success = configure_environment(env_name, url, key, service_key)
        
        if success:
            flash(f"Successfully configured {env_name} environment", "success")
            
            if set_active:
                active_success = set_current_environment(env_name)
                if active_success:
                    flash(f"Set {env_name} as the active environment", "success")
                else:
                    flash(f"Failed to set {env_name} as the active environment", "warning")
            
            return redirect(url_for('supabase_config.index'))
        else:
            flash(f"Failed to configure {env_name} environment", "danger")
            return redirect(url_for('supabase_config.configure'))
    
    # GET request
    environments = ['development', 'training', 'production']
    current_env = get_current_environment()
    
    return render_template(
        'supabase/configure.html',
        environments=environments,
        current_env=current_env,
        title="Configure Supabase Environment"
    )

@bp.route('/test')
def test():
    """Test Supabase connection"""
    if not FLASK_AVAILABLE:
        return "Flask is not installed, cannot render templates"
    
    return render_template(
        'supabase/test.html',
        title="Test Supabase Connection"
    )

@bp.route('/api/test_connection', methods=['POST'])
def api_test_connection():
    """API endpoint to test Supabase connection"""
    if not FLASK_AVAILABLE:
        return "Flask is not installed, cannot process request"
    
    env_name = request.json.get('environment')
    
    # Save original environment
    orig_env = os.environ.get("SUPABASE_ACTIVE_ENVIRONMENT")
    
    try:
        # Set the environment to test if specified
        if env_name:
            os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = env_name
        
        # Run all checks
        results = {
            "variables": check_environment_variables(),
            "connection": check_supabase_connection(),
            "auth": check_supabase_auth(),
            "storage": check_supabase_storage(),
            "postgis": check_postgis_extension()
        }
        
        # Overall success if all checks passed
        results["success"] = all(check.get("success", False) for check in results.values())
        results["environment"] = env_name or orig_env or "development"
        
        if results["success"]:
            results["message"] = f"Environment {results['environment']} is ready for use"
        else:
            results["message"] = f"Environment {results['environment']} has issues - see individual checks for details"
        
        return jsonify(results)
    finally:
        # Restore original environment
        if orig_env and env_name:
            os.environ["SUPABASE_ACTIVE_ENVIRONMENT"] = orig_env

@bp.route('/api/test_all_environments', methods=['GET'])
def api_test_all_environments():
    """API endpoint to test all Supabase environments"""
    if not FLASK_AVAILABLE:
        return "Flask is not installed, cannot process request"
    
    results = {}
    
    for env in ['development', 'training', 'production']:
        results[env] = {}
        
        try:
            # Run basic checks
            var_check = check_environment_variables()
            conn_check = check_supabase_connection()
            auth_check = check_supabase_auth()
            storage_check = check_supabase_storage()
            postgis_check = check_postgis_extension()
            
            # Store results
            results[env] = {
                "variables": var_check,
                "connection": conn_check,
                "auth": auth_check,
                "storage": storage_check,
                "postgis": postgis_check,
                "success": all([
                    var_check.get("success", False),
                    conn_check.get("success", False),
                    auth_check.get("success", False),
                    storage_check.get("success", False),
                    postgis_check.get("success", False)
                ]),
                "message": "Ready for use" if all([
                    var_check.get("success", False),
                    conn_check.get("success", False),
                    auth_check.get("success", False),
                    storage_check.get("success", False),
                    postgis_check.get("success", False)
                ]) else "Has issues"
            }
        except Exception as e:
            results[env] = {
                "success": False,
                "message": f"Error running tests: {str(e)}"
            }
    
    return jsonify(results)

def register_routes(app):
    """Register Supabase configuration routes with Flask app"""
    if not FLASK_AVAILABLE:
        logger.warning("Flask is not installed, cannot register Supabase configuration routes")
        return False
    
    app.register_blueprint(bp)
    logger.info("Supabase config routes registered successfully")
    return True