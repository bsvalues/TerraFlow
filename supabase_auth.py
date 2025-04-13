"""
Supabase Authentication Module

This module provides authentication and user management functions using Supabase Auth.
"""

import os
import logging
import json
from typing import Dict, Any, List, Tuple, Optional, Union
import time
import secrets
from datetime import datetime, timedelta

from flask import session, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define role constants for clarity
ROLE_ADMIN = 'admin'
ROLE_DATA_SETUP = 'data_setup'
ROLE_MOBILE_ASSESSOR = 'mobile_assessor'
ROLE_ANALYST = 'analyst'
ROLE_VIEWER = 'viewer'

# List of all available roles
ALL_ROLES = [ROLE_ADMIN, ROLE_DATA_SETUP, ROLE_MOBILE_ASSESSOR, ROLE_ANALYST, ROLE_VIEWER]

# Define permission constants
PERMISSION_MANAGE_USERS = 'manage_users'
PERMISSION_MANAGE_DATA = 'manage_data'
PERMISSION_VIEW_REPORTS = 'view_reports'
PERMISSION_EDIT_PROPERTY = 'edit_property'
PERMISSION_VIEW_PROPERTY = 'view_property'

# Define role to permission mapping
ROLE_PERMISSIONS = {
    ROLE_ADMIN: [PERMISSION_MANAGE_USERS, PERMISSION_MANAGE_DATA, PERMISSION_VIEW_REPORTS, PERMISSION_EDIT_PROPERTY, PERMISSION_VIEW_PROPERTY],
    ROLE_DATA_SETUP: [PERMISSION_MANAGE_DATA, PERMISSION_VIEW_REPORTS, PERMISSION_VIEW_PROPERTY],
    ROLE_MOBILE_ASSESSOR: [PERMISSION_EDIT_PROPERTY, PERMISSION_VIEW_PROPERTY],
    ROLE_ANALYST: [PERMISSION_VIEW_REPORTS, PERMISSION_VIEW_PROPERTY],
    ROLE_VIEWER: [PERMISSION_VIEW_PROPERTY]
}

# Session keys
SESSION_USER_KEY = 'user'
SESSION_AUTH_KEY = 'authenticated'
SESSION_TOKEN_KEY = 'access_token'
SESSION_REFRESH_TOKEN_KEY = 'refresh_token'

def _get_supabase_client():
    """
    Get the Supabase client from the current application context.
    
    Returns:
        Supabase client or None if not available
    """
    try:
        from supabase_client import get_supabase_client
        return get_supabase_client()
    except ImportError:
        logger.error("Failed to import supabase_client module")
        return None

def login_user(email: str, password: str) -> Tuple[bool, str]:
    """
    Log in a user with email and password using Supabase Auth.
    
    Args:
        email: User's email address
        password: User's password
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get Supabase client
        client = _get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return False, "Authentication service unavailable"
            
        # Sign in with Supabase
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        
        if response and response.user:
            # Extract user data
            user = response.user
            access_token = response.session.access_token if response.session else None
            refresh_token = response.session.refresh_token if response.session else None
            
            if not access_token:
                logger.error("No access token received from Supabase")
                return False, "Failed to get authentication token"
                
            # Store in session
            session[SESSION_USER_KEY] = {
                'id': user.id,
                'email': user.email,
                'full_name': user.user_metadata.get('full_name', '') if user.user_metadata else '',
                'department': user.user_metadata.get('department', '') if user.user_metadata else '',
                'created_at': user.created_at,
                'last_sign_in_at': user.last_sign_in_at
            }
            session[SESSION_AUTH_KEY] = True
            session[SESSION_TOKEN_KEY] = access_token
            session[SESSION_REFRESH_TOKEN_KEY] = refresh_token
            
            # Get user roles from metadata or fetch from database
            roles = _get_user_roles(user.id)
            session['roles'] = roles
            
            logger.info(f"User {email} logged in successfully")
            return True, ""
        else:
            logger.error("Failed to authenticate with Supabase")
            return False, "Invalid email or password"
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return False, f"Login error: {str(e)}"

def logout_user() -> None:
    """
    Log out the current user by clearing their session data.
    """
    # Clear session data
    session.pop(SESSION_USER_KEY, None)
    session.pop(SESSION_AUTH_KEY, None)
    session.pop(SESSION_TOKEN_KEY, None)
    session.pop(SESSION_REFRESH_TOKEN_KEY, None)
    session.pop('roles', None)
    
    # Try to sign out with Supabase client
    try:
        client = _get_supabase_client()
        if client:
            client.auth.sign_out()
    except Exception as e:
        logger.error(f"Error signing out from Supabase: {str(e)}")
    
    logger.info("User logged out")

def signup_user(email: str, password: str, user_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Register a new user with Supabase Auth.
    
    Args:
        email: User's email address
        password: User's password
        user_data: Additional user metadata (full_name, department, roles, etc.)
        
    Returns:
        Tuple of (success, error_message, user_data)
    """
    try:
        # Get Supabase client
        client = _get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return False, "Registration service unavailable", {}
            
        # Create user with Supabase
        signup_data = {
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": user_data.get('full_name', ''),
                    "department": user_data.get('department', '')
                }
            }
        }
        
        response = client.auth.sign_up(signup_data)
        
        if response and response.user:
            user = response.user
            
            # Add roles to user
            roles = user_data.get('roles', [ROLE_VIEWER])
            _set_user_roles(user.id, roles)
            
            logger.info(f"User {email} registered successfully")
            
            # Return user data
            user_info = {
                'id': user.id,
                'email': user.email,
                'full_name': user_data.get('full_name', ''),
                'department': user_data.get('department', ''),
                'created_at': user.created_at,
                'roles': roles
            }
            
            return True, "", user_info
        else:
            logger.error("Failed to register user with Supabase")
            return False, "Failed to create user account", {}
            
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return False, f"Registration error: {str(e)}", {}

def reset_password_request(email: str) -> Tuple[bool, str]:
    """
    Send a password reset request email to the user.
    
    Args:
        email: User's email address
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get Supabase client
        client = _get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return False, "Password reset service unavailable"
            
        # Send password reset email through Supabase
        client.auth.reset_password_for_email(email)
        
        logger.info(f"Password reset email sent to {email}")
        return True, ""
            
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        return False, f"Password reset error: {str(e)}"

def reset_password(token: str, new_password: str) -> Tuple[bool, str]:
    """
    Reset a user's password using a reset token.
    
    Args:
        token: Password reset token
        new_password: New password
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get Supabase client
        client = _get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return False, "Password reset service unavailable"
            
        # Process password reset with Supabase
        client.auth.update_user(
            {"password": new_password},
            jwt_token=token
        )
        
        logger.info("Password reset successful")
        return True, ""
            
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return False, f"Password reset error: {str(e)}"

def is_authenticated() -> bool:
    """
    Check if the current user is authenticated.
    
    Returns:
        True if authenticated, False otherwise
    """
    return session.get(SESSION_AUTH_KEY, False)

def get_current_user() -> Dict[str, Any]:
    """
    Get the current authenticated user's data.
    
    Returns:
        User data dictionary or empty dict if not authenticated
    """
    return session.get(SESSION_USER_KEY, {})

def has_role(role_name: str) -> bool:
    """
    Check if the current user has the specified role.
    
    Args:
        role_name: Name of the role to check
        
    Returns:
        True if user has the role, False otherwise
    """
    if not is_authenticated():
        return False
        
    roles = session.get('roles', [])
    
    # Admin role has access to everything
    if ROLE_ADMIN in roles:
        return True
        
    return role_name in roles

def has_permission(permission_name: str) -> bool:
    """
    Check if the current user has the specified permission.
    
    Args:
        permission_name: Name of the permission to check
        
    Returns:
        True if user has the permission, False otherwise
    """
    if not is_authenticated():
        return False
        
    roles = session.get('roles', [])
    
    # Check each role for the permission
    for role in roles:
        if role in ROLE_PERMISSIONS and permission_name in ROLE_PERMISSIONS[role]:
            return True
            
    return False

def get_user_roles() -> List[str]:
    """
    Get the current user's roles.
    
    Returns:
        List of role names
    """
    if not is_authenticated():
        return []
        
    return session.get('roles', [])

def _get_user_roles(user_id: str) -> List[str]:
    """
    Get a user's roles from the database.
    
    Args:
        user_id: Supabase user ID
        
    Returns:
        List of role names
    """
    try:
        # Get Supabase client
        client = _get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return [ROLE_VIEWER]  # Default to viewer role if no client
            
        # Query user_roles table
        response = client.table('user_roles').select('role').eq('user_id', user_id).execute()
        
        if response.data:
            # Extract role names from response
            roles = [item['role'] for item in response.data]
            return roles
        else:
            # If no roles found, assign default viewer role
            _set_user_roles(user_id, [ROLE_VIEWER])
            return [ROLE_VIEWER]
            
    except Exception as e:
        logger.error(f"Error getting user roles: {str(e)}")
        return [ROLE_VIEWER]  # Default to viewer role on error

def _set_user_roles(user_id: str, roles: List[str]) -> bool:
    """
    Set a user's roles in the database.
    
    Args:
        user_id: Supabase user ID
        roles: List of role names to assign
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get Supabase client
        client = _get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return False
            
        # First delete existing roles
        client.table('user_roles').delete().eq('user_id', user_id).execute()
        
        # Insert new roles
        if roles:
            role_records = [{'user_id': user_id, 'role': role} for role in roles]
            client.table('user_roles').insert(role_records).execute()
            
        return True
            
    except Exception as e:
        logger.error(f"Error setting user roles: {str(e)}")
        return False

def update_user_roles(user_id: str, roles: List[str]) -> Tuple[bool, str]:
    """
    Update a user's roles.
    
    Args:
        user_id: Supabase user ID
        roles: List of role names to assign
        
    Returns:
        Tuple of (success, error_message)
    """
    # Validate roles
    for role in roles:
        if role not in ALL_ROLES:
            return False, f"Invalid role: {role}"
            
    # Update roles in database
    success = _set_user_roles(user_id, roles)
    
    if success:
        return True, ""
    else:
        return False, "Failed to update user roles"

def list_users(page: int = 1, per_page: int = 20) -> Tuple[List[Dict[str, Any]], int]:
    """
    List users with pagination.
    
    Args:
        page: Page number (1-based)
        per_page: Number of users per page
        
    Returns:
        Tuple of (user_list, total_count)
    """
    try:
        # Get Supabase client
        client = _get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return [], 0
            
        # Calculate range for pagination
        start = (page - 1) * per_page
        end = start + per_page - 1
        
        # Get user count for pagination
        count_response = client.table('profiles').select('count', count='exact').execute()
        total_count = count_response.count if hasattr(count_response, 'count') else 0
        
        # Get users with pagination
        response = client.table('profiles').select('*').range(start, end).execute()
        
        if not response.data:
            return [], total_count
            
        # Get user roles
        users = []
        for user_data in response.data:
            user_id = user_data.get('id')
            roles = _get_user_roles(user_id) if user_id else []
            
            user_data['roles'] = roles
            users.append(user_data)
            
        return users, total_count
            
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return [], 0

def initialize_roles() -> bool:
    """
    Initialize the roles and permissions tables in the database.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get Supabase client
        client = _get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return False
            
        # First ensure the necessary tables exist
        # This would typically be done via migrations, but we'll check here too
        
        # Insert or update roles
        role_records = [{'name': role, 'description': f"{role.replace('_', ' ').title()} role"} for role in ALL_ROLES]
        
        for role in role_records:
            client.table('roles').upsert(role, on_conflict='name').execute()
            
        # Insert or update permissions
        all_permissions = list(set([perm for perms in ROLE_PERMISSIONS.values() for perm in perms]))
        perm_records = [{'name': perm, 'description': f"{perm.replace('_', ' ').title()} permission"} for perm in all_permissions]
        
        for perm in perm_records:
            client.table('permissions').upsert(perm, on_conflict='name').execute()
            
        # Insert or update role-permission mappings
        for role, permissions in ROLE_PERMISSIONS.items():
            # Delete existing mappings
            client.table('role_permissions').delete().eq('role', role).execute()
            
            # Insert new mappings
            for perm in permissions:
                client.table('role_permissions').insert({'role': role, 'permission': perm}).execute()
                
        logger.info("Roles and permissions initialized successfully")
        return True
            
    except Exception as e:
        logger.error(f"Error initializing roles: {str(e)}")
        return False