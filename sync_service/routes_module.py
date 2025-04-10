"""
Routes for the Sync Service module.

These routes provide API endpoints for configuring, controlling, and monitoring
the synchronization process.
"""
import datetime
from flask import render_template, request, jsonify, session, flash, redirect, url_for
from app import db
from sync_service.models import (
    SyncJob, TableConfiguration, FieldConfiguration, SyncLog, GlobalSetting
)
from sync_service.sync_engine import SyncEngine
from sync_service.bidirectional_sync import DataSynchronizer
from auth import login_required, permission_required, role_required

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
        # Get recent bidirectional sync jobs
        recent_jobs = SyncJob.query.filter(
            SyncJob.job_type.in_(['up_sync', 'down_sync'])
        ).order_by(SyncJob.created_at.desc()).limit(10).all()
        
        # Get global settings
        global_settings = GlobalSetting.query.first()
        
        # Get current time for calculating "hours ago"
        now = datetime.datetime.utcnow()
        
        return render_template('sync/bidirectional_sync.html', 
                              recent_jobs=recent_jobs,
                              global_settings=global_settings,
                              now=now)
        
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
        
    @bp.route('/api/pending-changes-count')
    @login_required
    @role_required('administrator')
    def api_pending_changes_count():
        """Get the count of pending changes for up-sync."""
        from sync_service.bidirectional_sync import DataSynchronizer
        count = DataSynchronizer.get_pending_changes_count()
        
        return jsonify({
            'count': count,
            'message': f"{count} pending change{'s' if count != 1 else ''} found"
        })
        
    # Scheduler management routes
    @bp.route('/schedules')
    @login_required
    @role_required('administrator')
    def schedules():
        """List all sync schedules."""
        from sync_service.scheduler import get_job_next_run
        
        # Get all schedules
        schedules = SyncSchedule.query.order_by(SyncSchedule.created_at.desc()).all()
        
        # Add next run time to each schedule
        for schedule in schedules:
            if schedule.job_id:
                schedule.next_run = get_job_next_run(schedule.job_id)
            else:
                schedule.next_run = None
                
        return render_template('sync/schedules.html', schedules=schedules)
    
    @bp.route('/schedules/add', methods=['POST'])
    @login_required
    @role_required('administrator')
    def add_schedule():
        """Add a new sync schedule."""
        from sync_service.scheduler import add_job_from_schedule
        
        try:
            # Create new schedule from form data
            schedule = SyncSchedule(
                name=request.form.get('name'),
                description=request.form.get('description'),
                job_type=request.form.get('job_type'),
                schedule_type=request.form.get('schedule_type'),
                created_by=session['user']['id']
            )
            
            # Set schedule details based on type
            if schedule.schedule_type == 'cron':
                schedule.cron_expression = request.form.get('cron_expression')
            else:  # interval
                schedule.interval_hours = int(request.form.get('interval_hours', 24))
            
            # For property export, add additional parameters
            if schedule.job_type == 'property_export':
                schedule.parameters = {
                    'database_name': request.form.get('database_name', 'web_internet_benton'),
                    'num_years': request.form.get('num_years', -1),
                    'min_bill_years': request.form.get('min_bill_years', 2)
                }
            
            # Save to database
            db.session.add(schedule)
            db.session.commit()
            
            # Add to scheduler
            if add_job_from_schedule(schedule):
                flash(f"Schedule '{schedule.name}' created successfully.", 'success')
            else:
                flash(f"Schedule saved but could not be activated.", 'warning')
                
            return redirect(url_for('sync.schedules'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating schedule: {str(e)}", 'danger')
            return redirect(url_for('sync.schedules'))
    
    @bp.route('/schedules/<int:schedule_id>/edit', methods=['GET', 'POST'])
    @login_required
    @role_required('administrator')
    def edit_schedule(schedule_id):
        """Edit an existing sync schedule."""
        from sync_service.scheduler import update_job_schedule
        
        schedule = SyncSchedule.query.get_or_404(schedule_id)
        
        if request.method == 'POST':
            try:
                # Update schedule from form data
                schedule.name = request.form.get('name')
                schedule.description = request.form.get('description')
                schedule.job_type = request.form.get('job_type')
                schedule.schedule_type = request.form.get('schedule_type')
                
                # Set schedule details based on type
                if schedule.schedule_type == 'cron':
                    schedule.cron_expression = request.form.get('cron_expression')
                    schedule.interval_hours = None
                else:  # interval
                    schedule.interval_hours = int(request.form.get('interval_hours', 24))
                    schedule.cron_expression = None
                
                # For property export, add additional parameters
                if schedule.job_type == 'property_export':
                    schedule.parameters = {
                        'database_name': request.form.get('database_name', 'web_internet_benton'),
                        'num_years': request.form.get('num_years', -1),
                        'min_bill_years': request.form.get('min_bill_years', 2)
                    }
                else:
                    schedule.parameters = {}
                
                # Update last_updated timestamp
                schedule.last_updated = datetime.datetime.utcnow()
                
                # Save to database
                db.session.commit()
                
                # Update in scheduler
                if update_job_schedule(schedule):
                    flash(f"Schedule '{schedule.name}' updated successfully.", 'success')
                else:
                    flash(f"Schedule saved but could not be updated in the scheduler.", 'warning')
                    
                return redirect(url_for('sync.schedules'))
                
            except Exception as e:
                db.session.rollback()
                flash(f"Error updating schedule: {str(e)}", 'danger')
                return redirect(url_for('sync.schedules'))
        
        # GET request - show edit form
        return render_template('sync/edit_schedule.html', schedule=schedule)
    
    @bp.route('/schedules/<int:schedule_id>/delete')
    @login_required
    @role_required('administrator')
    def delete_schedule(schedule_id):
        """Delete a sync schedule."""
        from sync_service.scheduler import remove_scheduled_job
        
        try:
            schedule = SyncSchedule.query.get_or_404(schedule_id)
            
            # Remove from scheduler if active
            if schedule.is_active and schedule.job_id:
                remove_scheduled_job(schedule_id)
            
            # Get the name before deleting
            schedule_name = schedule.name
            
            # Remove from database
            db.session.delete(schedule)
            db.session.commit()
            
            flash(f"Schedule '{schedule_name}' deleted successfully.", 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting schedule: {str(e)}", 'danger')
            
        return redirect(url_for('sync.schedules'))
    
    @bp.route('/schedules/<int:schedule_id>/pause')
    @login_required
    @role_required('administrator')
    def pause_schedule(schedule_id):
        """Pause a sync schedule."""
        from sync_service.scheduler import pause_scheduled_job
        
        try:
            if pause_scheduled_job(schedule_id):
                flash("Schedule paused successfully.", 'success')
            else:
                flash("Could not pause schedule.", 'warning')
                
        except Exception as e:
            flash(f"Error pausing schedule: {str(e)}", 'danger')
            
        return redirect(url_for('sync.schedules'))
    
    @bp.route('/schedules/<int:schedule_id>/resume')
    @login_required
    @role_required('administrator')
    def resume_schedule(schedule_id):
        """Resume a paused sync schedule."""
        from sync_service.scheduler import resume_scheduled_job
        
        try:
            if resume_scheduled_job(schedule_id):
                flash("Schedule resumed successfully.", 'success')
            else:
                flash("Could not resume schedule.", 'warning')
                
        except Exception as e:
            flash(f"Error resuming schedule: {str(e)}", 'danger')
            
        return redirect(url_for('sync.schedules'))
    
    @bp.route('/schedules/<int:schedule_id>/run-now')
    @login_required
    @role_required('administrator')
    def run_schedule_now(schedule_id):
        """Run a schedule immediately."""
        try:
            schedule = SyncSchedule.query.get_or_404(schedule_id)
            
            # Get the user ID
            user_id = session['user']['id']
            
            # Run the appropriate job based on job type
            if schedule.job_type == 'up_sync':
                job_id = DataSynchronizer.start_up_sync(user_id)
            elif schedule.job_type == 'down_sync':
                job_id = DataSynchronizer.start_down_sync(user_id)
            elif schedule.job_type == 'full_sync':
                job_id = DataSynchronizer.start_full_sync(user_id)
            elif schedule.job_type == 'incremental_sync':
                job_id = DataSynchronizer.start_incremental_sync(user_id)
            elif schedule.job_type == 'property_export':
                params = schedule.parameters or {}
                database_name = params.get('database_name', 'web_internet_benton')
                num_years = int(params.get('num_years', -1))
                min_bill_years = int(params.get('min_bill_years', 2))
                
                job_id = DataSynchronizer.start_property_export(
                    user_id,
                    database_name,
                    num_years,
                    min_bill_years
                )
            else:
                flash(f"Unknown job type: {schedule.job_type}", 'danger')
                return redirect(url_for('sync.schedules'))
            
            # Update the schedule with the last run information
            schedule.last_run = datetime.datetime.utcnow()
            schedule.last_job_id = job_id
            db.session.commit()
            
            flash(f"Schedule '{schedule.name}' run initiated successfully. Job ID: {job_id}", 'success')
            return redirect(url_for('sync.job_details', job_id=job_id))
            
        except Exception as e:
            flash(f"Error running schedule: {str(e)}", 'danger')
            return redirect(url_for('sync.schedules'))