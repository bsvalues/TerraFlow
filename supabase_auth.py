"""
Supabase Authentication Module

This module provides authentication functions using Supabase Auth.
It handles login, registration, password reset, and user management.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Union

from flask import session, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from supabase_client import get_supabase_client

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define roles
ALL_ROLES = ['admin', 'manager', 'analyst', 'editor', 'viewer']

def login_user(email: str, password: str) -> Tuple[bool, str]:
    """
    Authenticate a user with email and password
    
    Args:
        email: User's email
        password: User's password
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Try to authenticate with Supabase
        client = get_supabase_client()
        if client:
            # Use Supabase Auth
            auth_response = client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if auth_response.user:
                # Get user data from profiles table
                user_id = auth_response.user.id
                user_data_response = client.table('profiles').select('*').eq('id', user_id).execute()
                
                # Also login with Flask-Login
                from flask_login import login_user as flask_login_user
                from models import User
                user = User.query.filter_by(email=email).first()
                if user:
                    flask_login_user(user)
                    logger.info(f"User {email} logged in with Flask-Login")
                
                if user_data_response.data:
                    user_data = user_data_response.data[0]
                else:
                    # Create a basic profile if it doesn't exist
                    user_data = {
                        'id': user_id,
                        'email': email,
                        'roles': ['viewer']
                    }
                    client.table('profiles').insert(user_data).execute()
                
                # Store user info in session
                session['authenticated'] = True
                session['user'] = {
                    'id': user_id,
                    'email': email,
                    'full_name': user_data.get('full_name', ''),
                    'department': user_data.get('department', ''),
                    'roles': user_data.get('roles', ['viewer'])
                }
                
                logger.info(f"User {email} logged in successfully")
                return True, ""
            else:
                logger.warning(f"Failed login attempt for {email}")
                return False, "Invalid email or password"
        else:
            # If Supabase is not available, use development fallback
            # This is only for testing and should be removed in production
            if current_app.config.get('ENV') == 'development':
                logger.warning("Using development test user for authentication bypass")
                session['authenticated'] = True
                session['user'] = {
                    'id': '123456789',
                    'email': email,
                    'full_name': 'Test User',
                    'department': 'GIS',
                    'roles': ['admin', 'viewer']
                }
                return True, ""
            
            return False, "Authentication service unavailable"
            
    except Exception as e:
        logger.error(f"Error in login_user: {str(e)}")
        return False, str(e)

def logout_user() -> None:
    """
    Log out the current user
    """
    try:
        client = get_supabase_client()
        if client and session.get('authenticated'):
            client.auth.sign_out()
        
        # Clear session
        session.pop('authenticated', None)
        session.pop('user', None)
        
        # Also logout with Flask-Login
        from flask_login import logout_user as flask_logout_user
        flask_logout_user()
        
        logger.info("User logged out")
    except Exception as e:
        logger.error(f"Error in logout_user: {str(e)}")

def signup_user(email: str, password: str, user_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Register a new user
    
    Args:
        email: User's email
        password: User's password
        user_data: Additional user data (full_name, department, etc.)
        
    Returns:
        Tuple of (success, error_message, user_info)
    """
    try:
        client = get_supabase_client()
        if client:
            # Create the user in Supabase Auth
            auth_response = client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if auth_response.user:
                user_id = auth_response.user.id
                
                # Add user data to profiles table
                profile_data = {
                    'id': user_id,
                    'email': email,
                    'full_name': user_data.get('full_name', ''),
                    'department': user_data.get('department', ''),
                    'roles': user_data.get('roles', ['viewer'])
                }
                
                client.table('profiles').insert(profile_data).execute()
                
                logger.info(f"User {email} registered successfully")
                return True, "", profile_data
            else:
                logger.warning(f"Failed registration attempt for {email}")
                return False, "Registration failed", None
        else:
            # If Supabase is not available, use development fallback
            if current_app.config.get('ENV') == 'development':
                logger.warning("Using development test registration")
                test_user = {
                    'id': '123456789',
                    'email': email,
                    'full_name': user_data.get('full_name', ''),
                    'department': user_data.get('department', ''),
                    'roles': user_data.get('roles', ['viewer'])
                }
                return True, "", test_user
            
            return False, "Registration service unavailable", None
            
    except Exception as e:
        logger.error(f"Error in signup_user: {str(e)}")
        return False, str(e), None

def reset_password_request(email: str) -> Tuple[bool, str]:
    """
    Send a password reset email
    
    Args:
        email: User's email
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        client = get_supabase_client()
        if client:
            client.auth.reset_password_email(email)
            logger.info(f"Password reset email sent to {email}")
            return True, ""
        else:
            # If Supabase is not available, use development fallback
            if current_app.config.get('ENV') == 'development':
                logger.warning(f"Development password reset for {email}")
                return True, ""
            
            return False, "Password reset service unavailable"
            
    except Exception as e:
        logger.error(f"Error in reset_password_request: {str(e)}")
        return False, str(e)

def reset_password(token: str, new_password: str) -> Tuple[bool, str]:
    """
    Reset a user's password using a reset token
    
    Args:
        token: Password reset token
        new_password: New password
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        client = get_supabase_client()
        if client:
            client.auth.verify_otp({
                "token_hash": token,
                "type": "recovery",
                "new_password": new_password
            })
            
            logger.info("Password reset successful")
            return True, ""
        else:
            # If Supabase is not available, use development fallback
            if current_app.config.get('ENV') == 'development':
                logger.warning("Development password reset")
                return True, ""
            
            return False, "Password reset service unavailable"
            
    except Exception as e:
        logger.error(f"Error in reset_password: {str(e)}")
        return False, str(e)

def is_authenticated() -> bool:
    """
    Check if the current user is authenticated
    
    Returns:
        True if user is authenticated, False otherwise
    """
    return session.get('authenticated', False)

def has_role(role_name: str) -> bool:
    """
    Check if the current user has a specific role
    
    Args:
        role_name: Role to check
        
    Returns:
        True if user has the role, False otherwise
    """
    if not is_authenticated():
        return False
    
    user_roles = session.get('user', {}).get('roles', [])
    return role_name in user_roles or 'admin' in user_roles

def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get the current user's information
    
    Returns:
        User information or None if not authenticated
    """
    if not is_authenticated():
        return None
    
    return session.get('user', {})

def list_users(page: int = 1, per_page: int = 10) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get a list of users
    
    Args:
        page: Page number (starting from 1)
        per_page: Number of users per page
        
    Returns:
        Tuple of (users, total_count)
    """
    try:
        client = get_supabase_client()
        if client:
            # Calculate pagination
            from_idx = (page - 1) * per_page
            to_idx = from_idx + per_page - 1
            
            # Get users from profiles table
            response = client.table('profiles').select('*').range(from_idx, to_idx).execute()
            
            # Get total count
            count_response = client.table('profiles').select('id', count='exact').execute()
            total_count = count_response.count or 0
            
            return response.data, total_count
        else:
            # If Supabase is not available, use development fallback
            if current_app.config.get('ENV') == 'development':
                logger.warning("Using development test user list")
                test_users = [
                    {
                        'id': '123456789',
                        'email': 'admin@example.com',
                        'full_name': 'Admin User',
                        'department': 'GIS',
                        'roles': ['admin', 'viewer']
                    },
                    {
                        'id': '987654321',
                        'email': 'analyst@example.com',
                        'full_name': 'Analyst User',
                        'department': 'Assessment',
                        'roles': ['analyst', 'viewer']
                    }
                ]
                return test_users, len(test_users)
            
            return [], 0
            
    except Exception as e:
        logger.error(f"Error in list_users: {str(e)}")
        return [], 0

def update_user_roles(user_id: str, roles: List[str]) -> Tuple[bool, str]:
    """
    Update a user's roles
    
    Args:
        user_id: User ID
        roles: List of roles
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Validate roles
        valid_roles = [role for role in roles if role in ALL_ROLES]
        
        client = get_supabase_client()
        if client:
            # Update user roles in profiles table
            client.table('profiles').update({'roles': valid_roles}).eq('id', user_id).execute()
            
            logger.info(f"Roles updated for user {user_id}: {valid_roles}")
            return True, ""
        else:
            # If Supabase is not available, use development fallback
            if current_app.config.get('ENV') == 'development':
                logger.warning(f"Development role update for user {user_id}: {valid_roles}")
                return True, ""
            
            return False, "User management service unavailable"
            
    except Exception as e:
        logger.error(f"Error in update_user_roles: {str(e)}")
        return False, str(e)

def initialize_roles() -> bool:
    """
    Initialize default roles in the database
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_supabase_client()
        if client:
            # First, check if roles table exists
            response = client.table('roles').select('name').execute()
            
            existing_roles = [r['name'] for r in response.data] if response.data else []
            
            # Add missing roles
            for role_name in ALL_ROLES:
                if role_name not in existing_roles:
                    client.table('roles').insert({'name': role_name}).execute()
            
            logger.info(f"Roles initialized: {ALL_ROLES}")
            return True
        else:
            # If Supabase is not available, use development fallback
            if current_app.config.get('ENV') == 'development':
                logger.warning("Development role initialization")
                return True
            
            return False
            
    except Exception as e:
        logger.error(f"Error in initialize_roles: {str(e)}")
        return False