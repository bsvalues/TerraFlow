"""
Benton County Data Hub Sync Service

This module provides functionality for synchronizing data between
production databases and the training environment through the Data Hub API Gateway.
It also includes property export functionality for executing the ExportPropertyAccess
stored procedure against SQL Server.
"""

# Basic imports that don't cause circular dependencies
import os
import logging
from flask import Blueprint

# Create logger
logger = logging.getLogger(__name__)

# Create the blueprints - these will be registered by the app
sync_bp = Blueprint('sync', __name__, url_prefix='/sync')

def create_routes():
    """Create routes for sync_bp. This must be called before registering the blueprint."""
    # Local import to avoid circular dependencies
    from sync_service.routes_module import register_sync_routes
    
    # Register the routes with the blueprint
    register_sync_routes(sync_bp)
    
def register_blueprints(app):
    """
    Register all blueprints with the Flask app.
    This is called by the main app to initialize the module.
    """
    try:
        # Create routes before registering the blueprints
        create_routes()
        
        # Import verification blueprint
        from sync_service.verification_routes import verification_bp
        
        # Register the blueprints
        app.register_blueprint(sync_bp)
        app.register_blueprint(verification_bp)
        
        return True
    except Exception as e:
        logger.error(f"Error registering sync service blueprints: {str(e)}")
        return False