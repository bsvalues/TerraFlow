"""
Benton County Data Hub Sync Service

This module provides functionality for synchronizing data between
production databases and the training environment through the Data Hub API Gateway.
It also includes property export functionality for executing the ExportPropertyAccess
stored procedure against SQL Server.

Scheduled synchronization is supported through the APScheduler library,
allowing automatic execution of sync jobs at regular intervals or according to
cron expressions.
"""
import logging
import threading

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
    
    # Initialize scheduler (threading.Thread is used to avoid blocking the main thread)
    def init_scheduler_in_thread():
        try:
            from sync_service.app_context import with_app_context
            from sync_service.scheduler import init_scheduler
            
            # Make sure we run the scheduler in an app context
            @with_app_context
            def initialize_with_context():
                scheduler = init_scheduler()
                logger.info(f"Scheduler initialized with {len(scheduler.get_jobs())} jobs")
                return scheduler
            
            # Run the initialization with context
            scheduler = initialize_with_context()
        except Exception as e:
            logger.error(f"Error initializing scheduler: {str(e)}")
    
    # Start the scheduler in a separate thread after a short delay
    # to ensure the database is fully initialized
    thread = threading.Timer(5.0, init_scheduler_in_thread)
    thread.daemon = True
    thread.start()
    
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