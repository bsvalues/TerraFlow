"""
Authentication API Module

This module provides API endpoints for authentication and token management.
It supports both session-based and token-based authentication for the API.
"""

from flask import Blueprint, request, jsonify, current_app, session
import logging
import time
import json
import secrets
import datetime
from functools import wraps
from typing import Dict, Any, List

from auth import login_required, is_authenticated, authenticate_user

# Create blueprint
auth_api = Blueprint('auth_api', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('auth_api')

# In-memory token storage
# In production, this should be in a database
api_tokens = {}

# Token expiration in seconds (24 hours)
TOKEN_EXPIRATION = 24 * 60 * 60


def validate_token(token):
    """Validate an API token"""
    if token not in api_tokens:
        return False
    
    token_data = api_tokens[token]
    if token_data['expires_at'] < time.time():
        # Token expired, remove it
        del api_tokens[token]
        return False
    
    return token_data


def get_token_from_request():
    """Extract token from request (header or query param)"""
    # Check Authorization header first
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # Then check query parameter
    return request.args.get('api_token')


def token_required(f):
    """Decorator to require a valid token for an endpoint"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return jsonify({
                "status": "error",
                "message": "Missing API token"
            }), 401
        
        token_data = validate_token(token)
        if not token_data:
            return jsonify({
                "status": "error",
                "message": "Invalid or expired API token"
            }), 401
        
        # Set the user from the token
        request.token_data = token_data
        
        return f(*args, **kwargs)
    return decorated_function


@auth_api.route('/token', methods=['POST'])
def create_token():
    """Create a new API token using username and password"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "Missing request body"
        }), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "Missing username or password"
        }), 400
    
    # Authenticate the user
    if not authenticate_user(username, password):
        return jsonify({
            "status": "error",
            "message": "Invalid credentials"
        }), 401
    
    # Get the user info
    from app import db
    from models import User
    
    user = User.query.filter_by(username=username).first()
    if not user:
        # Create user if doesn't exist (for LDAP users)
        user = User(username=username, email=f"{username}@co.benton.wa.us")
        db.session.add(user)
        db.session.commit()
    
    # Generate a token
    token = secrets.token_hex(32)
    
    # Store token with user info
    expires_at = time.time() + TOKEN_EXPIRATION
    api_tokens[token] = {
        'user_id': user.id,
        'username': user.username,
        'created_at': time.time(),
        'expires_at': expires_at
    }
    
    return jsonify({
        "status": "success",
        "token": token,
        "expires_at": datetime.datetime.fromtimestamp(expires_at).isoformat(),
        "user": {
            "id": user.id,
            "username": user.username
        }
    })


@auth_api.route('/token/refresh', methods=['POST'])
@token_required
def refresh_token():
    """Refresh an existing API token"""
    token = get_token_from_request()
    token_data = request.token_data
    
    # Update expiration time
    token_data['expires_at'] = time.time() + TOKEN_EXPIRATION
    api_tokens[token] = token_data
    
    return jsonify({
        "status": "success",
        "token": token,
        "expires_at": datetime.datetime.fromtimestamp(token_data['expires_at']).isoformat(),
        "user": {
            "id": token_data['user_id'],
            "username": token_data['username']
        }
    })


@auth_api.route('/token/revoke', methods=['POST'])
@token_required
def revoke_token():
    """Revoke an API token"""
    token = get_token_from_request()
    
    # Delete the token
    if token in api_tokens:
        del api_tokens[token]
    
    return jsonify({
        "status": "success",
        "message": "Token revoked successfully"
    })


@auth_api.route('/me', methods=['GET'])
@token_required
def get_user_info():
    """Get information about the authenticated user"""
    token_data = request.token_data
    
    # Get the user from the database
    from app import db
    from models import User
    
    user = User.query.get(token_data['user_id'])
    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404
    
    return jsonify({
        "status": "success",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department
        }
    })