"""
Supabase Environment Management Routes

This module provides Flask routes for configuring and managing Supabase environments.
"""

import os
import logging
import traceback
from typing import Dict, Any, Optional
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

from auth import login_required, role_required
from supabase_env_manager import (
    get_current_environment, 
    set_current_environment,
    get_all_configured_environments,
    get_environment_url,
    get_environment_key,
    get_environment_service_key,
    check_environment_config
)
from supabase_client import get_supabase_client

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
supabase_config_bp = Blueprint('supabase_config', __name__, url_prefix='/supabase')

# Admin password for protecting sensitive operations
ADMIN_PASSWORD_HASH = None

@supabase_config_bp.route('/')
@login_required
@role_required('admin')
def index():
    """
    Supabase configuration home page.
    """
    return redirect(url_for('supabase_config.environments'))

@supabase_config_bp.route('/environments')
@login_required
@role_required('admin')
def environments():
    """
    View and manage Supabase environments.
    """
    # Get environment status
    configured_environments = get_all_configured_environments()
    
    # Get current environment
    current_env = get_current_environment()
    
    # Get environment details (masked)
    environment_details = {
        'development': {
            'url': get_environment_url('development'),
            'key': get_environment_key('development'),
            'has_service_key': bool(get_environment_service_key('development'))
        },
        'training': {
            'url': get_environment_url('training'),
            'key': get_environment_key('training'),
            'has_service_key': bool(get_environment_service_key('training'))
        },
        'production': {
            'url': get_environment_url('production'),
            'key': get_environment_key('production'),
            'has_service_key': bool(get_environment_service_key('production'))
        }
    }
    
    return render_template(
        'supabase/environments.html',
        environments=configured_environments,
        current_environment=current_env,
        environment_details=environment_details
    )

@supabase_config_bp.route('/set-environment/<environment>')
@login_required
@role_required('admin')
def set_current_environment_route(environment):
    """
    Set the current active Supabase environment.
    """
    if environment not in ['development', 'training', 'production']:
        flash(f"Invalid environment: {environment}", 'danger')
        return redirect(url_for('supabase_config.environments'))
    
    try:
        set_current_environment(environment)
        flash(f"Current Supabase environment set to: {environment}", 'success')
    except Exception as e:
        logger.error(f"Error setting environment to {environment}: {str(e)}")
        flash(f"Error setting environment: {str(e)}", 'danger')
    
    return redirect(url_for('supabase_config.environments'))

@supabase_config_bp.route('/setup-environment/<environment>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def setup_environment(environment):
    """
    Set up a specific Supabase environment.
    """
    if environment not in ['development', 'training', 'production']:
        flash(f"Invalid environment: {environment}", 'danger')
        return redirect(url_for('supabase_config.environments'))
    
    if request.method == 'POST':
        # Verify admin password
        if not verify_admin_password(request.form.get('admin_password', '')):
            flash("Invalid admin password", 'danger')
            return render_template('supabase/setup_environment.html', environment=environment)
        
        # Get form data
        url = request.form.get('url', '').strip()
        key = request.form.get('api_key', '').strip()
        service_key = request.form.get('service_key', '').strip()
        
        if not url or not key:
            flash("URL and API key are required", 'danger')
            return render_template('supabase/setup_environment.html', environment=environment)
        
        try:
            # Set environment variables
            os.environ[f"SUPABASE_URL_{environment.upper()}"] = url
            os.environ[f"SUPABASE_KEY_{environment.upper()}"] = key
            if service_key:
                os.environ[f"SUPABASE_SERVICE_KEY_{environment.upper()}"] = service_key
            
            # If this is the development environment, also set the base variables
            if environment == 'development':
                os.environ["SUPABASE_URL"] = url
                os.environ["SUPABASE_KEY"] = key
                if service_key:
                    os.environ["SUPABASE_SERVICE_KEY"] = service_key
            
            # Update .env file if requested
            if request.form.get('update_env_file') == 'yes':
                update_env_file(environment, url, key, service_key)
                flash(f"Environment variables for {environment} saved to .env file", 'success')
            
            flash(f"Supabase {environment} environment configured successfully", 'success')
            return redirect(url_for('supabase_config.environments'))
            
        except Exception as e:
            logger.error(f"Error configuring {environment} environment: {str(e)}")
            logger.error(traceback.format_exc())
            flash(f"Error configuring environment: {str(e)}", 'danger')
    
    return render_template('supabase/setup_environment.html', environment=environment)

@supabase_config_bp.route('/test-environment/<environment>')
@login_required
@role_required('admin')
def test_environment(environment):
    """
    Test the connection to a Supabase environment.
    """
    if environment not in ['development', 'training', 'production']:
        flash(f"Invalid environment: {environment}", 'danger')
        return redirect(url_for('supabase_config.environments'))
    
    try:
        # Check if environment is configured
        if not check_environment_config(environment):
            flash(f"Environment {environment} is not properly configured", 'danger')
            return redirect(url_for('supabase_config.environments'))
        
        # Try to get a client
        client = get_supabase_client(environment)
        if not client:
            flash(f"Failed to create Supabase client for {environment} environment", 'danger')
            return redirect(url_for('supabase_config.environments'))
        
        # Try a simple query
        try:
            # Try to query a system table or health check endpoint
            result = client.table('_system').select('version').limit(1).execute()
            flash(f"Successfully connected to Supabase {environment} environment!", 'success')
        except Exception:
            # Fallback to a more generic check
            try:
                response = client.functions.invoke('health-check')
                flash(f"Successfully connected to Supabase {environment} environment!", 'success')
            except Exception as e:
                # Last resort - just check if we can access the auth API
                auth_response = client.auth.get_user()
                flash(f"Successfully connected to Supabase {environment} environment!", 'success')
    
    except Exception as e:
        logger.error(f"Error testing connection to {environment} environment: {str(e)}")
        logger.error(traceback.format_exc())
        flash(f"Error testing connection: {str(e)}", 'danger')
    
    return redirect(url_for('supabase_config.environments'))

@supabase_config_bp.route('/setup-wizard')
@login_required
@role_required('admin')
def setup_wizard():
    """
    Launch the Supabase environment setup wizard.
    """
    return render_template('supabase/setup_wizard.html')

@supabase_config_bp.route('/api/environments')
@login_required
@role_required('admin')
def api_environments():
    """
    Get environment status as JSON.
    """
    configured_environments = get_all_configured_environments()
    current_env = get_current_environment()
    
    return jsonify({
        'environments': configured_environments,
        'current_environment': current_env
    })

def update_env_file(environment: str, url: str, key: str, service_key: Optional[str] = None) -> None:
    """
    Update .env file with environment-specific credentials
    
    Args:
        environment: Environment name
        url: Supabase URL
        key: Supabase API key
        service_key: Optional Supabase service role key
    """
    env_path = ".env"
    env_vars = {}
    
    # Read existing .env file
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    name, value = line.split('=', 1)
                    env_vars[name.strip()] = value.strip()
    
    # Update with new values
    env_vars[f"SUPABASE_URL_{environment.upper()}"] = url
    env_vars[f"SUPABASE_KEY_{environment.upper()}"] = key
    if service_key:
        env_vars[f"SUPABASE_SERVICE_KEY_{environment.upper()}"] = service_key
    
    # If this is the default environment, also set the base variables
    if environment == "development":
        env_vars["SUPABASE_URL"] = url
        env_vars["SUPABASE_KEY"] = key
        if service_key:
            env_vars["SUPABASE_SERVICE_KEY"] = service_key
    
    # Write back to .env file
    with open(env_path, 'w') as f:
        for name, value in env_vars.items():
            f.write(f"{name}={value}\n")

def verify_admin_password(password: str) -> bool:
    """
    Verify the admin password for sensitive operations.
    
    Args:
        password: Admin password to verify
        
    Returns:
        True if password is valid, False otherwise
    """
    global ADMIN_PASSWORD_HASH
    
    # In development mode, always allow access
    if os.environ.get('FLASK_ENV') == 'development':
        return True
    
    # If admin password is not set, use a default for initial setup
    if not ADMIN_PASSWORD_HASH:
        default_password = os.environ.get('ADMIN_PASSWORD', 'admin')
        ADMIN_PASSWORD_HASH = generate_password_hash(default_password)
    
    return check_password_hash(ADMIN_PASSWORD_HASH, password)

def init_app(app):
    """
    Initialize the Supabase config routes with the Flask app.
    
    Args:
        app: Flask application
    """
    app.register_blueprint(supabase_config_bp)
    app.logger.info("Supabase config routes registered successfully")