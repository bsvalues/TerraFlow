"""
Flask Routes for TerraFusion Sync Service.

This module provides Flask routes for integrating the TerraFusion Sync Service
with the main application.
"""

import os
import logging
from typing import Dict, List, Any, Optional

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, g, abort
from flask.views import MethodView
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound, BadRequest

from sync_service.terra_fusion.flask_integration import active_services
from sync_service.terra_fusion.sync_service import TerraFusionSyncService
from app import db

# Initialize logging
logger = logging.getLogger(__name__)

# Create Blueprint
terra_fusion_routes = Blueprint('terra_fusion_ui', __name__, url_prefix='/sync/terra_fusion')


def _get_sync_service(job_id: str) -> TerraFusionSyncService:
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
        abort(404, f"Sync job {job_id} not found")
    return active_services[job_id]


@terra_fusion_routes.route('/')
@terra_fusion_routes.route('/dashboard')
@login_required
def dashboard():
    """Render the TerraFusion Sync dashboard."""
    # Get active sync jobs
    active_jobs = []
    for job_id, service in active_services.items():
        status = service.get_sync_status()
        job_info = {
            'job_id': job_id,
            'status': status.get('status', 'unknown'),
            'start_time': status.get('start_time', ''),
            'source_db': service.source_connection_string.split('@')[-1] if service.source_connection_string else 'unknown',
            'target_db': service.target_connection_string.split('@')[-1] if service.target_connection_string else 'unknown',
            'stats': status.get('stats', {})
        }
        active_jobs.append(job_info)
    
    # Count conflicts
    pending_conflicts = 0
    for job_id, service in active_services.items():
        conflicts = service.get_conflicts(status='pending')
        pending_conflicts += len(conflicts)
    
    # Count total records processed
    total_synced_records = 0
    for job_id, service in active_services.items():
        status = service.get_sync_status()
        total_synced_records += status.get('stats', {}).get('processed_records', 0)
    
    # Get health status
    service_health = TerraFusionSyncService().health_check()
    
    # Get available tables (for new sync modal)
    available_tables = []
    if active_services:
        # Use first service as example
        service = list(active_services.values())[0]
        try:
            tables = service._identify_project_tables()
            available_tables = [t['name'] for t in tables]
        except Exception:
            pass
    
    return render_template(
        'sync/terra_fusion/dashboard.html',
        active_jobs=active_jobs,
        pending_conflicts=pending_conflicts,
        total_synced_records=total_synced_records,
        service_health=service_health,
        available_tables=available_tables
    )


@terra_fusion_routes.route('/job/<job_id>')
@login_required
def job_details(job_id):
    """Render the job details page."""
    try:
        service = _get_sync_service(job_id)
        status = service.get_sync_status()
        
        # Calculate progress percentage
        total_records = status.get('stats', {}).get('total_records', 0)
        processed_records = status.get('stats', {}).get('processed_records', 0)
        progress_percentage = int((processed_records / total_records * 100) if total_records > 0 else 0)
        
        # Get status color and icon
        status_map = {
            'pending': {'color': 'secondary', 'icon': 'clock'},
            'running': {'color': 'primary', 'icon': 'sync'},
            'resuming': {'color': 'info', 'icon': 'play'},
            'completed': {'color': 'success', 'icon': 'check-circle'},
            'failed': {'color': 'danger', 'icon': 'times-circle'},
            'stopped': {'color': 'warning', 'icon': 'stop-circle'},
            'interrupted': {'color': 'warning', 'icon': 'exclamation-circle'}
        }
        status_info = status_map.get(status.get('status', 'unknown'), {'color': 'info', 'icon': 'question-circle'})
        
        # Get table progress information
        table_progress = []
        for table in status.get('tables', []):
            table_name = table.get('name', '')
            
            # Get table-specific stats if available
            table_stats = status.get('table_stats', {}).get(table_name, {})
            
            # Default values
            table_info = {
                'name': table_name,
                'status': 'pending',
                'total_records': 0,
                'processed_records': 0,
                'conflict_count': 0,
                'error_count': 0,
                'progress_percentage': 0
            }
            
            # Update with actual stats if available
            if table_stats:
                table_info.update({
                    'status': table_stats.get('status', 'pending'),
                    'total_records': table_stats.get('total_records', 0),
                    'processed_records': table_stats.get('processed_records', 0),
                    'conflict_count': table_stats.get('conflict_count', 0),
                    'error_count': table_stats.get('error_count', 0)
                })
                
                # Calculate progress percentage
                if table_info['total_records'] > 0:
                    table_info['progress_percentage'] = int(
                        (table_info['processed_records'] / table_info['total_records'] * 100)
                    )
            
            table_progress.append(table_info)
        
        # Get conflicts
        conflicts = service.get_conflicts(status='pending')
        
        return render_template(
            'sync/terra_fusion/job_details.html',
            job_id=job_id,
            status=status,
            progress_percentage=progress_percentage,
            status_color=status_info['color'],
            status_icon=status_info['icon'],
            table_progress=table_progress,
            conflicts=conflicts
        )
        
    except NotFound as e:
        abort(404, str(e))
    except Exception as e:
        logger.error(f"Error getting job details: {str(e)}")
        abort(500, f"Error getting job details: {str(e)}")


@terra_fusion_routes.route('/conflicts/<job_id>')
@login_required
def conflicts_page(job_id):
    """Render the conflicts page."""
    try:
        service = _get_sync_service(job_id)
        
        # Get conflicts with optional status filter
        status = request.args.get('status')
        table_name = request.args.get('table_name')
        conflicts = service.get_conflicts(status=status, table_name=table_name)
        
        # Count conflicts by status
        pending_conflicts = len(service.get_conflicts(status='pending'))
        resolved_conflicts = len(service.get_conflicts(status='resolved'))
        
        # Get list of tables with conflicts
        all_conflicts = service.get_conflicts()
        table_names = sorted(list(set([c['table_name'] for c in all_conflicts])))
        
        # Count conflicts by table
        conflicts_by_table = []
        for table in table_names:
            count = len([c for c in all_conflicts if c['table_name'] == table])
            conflicts_by_table.append(count)
        
        return render_template(
            'sync/terra_fusion/conflicts.html',
            job_id=job_id,
            conflicts=conflicts,
            pending_conflicts=pending_conflicts,
            resolved_conflicts=resolved_conflicts,
            table_names=table_names,
            conflicts_by_table=conflicts_by_table
        )
        
    except NotFound as e:
        abort(404, str(e))
    except Exception as e:
        logger.error(f"Error getting conflicts: {str(e)}")
        abort(500, f"Error getting conflicts: {str(e)}")


def register_blueprint(app):
    """
    Register the TerraFusion UI blueprint with a Flask app.
    
    Args:
        app: Flask application
    """
    app.register_blueprint(terra_fusion_routes)
    logger.info("Registered TerraFusion UI routes at /sync/terra_fusion")