"""
Routes for the Sync Service module.

These routes provide API endpoints for configuring, controlling, and monitoring
the synchronization process.
"""
from flask import render_template, request, jsonify, session, flash, redirect, url_for
from app import db
from sync_service.models import (
    SyncJob, TableConfiguration, FieldConfiguration, SyncLog, GlobalSetting
)
from sync_service.sync_engine import SyncEngine
from sync_service.bidirectional_sync import DataSynchronizer
from auth import login_required, permission_required, role_required

# Helper class for API response consistency
class DataSynchronizer:
    """Helper class for synchronization operations through the API."""
    
    @staticmethod
    def get_job_status(job_id):
        """Get the status of a job."""
        job = SyncJob.query.filter_by(job_id=job_id).first()
        if not job:
            return {"status": "not_found", "message": "Job not found"}
        
        return {
            "status": job.status,
            "job_id": job.job_id,
            "name": job.name,
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "total_records": job.total_records,
            "processed_records": job.processed_records,
            "error_records": job.error_records,
            "error_details": job.error_details,
            "progress": (job.processed_records / job.total_records * 100) if job.total_records > 0 else 0
        }
    
    @staticmethod
    def get_job_logs(job_id, level=None, limit=100):
        """Get logs for a job."""
        query = SyncLog.query.filter_by(job_id=job_id)
        
        if level:
            query = query.filter_by(level=level.upper())
            
        logs = query.order_by(SyncLog.created_at.desc()).limit(limit).all()
        
        return [{
            "timestamp": log.created_at.isoformat(),
            "level": log.level,
            "message": log.message,
            "component": log.component,
            "table_name": log.table_name,
            "record_count": log.record_count,
            "duration_ms": log.duration_ms
        } for log in logs]
    
    @staticmethod
    def start_incremental_sync(user_id):
        """Start an incremental sync job."""
        engine = SyncEngine(user_id=user_id)
        engine.job.job_type = 'incremental'
        db.session.commit()
        
        engine.start_sync()
        return engine.job_id
    
    @staticmethod
    def start_full_sync(user_id):
        """Start a full sync job."""
        engine = SyncEngine(user_id=user_id)
        engine.job.job_type = 'full'
        db.session.commit()
        
        engine.start_sync()
        return engine.job_id
    
    @staticmethod
    def start_property_export(user_id, database_name, num_years, min_bill_years):
        """Start a property export job."""
        engine = SyncEngine(user_id=user_id)
        engine.job.job_type = 'property_export'
        engine.job.name = f"Property Export to {database_name}"
        db.session.commit()
        
        # TODO: Implement property export functionality
        # This will be part of another implementation
        
        return engine.job_id
    
    @staticmethod
    def start_up_sync(user_id):
        """Start an up-sync job (training to production)."""
        # This will be implemented in the bidirectional sync feature
        return "up_sync_job_id"
    
    @staticmethod
    def start_down_sync(user_id):
        """Start a down-sync job (production to training)."""
        # This will be implemented in the bidirectional sync feature
        return "down_sync_job_id"

def register_sync_routes(bp):
    """Register routes with the provided blueprint."""
    
    # Status dashboard
    @bp.route('/')
    @login_required
    def index():
        """Sync service dashboard."""
        # Get recent jobs
        recent_jobs = SyncJob.query.order_by(SyncJob.created_at.desc()).limit(10).all()
        
        # Get global settings
        global_settings = GlobalSetting.query.first()
        
        # Get table configurations
        tables = TableConfiguration.query.order_by(TableConfiguration.order).all()
        
        return render_template('sync/index.html', 
                              recent_jobs=recent_jobs, 
                              global_settings=global_settings,
                              tables=tables)

    # Job management
    @bp.route('/jobs')
    @login_required
    def jobs():
        """List sync jobs."""
        jobs = SyncJob.query.order_by(SyncJob.created_at.desc()).all()
        return render_template('sync/jobs.html', jobs=jobs)

    @bp.route('/jobs/<job_id>')
    @login_required
    def job_details(job_id):
        """Show details for a specific job."""
        job = SyncJob.query.filter_by(job_id=job_id).first_or_404()
        logs = SyncLog.query.filter_by(job_id=job_id).order_by(SyncLog.created_at.desc()).limit(100).all()
        
        return render_template('sync/job_details.html', job=job, logs=logs)

    @bp.route('/jobs/<job_id>/logs')
    @login_required
    def job_logs(job_id):
        """Show logs for a specific job."""
        job = SyncJob.query.filter_by(job_id=job_id).first_or_404()
        level = request.args.get('level', None)
        limit = request.args.get('limit', 100, type=int)
        
        logs = DataSynchronizer.get_job_logs(job_id, level, limit)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(logs)
        
        return render_template('sync/job_logs.html', job=job, logs=logs)

    # Configuration management
    @bp.route('/config')
    @login_required
    @role_required('administrator')
    def configuration():
        """Manage sync configuration."""
        tables = TableConfiguration.query.order_by(TableConfiguration.order).all()
        return render_template('sync/config.html', tables=tables)

    @bp.route('/config/tables')
    @login_required
    @role_required('administrator')
    def table_configurations():
        """List table configurations."""
        tables = TableConfiguration.query.order_by(TableConfiguration.order).all()
        return render_template('sync/table_configurations.html', tables=tables)

    @bp.route('/config/tables/<table_name>')
    @login_required
    @role_required('administrator')
    def table_details(table_name):
        """Show details for a specific table configuration."""
        table = TableConfiguration.query.filter_by(name=table_name).first_or_404()
        fields = FieldConfiguration.query.filter_by(table_name=table_name).all()
        
        return render_template('sync/table_details.html', table=table, fields=fields)

    # API endpoints
    @bp.route('/api/start-sync', methods=['POST'])
    @login_required
    @role_required('administrator')
    def api_start_sync():
        """Start a sync job."""
        sync_type = request.json.get('type', 'incremental')
        user_id = session['user']['id']
        
        if sync_type == 'full':
            job_id = DataSynchronizer.start_full_sync(user_id)
        else:
            job_id = DataSynchronizer.start_incremental_sync(user_id)
        
        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': f"{sync_type.capitalize()} sync job started successfully."
        })

    @bp.route('/api/job-status/<job_id>')
    @login_required
    def api_job_status(job_id):
        """Get status for a specific job."""
        status = DataSynchronizer.get_job_status(job_id)
        return jsonify(status)

    @bp.route('/api/job-logs/<job_id>')
    @login_required
    def api_job_logs(job_id):
        """Get logs for a specific job."""
        level = request.args.get('level', None)
        limit = request.args.get('limit', 100, type=int)
        
        logs = DataSynchronizer.get_job_logs(job_id, level, limit)
        return jsonify(logs)

    # Manual actions
    @bp.route('/run/incremental')
    @login_required
    @role_required('administrator')
    def run_incremental_sync():
        """Run an incremental sync job."""
        job_id = DataSynchronizer.start_incremental_sync(session['user']['id'])
        flash(f'Incremental sync job started. Job ID: {job_id}', 'success')
        return redirect(url_for('sync.job_details', job_id=job_id))

    @bp.route('/run/full')
    @login_required
    @role_required('administrator')
    def run_full_sync():
        """Run a full sync job."""
        job_id = DataSynchronizer.start_full_sync(session['user']['id'])
        flash(f'Full sync job started. Job ID: {job_id}', 'success')
        return redirect(url_for('sync.job_details', job_id=job_id))

    # Property Export Routes
    @bp.route('/property-export')
    @login_required
    @role_required('administrator')
    def property_export():
        """Property export form."""
        recent_jobs = SyncJob.query.filter_by(job_type='property_export').order_by(SyncJob.created_at.desc()).limit(5).all()
        return render_template('sync/property_export.html', recent_jobs=recent_jobs)

    @bp.route('/run/property-export', methods=['POST'])
    @login_required
    @role_required('administrator')
    def run_property_export():
        """Run a property export job."""
        database_name = request.form.get('database_name', '')
        num_years = int(request.form.get('num_years', -1))
        min_bill_years = int(request.form.get('min_bill_years', 2))
        
        job_id = DataSynchronizer.start_property_export(
            session['user']['id'], 
            database_name, 
            num_years, 
            min_bill_years
        )
        
        flash(f'Property export job started. Job ID: {job_id}', 'success')
        return redirect(url_for('sync.job_details', job_id=job_id))

    @bp.route('/api/start-property-export', methods=['POST'])
    @login_required
    @role_required('administrator')
    def api_start_property_export():
        """Start a property export job via API."""
        database_name = request.json.get('database_name', '')
        num_years = request.json.get('num_years', -1)
        min_bill_years = request.json.get('min_bill_years', 2)
        user_id = session['user']['id']
        
        job_id = DataSynchronizer.start_property_export(
            user_id,
            database_name,
            num_years,
            min_bill_years
        )
        
        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': f"Property export job started successfully."
        })
        
    # New bi-directional sync routes
    @bp.route('/bidirectional-sync')
    @login_required
    @role_required('administrator')
    def bidirectional_sync():
        """Bi-directional sync dashboard."""
        return render_template('sync/bidirectional_sync.html')
        
    @bp.route('/run/up-sync')
    @login_required
    @role_required('administrator')
    def run_up_sync():
        """Run an up-sync job (training to production)."""
        job_id = DataSynchronizer.start_up_sync(session['user']['id'])
        flash(f'Up-sync job started. Job ID: {job_id}', 'success')
        return redirect(url_for('sync.job_details', job_id=job_id))
        
    @bp.route('/run/down-sync')
    @login_required
    @role_required('administrator')
    def run_down_sync():
        """Run a down-sync job (production to training)."""
        job_id = DataSynchronizer.start_down_sync(session['user']['id'])
        flash(f'Down-sync job started. Job ID: {job_id}', 'success')
        return redirect(url_for('sync.job_details', job_id=job_id))
        
    @bp.route('/api/start-up-sync', methods=['POST'])
    @login_required
    @role_required('administrator')
    def api_start_up_sync():
        """Start an up-sync job via API."""
        user_id = session['user']['id']
        job_id = DataSynchronizer.start_up_sync(user_id)
        
        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': "Up-sync job started successfully."
        })
        
    @bp.route('/api/start-down-sync', methods=['POST'])
    @login_required
    @role_required('administrator')
    def api_start_down_sync():
        """Start a down-sync job via API."""
        user_id = session['user']['id']
        job_id = DataSynchronizer.start_down_sync(user_id)
        
        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': "Down-sync job started successfully."
        })