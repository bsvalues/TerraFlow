"""
GeoAssessmentPro API Package

This package contains API endpoints for the GeoAssessmentPro application.
"""

import logging

logger = logging.getLogger(__name__)

def init_api(app):
    """Initialize the API package"""
    logger.info("Initializing API package")
    
    # Register API modules and blueprints
    try:
        from api.assessment import assessment_bp
        app.register_blueprint(assessment_bp)
        logger.info("Assessment API registered")
    except Exception as e:
        logger.error(f"Error registering Assessment API: {str(e)}")
    
    # Add more API registrations here
    
    return True