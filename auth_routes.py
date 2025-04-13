"""
Authentication Routes Module

This module provides Flask routes for user authentication, registration,
and user management using Supabase Auth.
"""

import os
import logging
from typing import Dict, Any
from functools import wraps

from flask import (
    Blueprint, render_template, request, flash, redirect, 
    url_for, session, g, jsonify, current_app
)

from supabase_auth import (
    login_user, logout_user, signup_user, reset_password_request,
    reset_password, is_authenticated, has_role, get_current_user,
    get_user_roles, initialize_roles, update_user_roles, list_users,
    ROLE_ADMIN, ROLE_DATA_SETUP, ROLE_MOBILE_ASSESSOR, ROLE_ANALYST, ROLE_VIEWER
)

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login page.
    
    GET: Display login form
    POST: Process login attempt
    """
    # If user is already logged in, redirect to home
    if is_authenticated():
        return redirect(url_for('index'))
    
    # Handle form submission
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please provide both email and password', 'error')
            return render_template('login.html')
        
        # Attempt to log in
        success, error_message = login_user(email, password)
        
        if success:
            # Get redirect URL if any
            next_url = request.form.get('next') or request.args.get('next')
            
            # Flash success message
            flash('Login successful!', 'success')
            
            # Redirect to next URL or index
            if next_url:
                return redirect(next_url)
            else:
                return redirect(url_for('index'))
        else:
            # Flash error message
            flash(f'Login failed: {error_message}', 'error')
    
    # Render login template for GET request or failed login
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """
    Log the user out and redirect to login page.
    """
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration page.
    
    GET: Display registration form
    POST: Process registration attempt
    """
    # If user is already logged in, redirect to home
    if is_authenticated():
        return redirect(url_for('index'))
    
    # Handle form submission
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        department = request.form.get('department', '').strip()
        
        # Validate input
        if not email or not password or not confirm_password:
            flash('Please fill in all required fields', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        # Create user data
        user_data = {
            'full_name': full_name,
            'department': department,
            'roles': [ROLE_VIEWER]  # Default role for new users
        }
        
        # Attempt to register
        success, error_message, user = signup_user(email, password, user_data)
        
        if success:
            # Flash success message
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Flash error message
            flash(f'Registration failed: {error_message}', 'error')
    
    # Render registration template for GET request or failed registration
    return render_template('register.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request_route():
    """
    Password reset request page.
    
    GET: Display reset password form
    POST: Process reset password request
    """
    # Handle form submission
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('Please provide your email address', 'error')
            return render_template('reset_password_request.html')
        
        # Attempt to send reset password email
        success, error_message = reset_password_request(email)
        
        if success:
            # Flash success message
            flash('Password reset instructions have been sent to your email', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Flash error message
            flash(f'Password reset request failed: {error_message}', 'error')
    
    # Render reset password template for GET request or failed request
    return render_template('reset_password_request.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_route(token):
    """
    Password reset confirmation page.
    
    GET: Display reset password confirmation form
    POST: Process password reset
    """
    # Handle form submission
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or not confirm_password:
            flash('Please provide a new password', 'error')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', token=token)
        
        # Attempt to reset password
        success, error_message = reset_password(token, password)
        
        if success:
            # Flash success message
            flash('Password has been reset successfully. Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Flash error message
            flash(f'Password reset failed: {error_message}', 'error')
    
    # Render reset password confirmation template
    return render_template('reset_password.html', token=token)

@auth_bp.route('/profile')
def profile():
    """
    User profile page.
    """
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = get_current_user()
    roles = get_user_roles()
    
    return render_template('profile.html', user=user, roles=roles)

@auth_bp.route('/users')
def user_list():
    """
    User management page (admin only).
    """
    if not is_authenticated() or not has_role(ROLE_ADMIN):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Get page number from query string
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get users with pagination
    users, total_count = list_users(page, per_page)
    
    # Calculate pagination values
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('user_list.html', 
                          users=users, 
                          page=page, 
                          per_page=per_page,
                          total_pages=total_pages,
                          total_count=total_count)

@auth_bp.route('/api/users/<user_id>/roles', methods=['PUT'])
def update_roles_api(user_id):
    """
    API to update user roles (admin only).
    """
    if not is_authenticated() or not has_role(ROLE_ADMIN):
        return jsonify({
            'success': False,
            'error': 'Access denied. Admin privileges required.'
        }), 403
    
    # Get roles from request
    data = request.get_json()
    roles = data.get('roles', [])
    
    # Update roles
    success, error_message = update_user_roles(user_id, roles)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({
            'success': False,
            'error': error_message
        }), 400

@auth_bp.route('/initialize-roles')
def initialize_roles_route():
    """
    Initialize default roles in the database (admin only).
    """
    if not is_authenticated() or not has_role(ROLE_ADMIN):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Initialize roles
    success = initialize_roles()
    
    if success:
        flash('Roles initialized successfully', 'success')
    else:
        flash('Failed to initialize roles', 'error')
    
    return redirect(url_for('auth.user_list'))

# API endpoint to check if user is authenticated
@auth_bp.route('/api/check-auth')
def check_auth_api():
    """
    API to check if user is authenticated.
    """
    if is_authenticated():
        user = get_current_user()
        roles = get_user_roles()
        
        return jsonify({
            'authenticated': True,
            'user': {
                'id': user.get('id'),
                'email': user.get('email'),
                'full_name': user.get('full_name', '')
            },
            'roles': roles
        })
    else:
        return jsonify({
            'authenticated': False
        })