"""
API Package for Benton County GIS System

This package provides a comprehensive API for integrating with the
Benton County GIS system, including database access, file operations,
and GIS functionality.
"""

from api.endpoints import register_api_endpoints
from api.database import db_api
from api.connection_manager import connection_manager

def init_api(app):
    """
    Initialize API components with Flask app
    
    Args:
        app: Flask application instance
    """
    # Register API endpoints
    register_api_endpoints(app)
    
    # Set up API-specific configuration
    app.config.setdefault('API_KEYS', [])
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        from flask import jsonify, request
        
        # Check if this is an API request
        if request.path.startswith('/api/'):
            return jsonify({"error": "Not found"}), 404
        
        # Otherwise, let Flask handle it normally
        return error
    
    @app.errorhandler(500)
    def server_error(error):
        from flask import jsonify, request
        
        # Check if this is an API request
        if request.path.startswith('/api/'):
            return jsonify({"error": "Internal server error"}), 500
        
        # Otherwise, let Flask handle it normally
        return error