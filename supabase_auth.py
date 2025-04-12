"""
Supabase Authentication Module

This module provides authentication functionality using Supabase Auth.
It integrates with Flask's session mechanism and provides user management
functions for sign-up, login, password reset, and more.
"""

import os
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from functools import wraps

from flask import session, redirect, url_for, request, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

from supabase_client import get_supabase_client
from config_loader import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Session keys
SESSION_USER_KEY = 'user'
SESSION_TOKEN_KEY = 'access_token'
SESSION_REFRESH_TOKEN_KEY = 'refresh_token'
SESSION_EXPIRES_AT_KEY = 'expires_at'

# User role constants
ROLE_ADMIN = 'admin'
ROLE_DATA_SETUP = 'data_setup'
ROLE_MOBILE_ASSESSOR = 'mobile_assessor'
ROLE_ANALYST = 'analyst'
ROLE_VIEWER = 'viewer'

# Default roles and permissions
DEFAULT_ROLES = [
    {
        'name': ROLE_ADMIN,
        'description': 'Administrator with full access'
    },
    {
        'name': ROLE_DATA_SETUP,
        'description': 'Data setup and configuration manager'
    },
    {
        'name': ROLE_MOBILE_ASSESSOR,
        'description': 'Mobile assessor for field work'
    },
    {
        'name': ROLE_ANALYST,
        'description': 'Data analyst with advanced query capabilities'
    },
    {
        'name': ROLE_VIEWER,
        'description': 'Read-only viewer of data and reports'
    }
]

def login_required(f):
    """
    Decorator to require login for view functions.
    Redirects to login page if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    """
    Decorator to require specific role for a view function.
    Redirects to login page if user doesn't have the required role.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                return redirect(url_for('login', next=request.url))
            
            if not has_role(role_name):
                flash(f'You need {role_name} role to access this page', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_authenticated() -> bool:
    """
    Check if the user is authenticated and session is valid.
    Handles token refresh if needed.
    
    Returns:
        True if user is authenticated, False otherwise
    """
    # Check if we have a user in session
    if SESSION_USER_KEY not in session:
        return False
    
    # Check if token is expired and needs refresh
    if SESSION_EXPIRES_AT_KEY in session:
        expires_at = session[SESSION_EXPIRES_AT_KEY]
        if expires_at <= datetime.utcnow().timestamp():
            # Token is expired, try to refresh it
            if SESSION_REFRESH_TOKEN_KEY in session:
                success = refresh_token(session[SESSION_REFRESH_TOKEN_KEY])
                if not success:
                    # Refresh failed, log user out
                    logout_user()
                    return False
            else:
                # No refresh token, log user out
                logout_user()
                return False
    
    # Set user in global context for the current request
    g.user = session[SESSION_USER_KEY]
    
    return True

def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get the current authenticated user.
    
    Returns:
        User data or None if not authenticated
    """
    if is_authenticated():
        return session.get(SESSION_USER_KEY)
    return None

def has_role(role_name: str) -> bool:
    """
    Check if the current user has a specific role.
    
    Args:
        role_name: The role to check for
        
    Returns:
        True if user has the role, False otherwise
    """
    user = get_current_user()
    if not user:
        return False
    
    user_roles = user.get('app_metadata', {}).get('roles', [])
    return role_name in user_roles

def get_user_roles() -> List[str]:
    """
    Get all roles for the current user.
    
    Returns:
        List of role names
    """
    user = get_current_user()
    if not user:
        return []
    
    return user.get('app_metadata', {}).get('roles', [])

def signup_user(email: str, password: str, user_data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Register a new user with Supabase Auth.
    
    Args:
        email: User email address
        password: User password
        user_data: Additional user data
        
    Returns:
        Tuple of (success, error_message, user_data)
    """
    client = get_supabase_client()
    if not client:
        return False, "Supabase client not available", None
    
    try:
        # Register user with Supabase
        result = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": user_data.get("full_name", ""),
                    "department": user_data.get("department", ""),
                    "phone": user_data.get("phone", ""),
                    "roles": user_data.get("roles", [ROLE_VIEWER])  # Default to viewer role
                }
            }
        })
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Signup error: {result.error}")
            return False, str(result.error), None
        
        # Store the user data
        if hasattr(result, 'user') and result.user:
            user_data = {
                "id": result.user.id,
                "email": email,
                "full_name": user_data.get("full_name", ""),
                "roles": user_data.get("roles", [ROLE_VIEWER])
            }
            
            # Insert user metadata into our users table
            client.table("users").insert({
                "id": result.user.id,
                "email": email,
                "username": email.split('@')[0],
                "full_name": user_data.get("full_name", ""),
                "department": user_data.get("department", ""),
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"User {email} registered successfully")
            return True, None, user_data
        
        return False, "User registration failed", None
    
    except Exception as e:
        logger.error(f"Error signing up user: {str(e)}")
        return False, str(e), None

def login_user(email: str, password: str) -> Tuple[bool, Optional[str]]:
    """
    Authenticate a user with Supabase Auth.
    
    Args:
        email: User email address
        password: User password
        
    Returns:
        Tuple of (success, error_message)
    """
    client = get_supabase_client()
    if not client:
        return False, "Supabase client not available"
    
    try:
        # Log in with Supabase
        result = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Login error: {result.error}")
            return False, str(result.error)
        
        # Store session data
        if hasattr(result, 'user') and result.user and hasattr(result, 'session') and result.session:
            # Set user in session
            session[SESSION_USER_KEY] = {
                "id": result.user.id,
                "email": result.user.email,
                "app_metadata": result.user.app_metadata,
                "user_metadata": result.user.user_metadata
            }
            
            # Set token data
            session[SESSION_TOKEN_KEY] = result.session.access_token
            session[SESSION_REFRESH_TOKEN_KEY] = result.session.refresh_token
            session[SESSION_EXPIRES_AT_KEY] = result.session.expires_at
            
            # Update last login
            try:
                client.table("users").update({
                    "last_login": datetime.utcnow().isoformat()
                }).eq("id", result.user.id).execute()
            except Exception as e:
                logger.warning(f"Could not update last login: {str(e)}")
            
            logger.info(f"User {email} logged in successfully")
            return True, None
        
        return False, "Login failed"
    
    except Exception as e:
        logger.error(f"Error logging in user: {str(e)}")
        return False, str(e)

def logout_user():
    """
    Log the user out and clear session data.
    """
    client = get_supabase_client()
    
    # Try to sign out with Supabase if we have a token
    if client and SESSION_TOKEN_KEY in session:
        try:
            client.auth.sign_out()
        except Exception as e:
            logger.warning(f"Error signing out with Supabase: {str(e)}")
    
    # Clear session data
    if SESSION_USER_KEY in session:
        del session[SESSION_USER_KEY]
    
    if SESSION_TOKEN_KEY in session:
        del session[SESSION_TOKEN_KEY]
    
    if SESSION_REFRESH_TOKEN_KEY in session:
        del session[SESSION_REFRESH_TOKEN_KEY]
    
    if SESSION_EXPIRES_AT_KEY in session:
        del session[SESSION_EXPIRES_AT_KEY]
    
    logger.info("User logged out")

def refresh_token(refresh_token: str) -> bool:
    """
    Refresh the authentication token.
    
    Args:
        refresh_token: The refresh token
        
    Returns:
        True if successful, False otherwise
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Refresh token with Supabase
        result = client.auth.refresh_session(refresh_token)
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Token refresh error: {result.error}")
            return False
        
        # Update session data
        if hasattr(result, 'session') and result.session:
            session[SESSION_TOKEN_KEY] = result.session.access_token
            session[SESSION_REFRESH_TOKEN_KEY] = result.session.refresh_token
            session[SESSION_EXPIRES_AT_KEY] = result.session.expires_at
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return False

def reset_password_request(email: str) -> Tuple[bool, Optional[str]]:
    """
    Request a password reset.
    
    Args:
        email: User email address
        
    Returns:
        Tuple of (success, error_message)
    """
    client = get_supabase_client()
    if not client:
        return False, "Supabase client not available"
    
    try:
        # Request password reset
        result = client.auth.reset_password_email(email)
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Password reset request error: {result.error}")
            return False, str(result.error)
        
        logger.info(f"Password reset requested for {email}")
        return True, None
    
    except Exception as e:
        logger.error(f"Error requesting password reset: {str(e)}")
        return False, str(e)

def reset_password(token: str, new_password: str) -> Tuple[bool, Optional[str]]:
    """
    Reset a user's password with a reset token.
    
    Args:
        token: Password reset token
        new_password: New password
        
    Returns:
        Tuple of (success, error_message)
    """
    client = get_supabase_client()
    if not client:
        return False, "Supabase client not available"
    
    try:
        # Update password with token
        result = client.auth.update_user({
            "password": new_password
        }, token)
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Password reset error: {result.error}")
            return False, str(result.error)
        
        logger.info("Password reset successfully")
        return True, None
    
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        return False, str(e)

def update_user_roles(user_id: str, roles: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Update a user's roles.
    
    Args:
        user_id: User ID
        roles: List of role names
        
    Returns:
        Tuple of (success, error_message)
    """
    client = get_supabase_client()
    if not client:
        return False, "Supabase client not available"
    
    try:
        # Update user metadata
        result = client.auth.admin.update_user_by_id(
            user_id,
            {
                "app_metadata": {
                    "roles": roles
                }
            }
        )
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Role update error: {result.error}")
            return False, str(result.error)
        
        logger.info(f"Updated roles for user {user_id}: {roles}")
        return True, None
    
    except Exception as e:
        logger.error(f"Error updating user roles: {str(e)}")
        return False, str(e)

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user data by ID.
    
    Args:
        user_id: User ID
        
    Returns:
        User data or None if not found
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Get user from Auth
        result = client.auth.admin.get_user_by_id(user_id)
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Get user error: {result.error}")
            return None
        
        if hasattr(result, 'user') and result.user:
            # Get additional user data from our table
            try:
                db_result = client.table("users").select("*").eq("id", user_id).execute()
                if db_result.data and len(db_result.data) > 0:
                    # Merge data
                    user_data = {
                        "id": result.user.id,
                        "email": result.user.email,
                        "app_metadata": result.user.app_metadata,
                        "user_metadata": result.user.user_metadata,
                        "created_at": result.user.created_at,
                        "last_sign_in_at": result.user.last_sign_in_at
                    }
                    user_data.update(db_result.data[0])
                    return user_data
            except Exception as e:
                logger.warning(f"Could not get additional user data: {str(e)}")
            
            # Return basic user data
            return {
                "id": result.user.id,
                "email": result.user.email,
                "app_metadata": result.user.app_metadata,
                "user_metadata": result.user.user_metadata,
                "created_at": result.user.created_at,
                "last_sign_in_at": result.user.last_sign_in_at
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return None

def list_users(page: int = 1, per_page: int = 100) -> Tuple[List[Dict[str, Any]], int]:
    """
    List users with pagination.
    
    Args:
        page: Page number (1-based)
        per_page: Users per page
        
    Returns:
        Tuple of (users_list, total_count)
    """
    client = get_supabase_client()
    if not client:
        return [], 0
    
    try:
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get users from our table with pagination
        result = client.table("users").select(
            "*, user_roles(role_id, roles(name, description))"
        ).order("created_at", desc=True).range(
            offset, offset + per_page - 1
        ).execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"List users error: {result.error}")
            return [], 0
        
        # Get total count
        count_result = client.table("users").select(
            "id", count="exact"
        ).execute()
        
        total_count = 0
        if hasattr(count_result, 'count') and count_result.count is not None:
            total_count = count_result.count
        
        return result.data, total_count
    
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return [], 0

def create_api_token(user_id: str, name: str, expires_in_days: int = 30) -> Optional[str]:
    """
    Create an API token for a user.
    
    Args:
        user_id: User ID
        name: Token name
        expires_in_days: Token validity in days
        
    Returns:
        API token or None on error
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Generate token
        token = str(uuid.uuid4())
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Insert token into database
        result = client.table("api_tokens").insert({
            "token": token,
            "name": name,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "revoked": False
        }).execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Create API token error: {result.error}")
            return None
        
        logger.info(f"Created API token '{name}' for user {user_id}")
        return token
    
    except Exception as e:
        logger.error(f"Error creating API token: {str(e)}")
        return None

def verify_api_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify an API token and get associated user.
    
    Args:
        token: API token
        
    Returns:
        User data or None if token is invalid
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Find token in database
        result = client.table("api_tokens").select(
            "*, users(*)"
        ).eq("token", token).eq("revoked", False).execute()
        
        if not result.data or len(result.data) == 0:
            logger.warning(f"API token not found or revoked")
            return None
        
        token_data = result.data[0]
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if expires_at < datetime.utcnow():
            logger.warning(f"API token expired")
            return None
        
        # Update last used timestamp
        client.table("api_tokens").update({
            "last_used_at": datetime.utcnow().isoformat()
        }).eq("token", token).execute()
        
        # Return user data
        if "users" in token_data and token_data["users"]:
            user_data = token_data["users"]
            
            # Get roles
            try:
                user_info = get_user(user_data["id"])
                if user_info and "app_metadata" in user_info:
                    user_data["app_metadata"] = user_info["app_metadata"]
            except Exception as e:
                logger.warning(f"Could not get user roles: {str(e)}")
            
            return user_data
        
        return None
    
    except Exception as e:
        logger.error(f"Error verifying API token: {str(e)}")
        return None

def revoke_api_token(token: str) -> bool:
    """
    Revoke an API token.
    
    Args:
        token: API token
        
    Returns:
        True if successful, False otherwise
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Mark token as revoked
        result = client.table("api_tokens").update({
            "revoked": True
        }).eq("token", token).execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Revoke API token error: {result.error}")
            return False
        
        logger.info(f"Revoked API token")
        return True
    
    except Exception as e:
        logger.error(f"Error revoking API token: {str(e)}")
        return False

def initialize_roles() -> bool:
    """
    Initialize default roles in the database.
    
    Returns:
        True if successful, False otherwise
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Insert default roles
        for role in DEFAULT_ROLES:
            # Check if role exists
            result = client.table("roles").select("*").eq("name", role["name"]).execute()
            
            if not result.data or len(result.data) == 0:
                # Role doesn't exist, create it
                client.table("roles").insert({
                    "name": role["name"],
                    "description": role["description"],
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
                
                logger.info(f"Created role: {role['name']}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error initializing roles: {str(e)}")
        return False