"""
Visualizations Package

This package provides visualization modules and routes for the TerraFlow application,
including real-time geographic data visualizations and dashboards.
"""

from flask import Blueprint

# Create a visualizations blueprint for registering with the main application
visualizations_bp = Blueprint('visualizations', __name__, url_prefix='/visualizations')

# Import route modules
from .dashboard_routes import dashboard_bp

# Register child blueprints
visualizations_bp.register_blueprint(dashboard_bp)

# Function for registering the visualizations blueprint with a Flask app
def register_blueprint(app):
    """Register visualizations blueprint with the main Flask app.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(visualizations_bp)
    return True