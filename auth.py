import os
import time
from flask import session, redirect, url_for, flash, request, jsonify, current_app
from functools import wraps
import logging
import datetime
import json
from app import db

# Conditionally import ldap
try:
    import ldap
    HAS_LDAP = True
except ImportError:
    HAS_LDAP = False
    logging.getLogger(__name__).warning("LDAP module not available, authentication will be simplified")

# Conditionally import Azure AD libraries
try:
    import msal
    HAS_MSAL = True
except ImportError:
    HAS_MSAL = False
    logging.getLogger(__name__).warning("MSAL module not available, Azure AD authentication will be disabled")

logger = logging.getLogger(__name__)

# LDAP configuration - get from environment variables or use defaults
LDAP_SERVER = os.environ.get('LDAP_SERVER', 'ldap://benton.local')
LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN', 'dc=benton,dc=local')
LDAP_USER_DN = os.environ.get('LDAP_USER_DN', 'ou=users,dc=benton,dc=local')
LDAP_GROUP_DN = os.environ.get('LDAP_GROUP_DN', 'ou=groups,dc=benton,dc=local')

# Azure AD configuration
AZURE_AD_TENANT_ID = os.environ.get('AZURE_AD_TENANT_ID', '')
AZURE_AD_CLIENT_ID = os.environ.get('AZURE_AD_CLIENT_ID', '')
AZURE_AD_CLIENT_SECRET = os.environ.get('AZURE_AD_CLIENT_SECRET', '')
AZURE_AD_REDIRECT_URI = os.environ.get('AZURE_AD_REDIRECT_URI', 'http://localhost:5000/auth/callback')

# In a dev environment, we might want to bypass LDAP for testing
# Default to True since we're running in a development environment
BYPASS_LDAP = os.environ.get('BYPASS_LDAP', 'True').lower() == 'true'

def login_required(f):
    """Decorator to require login for view functions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_name):
    """Decorator to require specific permission for a view function"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not has_permission(permission_name):
                flash(f'You do not have permission to access this page: {permission_name} required', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(role_name):
    """Decorator to require specific role for a view function"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not has_role(role_name):
                flash(f'You do not have permission to access this page: {role_name} role required', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_authenticated():
    """Check if user is authenticated"""
    # For development, create a test user in session if bypass is enabled
    if BYPASS_LDAP and 'user' not in session:
        from models import User
        # Retrieve the user from the database to include roles and permissions
        dev_user = User.query.filter_by(username='dev_user').first()
        if dev_user:
            session['user'] = {
                'id': dev_user.id,
                'username': dev_user.username,
                'email': dev_user.email,
                'full_name': dev_user.full_name,
                'department': dev_user.department,
                'roles': [role.name for role in dev_user.roles],
                'permissions': dev_user.get_permissions()
            }
            logger.warning("Using development test user for authentication bypass")
        
    return 'user' in session

def has_role(role_name):
    """Check if the current user has a specific role"""
    if not is_authenticated():
        return False
    
    # If user has roles stored in session, check there first
    if 'roles' in session['user']:
        return role_name in session['user']['roles']
    
    # Otherwise, check the database
    from models import User, Role
    user = User.query.get(session['user']['id'])
    if user:
        return user.has_role(role_name)
    
    return False

def has_permission(permission_name):
    """Check if the current user has a specific permission"""
    if not is_authenticated():
        return False
    
    # If user has permissions stored in session, check there first
    if 'permissions' in session['user']:
        return permission_name in session['user']['permissions']
    
    # Otherwise, check the database
    from models import User
    user = User.query.get(session['user']['id'])
    if user:
        return user.has_permission(permission_name)
    
    return False

def get_user_permissions():
    """Get all permissions for the current user"""
    if not is_authenticated():
        return []
        
    # If user has permissions stored in session, return them
    if 'permissions' in session['user']:
        return session['user']['permissions']
    
    # Otherwise, get them from the database
    from models import User
    user = User.query.get(session['user']['id'])
    if user:
        return user.get_permissions()
    
    return []

def authenticate_user(username, password):
    """Authenticate user against LDAP or Azure AD"""
    if BYPASS_LDAP:
        # For development/testing only - bypass LDAP authentication
        logger.warning("LDAP authentication bypassed for development mode")
        # For demonstration purposes only - accept any username/password combo
        # that isn't empty in dev/test mode
        if username and password:
            # Log this authentication in the audit log
            from models import AuditLog
            audit_log = AuditLog(
                user_id=1,  # dev_user ID
                action='login',
                details={'method': 'bypass', 'success': True},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(audit_log)
            db.session.commit()
            return True
        return False
    
    auth_method = request.form.get('auth_method', 'ldap')
    
    if auth_method == 'azure_ad' and HAS_MSAL:
        return _authenticate_azure_ad()
    else:
        return _authenticate_ldap(username, password)

def _authenticate_ldap(username, password):
    """Authenticate user against LDAP/Active Directory"""
    if not HAS_LDAP:
        logger.error("LDAP module not available")
        return False
        
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
        
        # Get user information from LDAP
        user_info = {}
        search_filter = f"(sAMAccountName={username})"
        if '@' in username:
            search_filter = f"(userPrincipalName={username})"
            
        try:
            # Search for the user to get their information
            results = ldap_client.search_s(
                LDAP_BASE_DN,
                ldap.SCOPE_SUBTREE,
                search_filter,
                ['displayName', 'mail', 'department', 'objectGUID']
            )
            
            if results and len(results) > 0:
                dn, attributes = results[0]
                if attributes:
                    if 'displayName' in attributes and attributes['displayName']:
                        user_info['full_name'] = attributes['displayName'][0].decode('utf-8')
                    if 'mail' in attributes and attributes['mail']:
                        user_info['email'] = attributes['mail'][0].decode('utf-8')
                    if 'department' in attributes and attributes['department']:
                        user_info['department'] = attributes['department'][0].decode('utf-8')
                    if 'objectGUID' in attributes and attributes['objectGUID']:
                        # Store object GUID for future reference
                        user_info['ad_object_id'] = attributes['objectGUID'][0].hex()
        except Exception as e:
            logger.warning(f"Error retrieving user info from LDAP: {str(e)}")
                
        ldap_client.unbind_s()
        
        # Log this authentication in the audit log
        from models import User, AuditLog
        user = User.query.filter_by(username=username).first()
        if user:
            audit_log = AuditLog(
                user_id=user.id,
                action='login',
                details={'method': 'ldap', 'success': True},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(audit_log)
            
            # Update the user's last login time
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()

        logger.info(f"Successfully authenticated user: {username}")
        
        # Return the user info for account creation/update
        return True, user_info if user_info else True
    
    except Exception as e:
        # Only access LDAP exception types if we have the module
        if isinstance(e, ldap.INVALID_CREDENTIALS):
            logger.warning(f"Invalid credentials for user: {username}")
            
            # Log failed login attempt
            from models import User, AuditLog
            user = User.query.filter_by(username=username).first()
            if user:
                audit_log = AuditLog(
                    user_id=user.id,
                    action='login_failed',
                    details={'method': 'ldap', 'reason': 'invalid_credentials'},
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string
                )
                db.session.add(audit_log)
                db.session.commit()
                
            return False
        elif isinstance(e, ldap.SERVER_DOWN):
            logger.error("LDAP server unavailable")
            flash("Authentication service unavailable. Please try again later.", "danger")
            return False
        
        logger.error(f"Authentication error: {str(e)}")
        return False

def _authenticate_azure_ad():
    """Authenticate user using Azure AD (OAuth flow)"""
    if not HAS_MSAL:
        logger.error("MSAL module not available for Azure AD authentication")
        return False
        
    # This would be the start of the Azure AD authentication flow
    # We would redirect to Azure AD login page and handle the callback
    # For now, just return False as placeholder
    
    # Implementation will vary based on specific Azure AD integration requirements
    logger.warning("Azure AD authentication not yet implemented")
    return False

def logout_user():
    """Remove user from session and log the logout"""
    
    # Log the logout in the audit log if the user was authenticated
    if 'user' in session:
        from models import AuditLog
        
        try:
            audit_log = AuditLog(
                user_id=session['user']['id'],
                action='logout',
                details={'method': 'explicit_logout'},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(audit_log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error logging logout: {str(e)}")
    
    # Clear the session
    session.pop('user', None)
