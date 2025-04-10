"""
Database models for sync_service module
"""
import datetime
import uuid
from typing import Dict, Any, List, Optional

from sqlalchemy.dialects.postgresql import JSON
from app import db

class SyncJob(db.Model):
    """A synchronization job record"""
    __tablename__ = 'sync_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    job_type = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False, index=True)
    user_id = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    
    total_records = db.Column(db.Integer, default=0)
    processed_records = db.Column(db.Integer, default=0)
    error_records = db.Column(db.Integer, default=0)
    error_details = db.Column(JSON, default={})
    
    def __init__(self, job_id=None, job_type='sync', name=None, user_id=None):
        self.job_id = job_id or str(uuid.uuid4())
        self.job_type = job_type
        self.name = name or f"{job_type.capitalize()} Job {self.job_id[:8]}"
        self.user_id = user_id
        self.status = 'pending'
        self.created_at = datetime.datetime.utcnow()
        self.total_records = 0
        self.processed_records = 0
        self.error_records = 0
        self.error_details = {}
    
    def __repr__(self):
        return f"<SyncJob {self.job_id} [{self.status}]>"

class SyncLog(db.Model):
    """A log entry for a sync job"""
    __tablename__ = 'sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(50), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    level = db.Column(db.String(20), default='INFO', nullable=False)
    message = db.Column(db.Text, nullable=False)
    component = db.Column(db.String(100))
    table_name = db.Column(db.String(100))
    record_count = db.Column(db.Integer)
    duration_ms = db.Column(db.Integer)
    
    def __init__(self, job_id, message, level='INFO', component=None, 
                table_name=None, record_count=None, duration_ms=None):
        self.job_id = job_id
        self.message = message
        self.level = level.upper()
        self.component = component
        self.table_name = table_name
        self.record_count = record_count
        self.duration_ms = duration_ms
        self.created_at = datetime.datetime.utcnow()
    
    def __repr__(self):
        return f"<SyncLog {self.id} [{self.level}]: {self.message[:30]}...>"

class TableConfiguration(db.Model):
    """Configuration for a table to be synchronized"""
    __tablename__ = 'table_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    source_name = db.Column(db.String(100))
    display_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_incremental = db.Column(db.Boolean, default=True, nullable=False)
    batch_size = db.Column(db.Integer, default=1000)
    order = db.Column(db.Integer, default=0)
    
    primary_key = db.Column(db.String(100))
    timestamp_field = db.Column(db.String(100))
    last_sync_time = db.Column(db.DateTime)
    source_query = db.Column(db.Text)
    target_query = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<TableConfiguration {self.name}>"

class FieldConfiguration(db.Model):
    """Configuration for a field in a synchronized table"""
    __tablename__ = 'field_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(100), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    source_name = db.Column(db.String(100))
    display_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    
    data_type = db.Column(db.String(50))
    is_nullable = db.Column(db.Boolean, default=True)
    is_primary_key = db.Column(db.Boolean, default=False)
    is_timestamp = db.Column(db.Boolean, default=False)
    is_inherited = db.Column(db.Boolean, default=False)
    
    transform_sql = db.Column(db.Text)
    default_value = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<FieldConfiguration {self.table_name}.{self.name}>"

class GlobalSetting(db.Model):
    """Global settings for synchronization"""
    __tablename__ = 'global_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    is_sync_enabled = db.Column(db.Boolean, default=True)
    last_sync_time = db.Column(db.DateTime)
    last_sync_job_id = db.Column(db.String(50))
    sync_frequency_hours = db.Column(db.Integer, default=24)
    
    is_property_export_enabled = db.Column(db.Boolean, default=True)
    last_property_export_time = db.Column(db.DateTime)
    last_property_export_job_id = db.Column(db.String(50))
    
    last_up_sync_time = db.Column(db.DateTime)
    last_up_sync_job_id = db.Column(db.String(50))
    
    last_down_sync_time = db.Column(db.DateTime)
    last_down_sync_job_id = db.Column(db.String(50))
    
    system_user_id = db.Column(db.Integer)
    notification_email = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<GlobalSetting {self.id}>"

class UpSyncDataChange(db.Model):
    """A record of data changes for up-sync operations (training to production)"""
    __tablename__ = 'up_sync_data_changes'
    
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(100), nullable=False, index=True)
    field_name = db.Column(db.String(100), nullable=False)
    
    # Comma-separated list of "key=value" pairs for identifying the record
    keys = db.Column(db.Text, nullable=False)
    
    # The before and after values for the specific field
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    
    # The type of change (insert, update, delete)
    action = db.Column(db.String(20), nullable=False)
    
    # When the change was made
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # When the change was inserted into this tracking table
    record_inserted_date = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Whether this change has been processed by the up-sync process
    is_processed = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_processed_date = db.Column(db.DateTime)
    
    # Additional metadata
    pacs_user = db.Column(db.String(100))
    cc_field_id = db.Column(db.Integer)
    parcel_id = db.Column(db.String(100))
    unique_cc_row_id = db.Column(db.Integer)
    unique_cc_parent_row_id = db.Column(db.Integer)
    
    def __repr__(self):
        return f"<UpSyncDataChange {self.id} {self.table_name}.{self.field_name} [{self.action}]>"

class UpSyncDataChangeArchive(db.Model):
    """Archive of processed up-sync data changes"""
    __tablename__ = 'up_sync_data_change_archives'
    
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(100), nullable=False, index=True)
    field_name = db.Column(db.String(100), nullable=False)
    
    # Comma-separated list of "key=value" pairs for identifying the record
    keys = db.Column(db.Text, nullable=False)
    
    # The before and after values for the specific field
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    
    # The type of change (insert, update, delete)
    action = db.Column(db.String(20), nullable=False)
    
    # When the change was made
    date = db.Column(db.DateTime, nullable=False)
    
    # When the change was inserted into the tracking table
    record_inserted_date = db.Column(db.DateTime, nullable=False)
    
    # When the change was processed by the up-sync process
    is_processed = db.Column(db.Boolean, default=True, nullable=False)
    is_processed_date = db.Column(db.DateTime, nullable=False)
    
    # Additional metadata
    pacs_user = db.Column(db.String(100))
    cc_field_id = db.Column(db.Integer)
    parcel_id = db.Column(db.String(100))
    unique_cc_row_id = db.Column(db.Integer)
    unique_cc_parent_row_id = db.Column(db.Integer)
    
    def __repr__(self):
        return f"<UpSyncDataChangeArchive {self.id} {self.table_name}.{self.field_name} [{self.action}]>"

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
    parameters = db.Column(JSON, default={})
    
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