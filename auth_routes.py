"""
Authentication Routes Module

This module provides Flask routes for user authentication, registration,
and user management using Supabase Auth.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_required

from supabase_auth import (
    login_user, logout_user, signup_user, reset_password_request, reset_password,
    is_authenticated, has_role, get_current_user, list_users, update_user_roles,
    initialize_roles, ALL_ROLES
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the authentication blueprint
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
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please enter both email and password', 'danger')
            return render_template('login.html')
        
        # Attempt to login the user
        success, error_message = login_user(email, password)
        
        if success:
            flash('Login successful', 'success')
            # Redirect to requested page or default to home
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash(f'Login failed: {error_message}', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """
    Log the user out and redirect to login page.
    """
    logout_user()
    flash('You have been logged out', 'info')
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
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        department = request.form.get('department')
        
        # Validate form data
        if not email or not password or not confirm_password:
            flash('Please fill in all required fields', 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Prepare user data
        user_data = {
            'full_name': full_name,
            'department': department,
            'roles': ['viewer']  # Default role for new users
        }
        
        # Attempt to register the user
        success, error_message, user_info = signup_user(email, password, user_data)
        
        if success:
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(f'Registration failed: {error_message}', 'danger')
    
    return render_template('register.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request_route():
    """
    Password reset request page.
    
    GET: Display reset password form
    POST: Process reset password request
    """
    # If user is already logged in, redirect to home
    if is_authenticated():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Please enter your email address', 'danger')
            return render_template('reset_password_request.html')
        
        # Send password reset email
        success, error_message = reset_password_request(email)
        
        if success:
            flash('Password reset link has been sent to your email', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(f'Password reset request failed: {error_message}', 'danger')
    
    return render_template('reset_password_request.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_route(token):
    """
    Password reset confirmation page.
    
    GET: Display reset password confirmation form
    POST: Process password reset
    """
    # If user is already logged in, redirect to home
    if is_authenticated():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or not confirm_password:
            flash('Please fill in all fields', 'danger')
            return render_template('reset_password.html', token=token)
            
        if new_password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('reset_password.html', token=token)
        
        # Process password reset
        success, error_message = reset_password(token, new_password)
        
        if success:
            flash('Your password has been reset successfully. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(f'Password reset failed: {error_message}', 'danger')
            return render_template('reset_password.html', token=token)
    
    return render_template('reset_password.html', token=token)

@auth_bp.route('/profile')
@login_required
def profile():
    """
    User profile page.
    """
    user = get_current_user()
    
    return render_template('profile.html', user=user)

@auth_bp.route('/users')
def user_list():
    """
    User management page (admin only).
    """
    if not is_authenticated() or not has_role('admin'):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    users, total_count = list_users(page, per_page)
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template(
        'user_list.html', 
        users=users, 
        page=page, 
        per_page=per_page, 
        total_pages=total_pages,
        total_count=total_count,
        all_roles=ALL_ROLES
    )

@auth_bp.route('/users/<user_id>/roles', methods=['POST'])
def update_roles_api(user_id):
    """
    API to update user roles (admin only).
    """
    if not is_authenticated() or not has_role('admin'):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    
    data = request.json
    roles = data.get('roles', [])
    
    success, error_message = update_user_roles(user_id, roles)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error_message}), 400

@auth_bp.route('/initialize-roles')
def initialize_roles_route():
    """
    Initialize default roles in the database (admin only).
    """
    if not is_authenticated() or not has_role('admin'):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    success = initialize_roles()
    
    if success:
        flash('Roles and permissions initialized successfully', 'success')
    else:
        flash('Failed to initialize roles and permissions', 'danger')
    
    return redirect(url_for('auth.user_list'))

@auth_bp.route('/check-auth')
def check_auth_api():
    """
    API to check if user is authenticated.
    """
    if is_authenticated():
        return jsonify({
            'authenticated': True,
            'user': get_current_user()
        })
    else:
        return jsonify({
            'authenticated': False
        })