import os
import ldap
from flask import session, redirect, url_for, flash, request
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# LDAP configuration - get from environment variables or use defaults
LDAP_SERVER = os.environ.get('LDAP_SERVER', 'ldap://benton.local')
LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN', 'dc=benton,dc=local')
LDAP_USER_DN = os.environ.get('LDAP_USER_DN', 'ou=users,dc=benton,dc=local')
LDAP_GROUP_DN = os.environ.get('LDAP_GROUP_DN', 'ou=groups,dc=benton,dc=local')
# In a dev environment, we might want to bypass LDAP for testing
BYPASS_LDAP = os.environ.get('BYPASS_LDAP', 'False').lower() == 'true'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def is_authenticated():
    """Check if user is authenticated"""
    return 'user' in session

def authenticate_user(username, password):
    """Authenticate user against LDAP"""
    if BYPASS_LDAP:
        # For development/testing only - bypass LDAP authentication
        logger.warning("LDAP authentication bypassed for development")
        return True
    
    if not username or not password:
        return False
    
    # Format the username to match expected LDAP format
    ldap_username = username
    if '@' not in ldap_username and '\\' not in ldap_username:
        ldap_username = f"benton\\{username}"  # Format for Windows AD
    
    try:
        # Initialize connection to LDAP server
        ldap_client = ldap.initialize(LDAP_SERVER)
        ldap_client.set_option(ldap.OPT_REFERRALS, 0)
        
        # Bind with the username and password
        ldap_client.simple_bind_s(ldap_username, password)
        
        # If we get here, the authentication was successful
        ldap_client.unbind_s()
        logger.info(f"Successfully authenticated user: {username}")
        return True
    
    except ldap.INVALID_CREDENTIALS:
        logger.warning(f"Invalid credentials for user: {username}")
        return False
    except ldap.SERVER_DOWN:
        logger.error("LDAP server unavailable")
        flash("Authentication service unavailable. Please try again later.", "danger")
        return False
    except Exception as e:
        logger.error(f"LDAP authentication error: {str(e)}")
        return False

def logout_user():
    """Remove user from session"""
    session.pop('user', None)
