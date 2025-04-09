"""
Benton County Data Hub Sync Service

This module provides functionality for synchronizing data between
production databases and the training environment through the Data Hub API Gateway.
"""

from flask import Blueprint

sync_bp = Blueprint('sync', __name__, url_prefix='/sync')

from sync_service import routes, models, config