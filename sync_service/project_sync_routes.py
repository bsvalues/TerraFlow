"""
Project Sync Service Routes

This module provides Flask routes for the enhanced DatabaseProjectSyncService,
allowing users to configure, initiate, and monitor database project synchronization.
"""
import datetime
import json
from flask import (
    Blueprint, render_template, request, jsonify, 
    session, flash, redirect, url_for, current_app
)

from app import db
from sync_service.models import (
    SyncJob, TableConfiguration, FieldConfiguration, 
    SyncLog, SyncConflict, GlobalSetting
)
from sync_service.database_project_sync import DatabaseProjectSyncService
from auth import login_required, permission_required, role_required

# Create the blueprint
project_sync_bp = Blueprint('project_sync', __name__, url_prefix='/project-sync')

# Active sync services
active_syncs = {}

@project_sync_bp.route('/')
@login_required
@role_required('administrator')
def dashboard():
    """Project sync dashboard."""
    # Get recent project sync jobs
    recent_jobs = SyncJob.query.filter_by(
        job_type='project_sync'
    ).order_by(SyncJob.created_at.desc()).limit(10).all()
    
    # Get project tables configuration
    project_tables = TableConfiguration.query.filter_by(
        sync_enabled=True,
        config_type='project'
    ).all()
    
    # Count pending conflicts
    pending_conflicts = SyncConflict.query.filter_by(
        resolution_status='pending'
    ).count()
    
    # Calculate some statistics
    total_jobs = SyncJob.query.filter_by(job_type='project_sync').count()
    successful_jobs = SyncJob.query.filter_by(job_type='project_sync', status='completed').count()
    failed_jobs = SyncJob.query.filter_by(job_type='project_sync', status='failed').count()
    
    # Calculate success rate
    success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
    
    # Get global settings
    global_settings = GlobalSetting.query.first()
    
    # Current time for calculating "time ago"
    now = datetime.datetime.utcnow()
    
    return render_template(
        'sync/project_sync_dashboard.html',
        recent_jobs=recent_jobs,
        project_tables=project_tables,
        pending_conflicts=pending_conflicts,
        total_jobs=total_jobs,
        successful_jobs=successful_jobs,
        failed_jobs=failed_jobs,
        success_rate=success_rate,
        global_settings=global_settings,
        now=now
    )

@project_sync_bp.route('/jobs')
@login_required
@role_required('administrator')
def job_list():
    """List all project sync jobs."""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get filter parameters
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Base query
    query = SyncJob.query.filter_by(job_type='project_sync')
    
    # Apply filters
    if status:
        query = query.filter_by(status=status)
    
    if date_from:
        try:
            from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(SyncJob.created_at >= from_date)
        except ValueError:
            flash('Invalid date format for "From Date"', 'error')
    
    if date_to:
        try:
            to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + datetime.timedelta(days=1)  # Include the entire day
            query = query.filter(SyncJob.created_at <= to_date)
        except ValueError:
            flash('Invalid date format for "To Date"', 'error')
    
    # Execute query with pagination
    jobs_pagination = query.order_by(SyncJob.created_at.desc()).paginate(
        page=page, per_page=per_page
    )
    
    return render_template(
        'sync/project_sync_jobs.html',
        jobs=jobs_pagination.items,
        pagination=jobs_pagination,
        status=status,
        date_from=date_from,
        date_to=date_to
    )

@project_sync_bp.route('/job/<job_id>')
@login_required
@role_required('administrator')
def job_details(job_id):
    """View details of a specific sync job."""
    job = SyncJob.query.filter_by(job_id=job_id).first_or_404()
    
    # Get logs for this job
    logs = SyncLog.query.filter_by(job_id=job_id).order_by(SyncLog.timestamp.asc()).all()
    
    # Get conflicts for this job
    conflicts = SyncConflict.query.filter_by(job_id=job_id).all()
    
    # Check if this job is active
    is_active = job_id in active_syncs and active_syncs[job_id].sync_in_progress
    
    # Get real-time status if available
    status = None
    if is_active:
        status = active_syncs[job_id].get_status()
    
    return render_template(
        'sync/project_sync_job_details.html',
        job=job,
        logs=logs,
        conflicts=conflicts,
        is_active=is_active,
        status=status
    )

@project_sync_bp.route('/tables')
@login_required
@role_required('administrator')
def table_config():
    """Configure tables for project synchronization."""
    # Get all table configurations
    tables = TableConfiguration.query.filter_by(
        config_type='project'
    ).order_by(TableConfiguration.name).all()
    
    return render_template(
        'sync/project_sync_tables.html',
        tables=tables
    )

@project_sync_bp.route('/tables/add', methods=['GET', 'POST'])
@login_required
@role_required('administrator')
def add_table():
    """Add a new table configuration."""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        sync_enabled = 'sync_enabled' in request.form
        
        # Check if table already exists
        existing = TableConfiguration.query.filter_by(name=name).first()
        if existing:
            flash(f'Table configuration for {name} already exists', 'error')
            return redirect(url_for('project_sync.table_config'))
        
        # Create new table configuration
        table = TableConfiguration(
            name=name,
            description=description,
            sync_enabled=sync_enabled,
            config_type='project'
        )
        db.session.add(table)
        db.session.commit()
        
        flash(f'Table configuration for {name} added successfully', 'success')
        return redirect(url_for('project_sync.edit_table', table_id=table.id))
    
    return render_template('sync/project_sync_add_table.html')

@project_sync_bp.route('/tables/edit/<int:table_id>', methods=['GET', 'POST'])
@login_required
@role_required('administrator')
def edit_table(table_id):
    """Edit a table configuration."""
    table = TableConfiguration.query.get_or_404(table_id)
    
    if request.method == 'POST':
        table.name = request.form.get('name')
        table.description = request.form.get('description')
        table.sync_enabled = 'sync_enabled' in request.form
        
        db.session.commit()
        flash(f'Table configuration for {table.name} updated successfully', 'success')
        return redirect(url_for('project_sync.table_config'))
    
    # Get fields for this table
    fields = FieldConfiguration.query.filter_by(
        table_id=table_id
    ).order_by(FieldConfiguration.name).all()
    
    return render_template(
        'sync/project_sync_edit_table.html',
        table=table,
        fields=fields
    )

@project_sync_bp.route('/tables/delete/<int:table_id>', methods=['POST'])
@login_required
@role_required('administrator')
def delete_table(table_id):
    """Delete a table configuration."""
    table = TableConfiguration.query.get_or_404(table_id)
    
    db.session.delete(table)
    db.session.commit()
    
    flash(f'Table configuration for {table.name} deleted successfully', 'success')
    return redirect(url_for('project_sync.table_config'))

@project_sync_bp.route('/fields/add/<int:table_id>', methods=['POST'])
@login_required
@role_required('administrator')
def add_field(table_id):
    """Add a field configuration to a table."""
    table = TableConfiguration.query.get_or_404(table_id)
    
    name = request.form.get('name')
    description = request.form.get('description')
    sync_enabled = 'sync_enabled' in request.form
    is_pk = 'is_pk' in request.form
    
    # Check if field already exists
    existing = FieldConfiguration.query.filter_by(
        table_id=table_id, name=name
    ).first()
    
    if existing:
        flash(f'Field {name} already exists for table {table.name}', 'error')
    else:
        field = FieldConfiguration(
            table_id=table_id,
            name=name,
            description=description,
            sync_enabled=sync_enabled,
            is_primary_key=is_pk
        )
        db.session.add(field)
        db.session.commit()
        
        flash(f'Field {name} added successfully to table {table.name}', 'success')
    
    return redirect(url_for('project_sync.edit_table', table_id=table_id))

@project_sync_bp.route('/fields/delete/<int:field_id>', methods=['POST'])
@login_required
@role_required('administrator')
def delete_field(field_id):
    """Delete a field configuration."""
    field = FieldConfiguration.query.get_or_404(field_id)
    table_id = field.table_id
    
    db.session.delete(field)
    db.session.commit()
    
    flash(f'Field {field.name} deleted successfully', 'success')
    return redirect(url_for('project_sync.edit_table', table_id=table_id))

@project_sync_bp.route('/conflicts')
@login_required
@role_required('administrator')
def conflict_list():
    """List all sync conflicts."""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get filter parameters
    status = request.args.get('status', 'pending')
    table_name = request.args.get('table_name')
    
    # Base query
    query = SyncConflict.query
    
    # Apply filters
    if status:
        query = query.filter_by(resolution_status=status)
    
    if table_name:
        query = query.filter_by(table_name=table_name)
    
    # Execute query with pagination
    conflicts_pagination = query.order_by(SyncConflict.created_at.desc()).paginate(
        page=page, per_page=per_page
    )
    
    # Get unique table names for the filter dropdown
    table_names = db.session.query(SyncConflict.table_name).distinct().all()
    table_names = [t[0] for t in table_names]
    
    return render_template(
        'sync/project_sync_conflicts.html',
        conflicts=conflicts_pagination.items,
        pagination=conflicts_pagination,
        status=status,
        table_name=table_name,
        table_names=table_names
    )

@project_sync_bp.route('/conflicts/<int:conflict_id>', methods=['GET', 'POST'])
@login_required
@role_required('administrator')
def resolve_conflict(conflict_id):
    """View and resolve a specific conflict."""
    conflict = SyncConflict.query.get_or_404(conflict_id)
    
    if request.method == 'POST':
        resolution_type = request.form.get('resolution_type')
        resolution_notes = request.form.get('resolution_notes')
        
        if resolution_type == 'source_wins':
            resolved_data = conflict.source_data
        elif resolution_type == 'target_wins':
            resolved_data = conflict.target_data
        elif resolution_type == 'manual':
            # For manual resolution, the form will include all field values
            resolved_data = {}
            for field in conflict.source_data.keys():
                resolved_data[field] = request.form.get(f'field_{field}')
        else:
            flash('Invalid resolution type', 'error')
            return redirect(url_for('project_sync.resolve_conflict', conflict_id=conflict_id))
        
        # Update the conflict
        conflict.resolution_status = 'resolved'
        conflict.resolution_type = resolution_type
        conflict.resolved_by = session.get('user_id')
        conflict.resolved_at = datetime.datetime.utcnow()
        conflict.resolution_notes = resolution_notes
        conflict.resolved_data = resolved_data
        
        db.session.commit()
        
        # TODO: Apply the resolved data to the target database
        # This would require connecting to the database and updating the record
        
        flash('Conflict resolved successfully', 'success')
        return redirect(url_for('project_sync.conflict_list'))
    
    return render_template(
        'sync/project_sync_resolve_conflict.html',
        conflict=conflict
    )

@project_sync_bp.route('/run', methods=['GET', 'POST'])
@login_required
@role_required('administrator')
def run_sync():
    """Run a new project sync job."""
    if request.method == 'POST':
        source_connection = request.form.get('source_connection')
        target_connection = request.form.get('target_connection')
        conflict_strategy = request.form.get('conflict_strategy', 'source_wins')
        schema_validation = 'schema_validation' in request.form
        auto_migration = 'auto_migration' in request.form
        batch_size = int(request.form.get('batch_size', 1000))
        
        # Create and start the sync service
        sync_service = DatabaseProjectSyncService(
            source_connection_string=source_connection,
            target_connection_string=target_connection,
            user_id=session.get('user_id'),
            conflict_strategy=conflict_strategy,
            schema_validation=schema_validation,
            auto_migration=auto_migration,
            batch_size=batch_size
        )
        
        job_id = sync_service.start_sync(async_mode=True)
        
        # Store the sync service in active_syncs
        active_syncs[job_id] = sync_service
        
        flash(f'Project sync job started. Job ID: {job_id}', 'success')
        return redirect(url_for('project_sync.job_details', job_id=job_id))
    
    # Get available connections from global settings
    connections = []
    global_settings = GlobalSetting.query.first()
    
    if global_settings and global_settings.connection_strings:
        for name, conn in global_settings.connection_strings.items():
            # Mask password in connection string for display
            masked_conn = conn
            if 'password=' in masked_conn.lower():
                parts = masked_conn.split('password=')
                password_part = parts[1].split(';')[0] if ';' in parts[1] else parts[1]
                masked_conn = masked_conn.replace(f'password={password_part}', 'password=*****')
            
            connections.append({
                'name': name,
                'connection_string': masked_conn
            })
    
    return render_template(
        'sync/project_sync_run.html',
        connections=connections
    )

@project_sync_bp.route('/status/<job_id>')
@login_required
def job_status(job_id):
    """Get the current status of a sync job."""
    if job_id in active_syncs:
        return jsonify(active_syncs[job_id].get_status())
    
    # If not in active_syncs, return job info from database
    job = SyncJob.query.filter_by(job_id=job_id).first()
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    # Return basic job info
    return jsonify({
        'job_id': job.job_id,
        'status': job.status,
        'progress': {
            'records': {
                'total': job.total_records,
                'processed': job.processed_records,
                'errors': job.error_records
            }
        },
        'timing': {
            'start': job.start_time.isoformat() if job.start_time else None,
            'end': job.end_time.isoformat() if job.end_time else None,
            'duration': job.duration_seconds
        }
    })

@project_sync_bp.route('/cancel/<job_id>', methods=['POST'])
@login_required
@role_required('administrator')
def cancel_job(job_id):
    """Cancel a running sync job."""
    # Implementation would depend on how we handle cancellation
    # For now, we'll just mark the job as cancelled in the database
    
    job = SyncJob.query.filter_by(job_id=job_id).first()
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.status in ['pending', 'running']:
        job.status = 'cancelled'
        job.end_time = datetime.datetime.utcnow()
        
        if job.start_time:
            job.duration_seconds = int((job.end_time - job.start_time).total_seconds())
        
        db.session.commit()
        
        # If job is in active_syncs, we would need to signal the thread to stop
        # For now, just remove it from active_syncs
        if job_id in active_syncs:
            active_syncs.pop(job_id, None)
        
        flash(f'Job {job_id} has been cancelled', 'success')
    else:
        flash(f'Cannot cancel job {job_id} with status {job.status}', 'error')
    
    return redirect(url_for('project_sync.job_details', job_id=job_id))

# API endpoints for programmatic access

@project_sync_bp.route('/api/start-sync', methods=['POST'])
@login_required
@role_required('administrator')
def api_start_sync():
    """Start a project sync job via API."""
    data = request.get_json()
    
    source_connection = data.get('source_connection')
    target_connection = data.get('target_connection')
    conflict_strategy = data.get('conflict_strategy', 'source_wins')
    schema_validation = data.get('schema_validation', True)
    auto_migration = data.get('auto_migration', True)
    batch_size = int(data.get('batch_size', 1000))
    
    if not source_connection or not target_connection:
        return jsonify({
            'error': 'Source and target connection strings are required'
        }), 400
    
    # Create and start the sync service
    sync_service = DatabaseProjectSyncService(
        source_connection_string=source_connection,
        target_connection_string=target_connection,
        user_id=session.get('user_id'),
        conflict_strategy=conflict_strategy,
        schema_validation=schema_validation,
        auto_migration=auto_migration,
        batch_size=batch_size
    )
    
    job_id = sync_service.start_sync(async_mode=True)
    
    # Store the sync service in active_syncs
    active_syncs[job_id] = sync_service
    
    return jsonify({
        'job_id': job_id,
        'status': 'started',
        'message': "Project sync job started successfully."
    })

@project_sync_bp.route('/api/status/<job_id>')
@login_required
def api_job_status(job_id):
    """Get the current status of a sync job via API."""
    return job_status(job_id)

@project_sync_bp.route('/api/jobs')
@login_required
def api_jobs():
    """Get list of sync jobs via API."""
    # Get filter parameters
    status = request.args.get('status')
    limit = request.args.get('limit', 10, type=int)
    
    # Base query
    query = SyncJob.query.filter_by(job_type='project_sync')
    
    # Apply filters
    if status:
        query = query.filter_by(status=status)
    
    # Execute query
    jobs = query.order_by(SyncJob.created_at.desc()).limit(limit).all()
    
    # Convert to dictionary
    result = []
    for job in jobs:
        result.append({
            'job_id': job.job_id,
            'name': job.name,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'start_time': job.start_time.isoformat() if job.start_time else None,
            'end_time': job.end_time.isoformat() if job.end_time else None,
            'duration_seconds': job.duration_seconds,
            'total_records': job.total_records,
            'processed_records': job.processed_records,
            'error_records': job.error_records
        })
    
    return jsonify(result)

@project_sync_bp.route('/api/conflicts')
@login_required
def api_conflicts():
    """Get list of conflicts via API."""
    # Get filter parameters
    status = request.args.get('status', 'pending')
    table_name = request.args.get('table_name')
    limit = request.args.get('limit', 10, type=int)
    
    # Base query
    query = SyncConflict.query
    
    # Apply filters
    if status:
        query = query.filter_by(resolution_status=status)
    
    if table_name:
        query = query.filter_by(table_name=table_name)
    
    # Execute query
    conflicts = query.order_by(SyncConflict.created_at.desc()).limit(limit).all()
    
    # Convert to dictionary
    result = []
    for conflict in conflicts:
        result.append({
            'id': conflict.id,
            'job_id': conflict.job_id,
            'table_name': conflict.table_name,
            'record_id': conflict.record_id,
            'resolution_status': conflict.resolution_status,
            'created_at': conflict.created_at.isoformat()
        })
    
    return jsonify(result)

@project_sync_bp.route('/api/tables')
@login_required
def api_tables():
    """Get list of table configurations via API."""
    tables = TableConfiguration.query.filter_by(
        config_type='project'
    ).order_by(TableConfiguration.name).all()
    
    result = []
    for table in tables:
        result.append({
            'id': table.id,
            'name': table.name,
            'description': table.description,
            'sync_enabled': table.sync_enabled
        })
    
    return jsonify(result)

def register_project_sync_blueprint(app):
    """Register the project sync blueprint with the Flask app."""
    app.register_blueprint(project_sync_bp)
    return True