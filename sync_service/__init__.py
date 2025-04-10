"""
Benton County Data Hub Sync Service

This module provides functionality for synchronizing data between
production databases and the training environment through the Data Hub API Gateway.
It also includes property export functionality for executing the ExportPropertyAccess
stored procedure against SQL Server.
"""

from flask import Blueprint

sync_bp = Blueprint('sync', __name__, url_prefix='/sync')

# Import verification blueprint for property export testing and verification
from sync_service.verification_routes import verification_bp

from sync_service import routes, models, config