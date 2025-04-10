"""
Scheduled Job Management for Data Hub Sync Service.

This module provides functionality for scheduling and managing sync jobs 
using APScheduler. It allows setting up recurring sync jobs and managing
the schedule through the web interface.
"""
import logging
from typing import Dict, Any, Optional, List
import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from app import db
from sync_service.models import GlobalSetting, SyncJob, SyncLog
from sync_service.bidirectional_sync import DataSynchronizer
from sync_service.app_context import with_app_context, handle_job_exception

# Create SyncSchedule model here to avoid import issues
class SyncSchedule(db.Model):
    """Schedule for automated sync jobs"""
    __tablename__ = 'sync_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Schedule configuration
    job_type = db.Column(db.String(50), nullable=False)  # up_sync, down_sync, full_sync, incremental_sync, property_export
    schedule_type = db.Column(db.String(20), nullable=False)  # cron, interval
    cron_expression = db.Column(db.String(100))  # For cron-based schedules
    interval_hours = db.Column(db.Integer)  # For interval-based schedules
    
    # Additional parameters for the job (stored as JSON)
    parameters = db.Column(db.JSON, default={})
    
    # Status and tracking
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    last_run = db.Column(db.DateTime)
    last_job_id = db.Column(db.String(50))
    job_id = db.Column(db.String(100))  # ID of the scheduled job in the APScheduler
    
    # User who created the schedule
    created_by = db.Column(db.Integer)
    
    def __repr__(self):
        return f"<SyncSchedule {self.id} {self.name} [{self.job_type}]>"

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create scheduler instance
jobstore = SQLAlchemyJobStore(engine=db.engine)
executors = {
    'default': ThreadPoolExecutor(10)
}
job_defaults = {
    'coalesce': True,
    'max_instances': 1
}

scheduler = BackgroundScheduler(
    jobstores={'default': jobstore},
    executors=executors,
    job_defaults=job_defaults
)

@with_app_context
def init_scheduler():
    """Initialize the scheduler and load existing schedules with proper application context."""
    logger.info("Initializing sync job scheduler")
    
    # Start the scheduler if it's not already running
    if not scheduler.running:
        scheduler.start()
    
    # Load existing schedules from database
    try:
        # Create a new session to avoid transaction issues
        with db.session.begin():
            # Get active schedules
            schedules = SyncSchedule.query.filter_by(is_active=True).all()
            # Clone the data to avoid using session objects outside of the transaction
            schedule_data = [(s.id, s.name, s.job_type) for s in schedules]
        
        # Now add the jobs using the collected data
        for schedule_id, name, job_type in schedule_data:
            # Get a fresh instance of the schedule
            with db.session.begin():
                schedule = SyncSchedule.query.get(schedule_id)
                if schedule:
                    add_job_from_schedule(schedule)
                    logger.info(f"Loaded scheduled job: {name} ({job_type})")
    except Exception as e:
        logger.error(f"Error loading scheduled jobs: {str(e)}")
        # Make sure to rollback any active transaction
        try:
            db.session.rollback()
        except:
            pass
    
    logger.info(f"Scheduler initialized with {len(scheduler.get_jobs())} jobs")
    
    return scheduler

def add_job_from_schedule(schedule: SyncSchedule) -> Optional[str]:
    """Add a job to the scheduler from a SyncSchedule object."""
    try:
        # Create the appropriate trigger based on schedule type
        if schedule.schedule_type == 'cron':
            trigger = CronTrigger.from_crontab(schedule.cron_expression)
        elif schedule.schedule_type == 'interval':
            # Parse interval (stored as hours)
            interval_hours = int(schedule.interval_hours) if schedule.interval_hours else 24
            trigger = IntervalTrigger(hours=interval_hours)
        else:
            logger.error(f"Unknown schedule type: {schedule.schedule_type}")
            return None
        
        # Determine which function to call based on job type
        if schedule.job_type == 'up_sync':
            job_function = scheduled_up_sync
        elif schedule.job_type == 'down_sync':
            job_function = scheduled_down_sync
        elif schedule.job_type == 'full_sync':
            job_function = scheduled_full_sync
        elif schedule.job_type == 'incremental_sync':
            job_function = scheduled_incremental_sync
        elif schedule.job_type == 'property_export':
            job_function = scheduled_property_export
        else:
            logger.error(f"Unknown job type: {schedule.job_type}")
            return None
        
        # Add the job to the scheduler
        job = scheduler.add_job(
            job_function,
            trigger=trigger,
            id=f"sync_{schedule.id}",
            name=schedule.name,
            args=[schedule.id],
            replace_existing=True
        )
        
        # Update the schedule with the job ID using a fresh transaction
        try:
            with db.session.begin():
                # Get a fresh copy of the schedule to avoid transaction issues
                fresh_schedule = SyncSchedule.query.get(schedule.id)
                if fresh_schedule:
                    fresh_schedule.job_id = job.id
                    fresh_schedule.last_updated = datetime.datetime.utcnow()
                else:
                    logger.warning(f"Could not find schedule {schedule.id} to update job ID")
        except Exception as e:
            logger.error(f"Error updating schedule job ID: {str(e)}")
            # Try to rollback explicitly
            try:
                db.session.rollback()
            except:
                pass
        
        logger.info(f"Added scheduled job: {schedule.name} ({schedule.job_type})")
        return job.id
        
    except Exception as e:
        logger.error(f"Error adding job from schedule: {str(e)}")
        return None

def remove_scheduled_job(schedule_id: int) -> bool:
    """Remove a job from the scheduler."""
    try:
        schedule = SyncSchedule.query.get(schedule_id)
        if not schedule or not schedule.job_id:
            logger.warning(f"Schedule {schedule_id} not found or has no job ID")
            return False
        
        # Remove the job from the scheduler
        scheduler.remove_job(schedule.job_id)
        
        # Update the schedule
        schedule.job_id = None
        schedule.is_active = False
        schedule.last_updated = datetime.datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Removed scheduled job: {schedule.name} ({schedule.job_type})")
        return True
        
    except Exception as e:
        logger.error(f"Error removing scheduled job: {str(e)}")
        return False

def pause_scheduled_job(schedule_id: int) -> bool:
    """Pause a scheduled job."""
    try:
        schedule = SyncSchedule.query.get(schedule_id)
        if not schedule or not schedule.job_id:
            logger.warning(f"Schedule {schedule_id} not found or has no job ID")
            return False
        
        # Pause the job
        scheduler.pause_job(schedule.job_id)
        
        # Update the schedule
        schedule.is_active = False
        schedule.last_updated = datetime.datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Paused scheduled job: {schedule.name} ({schedule.job_type})")
        return True
        
    except Exception as e:
        logger.error(f"Error pausing scheduled job: {str(e)}")
        return False

def resume_scheduled_job(schedule_id: int) -> bool:
    """Resume a paused scheduled job."""
    try:
        schedule = SyncSchedule.query.get(schedule_id)
        if not schedule or not schedule.job_id:
            logger.warning(f"Schedule {schedule_id} not found or has no job ID")
            return False
        
        # Resume the job
        scheduler.resume_job(schedule.job_id)
        
        # Update the schedule
        schedule.is_active = True
        schedule.last_updated = datetime.datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Resumed scheduled job: {schedule.name} ({schedule.job_type})")
        return True
        
    except Exception as e:
        logger.error(f"Error resuming scheduled job: {str(e)}")
        return False

def get_job_next_run(job_id: str) -> Optional[datetime.datetime]:
    """Get the next run time for a job."""
    try:
        job = scheduler.get_job(job_id)
        if not job:
            return None
        return job.next_run_time
    except Exception as e:
        logger.error(f"Error getting next run time: {str(e)}")
        return None

def update_job_schedule(schedule: SyncSchedule) -> bool:
    """Update an existing job schedule."""
    try:
        # Remove the existing job
        if schedule.job_id:
            try:
                scheduler.remove_job(schedule.job_id)
            except Exception:
                pass  # Job might not exist anymore
        
        # Only add the job if the schedule is active
        if schedule.is_active:
            job_id = add_job_from_schedule(schedule)
            if not job_id:
                return False
        
        logger.info(f"Updated scheduled job: {schedule.name} ({schedule.job_type})")
        return True
        
    except Exception as e:
        logger.error(f"Error updating job schedule: {str(e)}")
        return False

# Scheduled job functions

# Scheduled job functions

@with_app_context
def scheduled_up_sync(schedule_id: int):
    """Run a scheduled up-sync job with proper application context."""
    job_id = None
    try:
        # Start a fresh transaction to get the schedule
        with db.session.begin():
            schedule = SyncSchedule.query.get(schedule_id)
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return
            
            # Store the name for logging outside the transaction
            schedule_name = schedule.name
            
        logger.info(f"Running scheduled up-sync job: {schedule_name}")
        
        # Get the system user ID in a separate transaction
        user_id = 1  # Default
        try:
            with db.session.begin():
                global_settings = GlobalSetting.query.first()
                if global_settings and global_settings.system_user_id:
                    user_id = global_settings.system_user_id
        except Exception as e:
            logger.warning(f"Could not get system user ID: {str(e)}")
        
        # Run the up-sync job
        job_id = DataSynchronizer.start_up_sync(user_id)
        
        # Update the schedule with the last run information in a separate transaction
        try:
            with db.session.begin():
                # Get a fresh copy of the schedule
                fresh_schedule = SyncSchedule.query.get(schedule_id)
                if fresh_schedule:
                    fresh_schedule.last_run = datetime.datetime.utcnow()
                    fresh_schedule.last_job_id = job_id
                    fresh_schedule.last_updated = datetime.datetime.utcnow()
                else:
                    logger.warning(f"Could not find schedule {schedule_id} to update last run info")
        except Exception as e:
            logger.error(f"Error updating schedule last run info: {str(e)}")
            # Try to rollback explicitly
            try:
                db.session.rollback()
            except:
                pass
        
        logger.info(f"Completed scheduled up-sync job: {schedule_name}, Job ID: {job_id}")
        
    except Exception as e:
        error_msg = f"Error in scheduled up-sync job: {str(e)}"
        logger.error(error_msg)
        if job_id:
            handle_job_exception(job_id, e)
        # Make sure to rollback any active transaction
        try:
            db.session.rollback()
        except:
            pass

@with_app_context
def scheduled_down_sync(schedule_id: int):
    """Run a scheduled down-sync job with proper application context."""
    job_id = None
    try:
        # Start a fresh transaction to get the schedule
        with db.session.begin():
            schedule = SyncSchedule.query.get(schedule_id)
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return
            
            # Store the name for logging outside the transaction
            schedule_name = schedule.name
            
        logger.info(f"Running scheduled down-sync job: {schedule_name}")
        
        # Get the system user ID in a separate transaction
        user_id = 1  # Default
        try:
            with db.session.begin():
                global_settings = GlobalSetting.query.first()
                if global_settings and global_settings.system_user_id:
                    user_id = global_settings.system_user_id
        except Exception as e:
            logger.warning(f"Could not get system user ID: {str(e)}")
        
        # Run the down-sync job
        job_id = DataSynchronizer.start_down_sync(user_id)
        
        # Update the schedule with the last run information in a separate transaction
        try:
            with db.session.begin():
                # Get a fresh copy of the schedule
                fresh_schedule = SyncSchedule.query.get(schedule_id)
                if fresh_schedule:
                    fresh_schedule.last_run = datetime.datetime.utcnow()
                    fresh_schedule.last_job_id = job_id
                    fresh_schedule.last_updated = datetime.datetime.utcnow()
                else:
                    logger.warning(f"Could not find schedule {schedule_id} to update last run info")
        except Exception as e:
            logger.error(f"Error updating schedule last run info: {str(e)}")
            # Try to rollback explicitly
            try:
                db.session.rollback()
            except:
                pass
        
        logger.info(f"Completed scheduled down-sync job: {schedule_name}, Job ID: {job_id}")
        
    except Exception as e:
        error_msg = f"Error in scheduled down-sync job: {str(e)}"
        logger.error(error_msg)
        if job_id:
            handle_job_exception(job_id, e)
        # Make sure to rollback any active transaction
        try:
            db.session.rollback()
        except:
            pass

@with_app_context
def scheduled_full_sync(schedule_id: int):
    """Run a scheduled full sync job with proper application context."""
    job_id = None
    try:
        # Start a fresh transaction to get the schedule
        with db.session.begin():
            schedule = SyncSchedule.query.get(schedule_id)
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return
            
            # Store the name for logging outside the transaction
            schedule_name = schedule.name
            
        logger.info(f"Running scheduled full sync job: {schedule_name}")
        
        # Get the system user ID in a separate transaction
        user_id = 1  # Default
        try:
            with db.session.begin():
                global_settings = GlobalSetting.query.first()
                if global_settings and global_settings.system_user_id:
                    user_id = global_settings.system_user_id
        except Exception as e:
            logger.warning(f"Could not get system user ID: {str(e)}")
        
        # Run the full sync job
        job_id = DataSynchronizer.start_full_sync(user_id)
        
        # Update the schedule with the last run information in a separate transaction
        try:
            with db.session.begin():
                # Get a fresh copy of the schedule
                fresh_schedule = SyncSchedule.query.get(schedule_id)
                if fresh_schedule:
                    fresh_schedule.last_run = datetime.datetime.utcnow()
                    fresh_schedule.last_job_id = job_id
                    fresh_schedule.last_updated = datetime.datetime.utcnow()
                else:
                    logger.warning(f"Could not find schedule {schedule_id} to update last run info")
        except Exception as e:
            logger.error(f"Error updating schedule last run info: {str(e)}")
            # Try to rollback explicitly
            try:
                db.session.rollback()
            except:
                pass
        
        logger.info(f"Completed scheduled full sync job: {schedule_name}, Job ID: {job_id}")
        
    except Exception as e:
        error_msg = f"Error in scheduled full sync job: {str(e)}"
        logger.error(error_msg)
        if job_id:
            handle_job_exception(job_id, e)
        # Make sure to rollback any active transaction
        try:
            db.session.rollback()
        except:
            pass

@with_app_context
def scheduled_incremental_sync(schedule_id: int):
    """Run a scheduled incremental sync job with proper application context."""
    job_id = None
    try:
        # Start a fresh transaction to get the schedule
        with db.session.begin():
            schedule = SyncSchedule.query.get(schedule_id)
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return
            
            # Store the name for logging outside the transaction
            schedule_name = schedule.name
            
        logger.info(f"Running scheduled incremental sync job: {schedule_name}")
        
        # Get the system user ID in a separate transaction
        user_id = 1  # Default
        try:
            with db.session.begin():
                global_settings = GlobalSetting.query.first()
                if global_settings and global_settings.system_user_id:
                    user_id = global_settings.system_user_id
        except Exception as e:
            logger.warning(f"Could not get system user ID: {str(e)}")
        
        # Run the incremental sync job
        job_id = DataSynchronizer.start_incremental_sync(user_id)
        
        # Update the schedule with the last run information in a separate transaction
        try:
            with db.session.begin():
                # Get a fresh copy of the schedule
                fresh_schedule = SyncSchedule.query.get(schedule_id)
                if fresh_schedule:
                    fresh_schedule.last_run = datetime.datetime.utcnow()
                    fresh_schedule.last_job_id = job_id
                    fresh_schedule.last_updated = datetime.datetime.utcnow()
                else:
                    logger.warning(f"Could not find schedule {schedule_id} to update last run info")
        except Exception as e:
            logger.error(f"Error updating schedule last run info: {str(e)}")
            # Try to rollback explicitly
            try:
                db.session.rollback()
            except:
                pass
        
        logger.info(f"Completed scheduled incremental sync job: {schedule_name}, Job ID: {job_id}")
        
    except Exception as e:
        error_msg = f"Error in scheduled incremental sync job: {str(e)}"
        logger.error(error_msg)
        if job_id:
            handle_job_exception(job_id, e)
        # Make sure to rollback any active transaction
        try:
            db.session.rollback()
        except:
            pass

@with_app_context
def scheduled_property_export(schedule_id: int):
    """Run a scheduled property export job with proper application context."""
    job_id = None
    try:
        # Start a fresh transaction to get the schedule and parameters
        schedule_name = None
        params = {}
        with db.session.begin():
            schedule = SyncSchedule.query.get(schedule_id)
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return
            
            # Store the name and parameters for use outside the transaction
            schedule_name = schedule.name
            params = schedule.parameters or {}
            
        logger.info(f"Running scheduled property export job: {schedule_name}")
        
        # Get the system user ID in a separate transaction
        user_id = 1  # Default
        try:
            with db.session.begin():
                global_settings = GlobalSetting.query.first()
                if global_settings and global_settings.system_user_id:
                    user_id = global_settings.system_user_id
        except Exception as e:
            logger.warning(f"Could not get system user ID: {str(e)}")
        
        # Extract export parameters
        database_name = params.get('database_name', 'web_internet_benton')
        num_years = int(params.get('num_years', -1))
        min_bill_years = int(params.get('min_bill_years', 2))
        
        # Run the property export job
        job_id = DataSynchronizer.start_property_export(
            user_id,
            database_name,
            num_years,
            min_bill_years
        )
        
        # Update the schedule with the last run information in a separate transaction
        try:
            with db.session.begin():
                # Get a fresh copy of the schedule
                fresh_schedule = SyncSchedule.query.get(schedule_id)
                if fresh_schedule:
                    fresh_schedule.last_run = datetime.datetime.utcnow()
                    fresh_schedule.last_job_id = job_id
                    fresh_schedule.last_updated = datetime.datetime.utcnow()
                else:
                    logger.warning(f"Could not find schedule {schedule_id} to update last run info")
        except Exception as e:
            logger.error(f"Error updating schedule last run info: {str(e)}")
            # Try to rollback explicitly
            try:
                db.session.rollback()
            except:
                pass
        
        logger.info(f"Completed scheduled property export job: {schedule_name}, Job ID: {job_id}")
        
    except Exception as e:
        error_msg = f"Error in scheduled property export job: {str(e)}"
        logger.error(error_msg)
        if job_id:
            handle_job_exception(job_id, e)
        # Make sure to rollback any active transaction
        try:
            db.session.rollback()
        except:
            pass