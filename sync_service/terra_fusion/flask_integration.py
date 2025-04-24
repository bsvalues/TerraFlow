"""
Flask Integration for TerraFusion Sync Service.

This module provides integration between the TerraFusion Sync Service and Flask,
allowing the service to be used within a Flask application.
"""

import os
import logging
import json
import datetime
from typing import Dict, List, Any, Optional, Union

from flask import Blueprint, request, jsonify, current_app, g, abort, url_for
from flask.views import MethodView
from sqlalchemy import create_engine
from werkzeug.exceptions import NotFound, BadRequest

from sync_service.terra_fusion.sync_service import TerraFusionSyncService
from sync_service.terra_fusion.change_detector import ChangeDetector
from sync_service.terra_fusion.transformer import Transformer
from sync_service.terra_fusion.validator import Validator
from sync_service.terra_fusion.orchestrator import SelfHealingOrchestrator
from sync_service.terra_fusion.conflict_resolver import ConflictResolver
from sync_service.terra_fusion.audit_system import AuditSystem

# Initialize logging
logger = logging.getLogger(__name__)

# Create Blueprint
terra_fusion_bp = Blueprint('terra_fusion', __name__, url_prefix='/api/sync')

# Active sync services
active_services: Dict[str, TerraFusionSyncService] = {}


def get_sync_service(job_id: str) -> TerraFusionSyncService:
    """
    Get an active sync service by job ID.
    
    Args:
        job_id: ID of the sync job
        
    Returns:
        TerraFusionSyncService instance
    
    Raises:
        NotFound: If job ID not found
    """
    if job_id not in active_services:
        raise NotFound(f"Sync job {job_id} not found")
    return active_services[job_id]


def serialize_datetime(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# API Routes
@terra_fusion_bp.route('/full', methods=['POST'])
def start_full_sync():
    """Start a full synchronization of all tables."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Extract request parameters
        source_connection = data.get('source_connection')
        target_connection = data.get('target_connection')
        user_id = data.get('user_id')
        config = data.get('config')
        
        if not source_connection or not target_connection:
            return jsonify({'error': 'Source and target connections are required'}), 400
            
        # Create a new sync service
        service = TerraFusionSyncService(
            source_connection_string=source_connection,
            target_connection_string=target_connection,
            user_id=user_id,
            config=config
        )
        
        # Register the service
        job_id = service.job_id
        active_services[job_id] = service
        
        # Start the sync
        service.start_full_sync()
        
        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': f"Full sync started with job ID: {job_id}"
        })
        
    except Exception as e:
        logger.error(f"Error starting full sync: {str(e)}")
        return jsonify({'error': f"Error starting sync: {str(e)}"}), 500


@terra_fusion_bp.route('/incremental', methods=['POST'])
def start_incremental_sync():
    """Start an incremental synchronization of specified tables."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Extract request parameters
        source_connection = data.get('source_connection')
        target_connection = data.get('target_connection')
        user_id = data.get('user_id')
        tables = data.get('tables')
        config = data.get('config')
        
        if not source_connection or not target_connection:
            return jsonify({'error': 'Source and target connections are required'}), 400
            
        # Create a new sync service
        service = TerraFusionSyncService(
            source_connection_string=source_connection,
            target_connection_string=target_connection,
            user_id=user_id,
            config=config
        )
        
        # Register the service
        job_id = service.job_id
        active_services[job_id] = service
        
        # Start the sync
        service.start_incremental_sync(tables=tables)
        
        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': f"Incremental sync started with job ID: {job_id}"
        })
        
    except Exception as e:
        logger.error(f"Error starting incremental sync: {str(e)}")
        return jsonify({'error': f"Error starting sync: {str(e)}"}), 500


@terra_fusion_bp.route('/status/<job_id>', methods=['GET'])
def get_sync_status(job_id):
    """Get the status of a synchronization job."""
    try:
        service = get_sync_service(job_id)
        status = service.get_sync_status()
        return jsonify(status)
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        return jsonify({'error': f"Error getting status: {str(e)}"}), 500


@terra_fusion_bp.route('/stop/<job_id>', methods=['POST'])
def stop_sync(job_id):
    """Stop an ongoing synchronization job."""
    try:
        service = get_sync_service(job_id)
        stopped = service.stop_sync()
        
        if stopped:
            return jsonify({
                'job_id': job_id,
                'status': 'stopped',
                'message': f"Sync job {job_id} stopped successfully"
            })
        else:
            return jsonify({
                'job_id': job_id,
                'status': 'error',
                'message': f"Failed to stop sync job {job_id}"
            }), 500
            
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error stopping sync: {str(e)}")
        return jsonify({'error': f"Error stopping sync: {str(e)}"}), 500


@terra_fusion_bp.route('/resume/<job_id>', methods=['POST'])
def resume_sync(job_id):
    """Resume a previously interrupted sync job."""
    try:
        service = get_sync_service(job_id)
        resumed = service.resume_sync()
        
        if resumed:
            return jsonify({
                'job_id': job_id,
                'status': 'resuming',
                'message': f"Resuming sync job {job_id}"
            })
        else:
            return jsonify({
                'job_id': job_id,
                'status': 'error',
                'message': f"Failed to resume sync job {job_id}"
            }), 500
            
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error resuming sync: {str(e)}")
        return jsonify({'error': f"Error resuming sync: {str(e)}"}), 500


@terra_fusion_bp.route('/conflicts/<job_id>', methods=['GET'])
def get_conflicts(job_id):
    """Get conflicts for a sync job."""
    try:
        service = get_sync_service(job_id)
        
        # Extract query parameters
        table_name = request.args.get('table_name')
        status = request.args.get('status')
        
        conflicts = service.get_conflicts(table_name=table_name, status=status)
        return jsonify(conflicts)
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting conflicts: {str(e)}")
        return jsonify({'error': f"Error getting conflicts: {str(e)}"}), 500


@terra_fusion_bp.route('/conflicts/<job_id>/<conflict_id>/resolve', methods=['POST'])
def resolve_conflict(job_id, conflict_id):
    """Resolve a specific conflict."""
    try:
        service = get_sync_service(job_id)
        data = request.get_json() or {}
        
        resolved = service.resolve_conflict(
            conflict_id=conflict_id,
            strategy=data.get('strategy')
        )
        
        if resolved:
            return jsonify({
                'job_id': job_id,
                'status': 'success',
                'message': f"Conflict {conflict_id} resolved successfully"
            })
        else:
            return jsonify({
                'job_id': job_id,
                'status': 'error',
                'message': f"Failed to resolve conflict {conflict_id}"
            }), 500
            
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error resolving conflict: {str(e)}")
        return jsonify({'error': f"Error resolving conflict: {str(e)}"}), 500


@terra_fusion_bp.route('/conflicts/<job_id>/resolve-all', methods=['POST'])
def resolve_all_conflicts(job_id):
    """Resolve all pending conflicts."""
    try:
        service = get_sync_service(job_id)
        data = request.get_json() or {}
        
        count = service.resolve_all_conflicts(strategy=data.get('strategy'))
        
        return jsonify({
            'job_id': job_id,
            'status': 'success',
            'message': f"Resolved {count} conflicts"
        })
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error resolving conflicts: {str(e)}")
        return jsonify({'error': f"Error resolving conflicts: {str(e)}"}), 500


@terra_fusion_bp.route('/audit/<job_id>', methods=['GET'])
def get_audit_events(job_id):
    """Get audit events for a sync job."""
    try:
        service = get_sync_service(job_id)
        
        # Extract query parameters
        event_type = request.args.get('event_type')
        table_name = request.args.get('table_name')
        limit = int(request.args.get('limit', 1000))
        offset = int(request.args.get('offset', 0))
        
        events = service.get_audit_events(
            event_type=event_type,
            table_name=table_name,
            limit=limit,
            offset=offset
        )
        return jsonify(events)
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting audit events: {str(e)}")
        return jsonify({'error': f"Error getting audit events: {str(e)}"}), 500


@terra_fusion_bp.route('/audit/<job_id>/report', methods=['GET'])
def get_audit_report(job_id):
    """Generate an audit report for a sync job."""
    try:
        service = get_sync_service(job_id)
        report = service.get_audit_report()
        return jsonify(report)
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error generating audit report: {str(e)}")
        return jsonify({'error': f"Error generating audit report: {str(e)}"}), 500


@terra_fusion_bp.route('/validate/<job_id>/<table_name>', methods=['POST'])
def validate_schema(job_id, table_name):
    """Validate schema compatibility for a table."""
    try:
        service = get_sync_service(job_id)
        is_compatible, issues = service.validate_schema_compatibility(table_name)
        
        return jsonify({
            'table_name': table_name,
            'is_compatible': is_compatible,
            'issues': issues
        })
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error validating schema: {str(e)}")
        return jsonify({'error': f"Error validating schema: {str(e)}"}), 500


@terra_fusion_bp.route('/health', methods=['GET'])
def health_check():
    """Check the health of the sync service."""
    try:
        # Create a temporary service for health check
        service = TerraFusionSyncService()
        health = service.health_check()
        
        return jsonify(health)
        
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'source_db': 'error',
            'target_db': 'error',
            'components': {},
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 500


# Web UI Routes
@terra_fusion_bp.route('/ui/dashboard', methods=['GET'])
def dashboard():
    """Render the sync service dashboard."""
    # This would normally use a template, but we'll just return JSON for now
    active_jobs = [
        {
            'job_id': job_id,
            'status': service.get_sync_status().get('status', 'unknown'),
            'start_time': service.get_sync_status().get('start_time', ''),
            'source_db': service.source_connection_string.split('@')[-1] if service.source_connection_string else 'unknown',
            'target_db': service.target_connection_string.split('@')[-1] if service.target_connection_string else 'unknown'
        }
        for job_id, service in active_services.items()
    ]
    
    return jsonify({
        'active_jobs': active_jobs,
        'service_health': TerraFusionSyncService().health_check()
    })


@terra_fusion_bp.route('/ui/job/<job_id>', methods=['GET'])
def job_details(job_id):
    """Render the job details page."""
    try:
        service = get_sync_service(job_id)
        status = service.get_sync_status()
        
        return jsonify({
            'job_id': job_id,
            'status': status,
            'conflicts': len(service.get_conflicts(status='pending')),
            'source_db': service.source_connection_string.split('@')[-1] if service.source_connection_string else 'unknown',
            'target_db': service.target_connection_string.split('@')[-1] if service.target_connection_string else 'unknown'
        })
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting job details: {str(e)}")
        return jsonify({'error': f"Error getting job details: {str(e)}"}), 500


@terra_fusion_bp.route('/ui/conflicts/<job_id>', methods=['GET'])
def conflicts_page(job_id):
    """Render the conflicts page."""
    try:
        service = get_sync_service(job_id)
        conflicts = service.get_conflicts()
        
        return jsonify({
            'job_id': job_id,
            'conflicts': conflicts
        })
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting conflicts: {str(e)}")
        return jsonify({'error': f"Error getting conflicts: {str(e)}"}), 500


def register_blueprint(app):
    """
    Register the TerraFusion blueprint with a Flask app.
    
    Args:
        app: Flask application
    """
    app.register_blueprint(terra_fusion_bp)
    logger.info("Registered TerraFusion Sync Service blueprint at /api/sync")
    
    # Add JSON encoder for datetime
    app.json_encoder = lambda obj: json.dumps(obj, default=serialize_datetime)
    
    return app