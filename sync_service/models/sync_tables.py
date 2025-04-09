"""
Sync service table models

This module contains the database models for the sync service tables.
"""
import datetime
from app import db
from sqlalchemy import Index, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import JSON

class SyncBase(object):
    """Base class for sync service models with common fields."""

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    @declared_attr
    def __tablename__(cls):
        # Convert CamelCase to snake_case for table names
        name = cls.__name__
        import re
        return re.sub('(?<!^)(?=[A-Z])', '_', name).lower()

class SyncJob(SyncBase, db.Model):
    """Represents a sync job execution."""

    job_id = db.Column(db.String(36), unique=True, nullable=False)  # UUID
    name = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(32), nullable=False, default='pending')  # pending, running, completed, failed
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    total_records = db.Column(db.Integer, default=0)
    processed_records = db.Column(db.Integer, default=0)
    error_records = db.Column(db.Integer, default=0)
    error_details = db.Column(JSON)
    job_type = db.Column(db.String(64))  # full, incremental, schema, etc.
    source_db = db.Column(db.String(256))
    target_db = db.Column(db.String(256))
    initiated_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f"<SyncJob {self.job_id} ({self.status})>"

class TableConfiguration(SyncBase, db.Model):
    """Configuration for tables to be synchronized."""

    name = db.Column(db.String(128), unique=True, nullable=False)
    join_table = db.Column(db.String(128))
    join_sql = db.Column(db.Text)
    order = db.Column(db.Integer, nullable=False, default=0)
    total_pages = db.Column(db.BigInteger, default=0)
    current_page = db.Column(db.BigInteger, default=0)
    total_pages_for_change_schema = db.Column(db.BigInteger, default=0)
    current_page_for_change_schema = db.Column(db.BigInteger, default=0)
    total_pages_for_assign_group_refresh = db.Column(db.BigInteger, default=0)
    current_page_for_assign_group_refresh = db.Column(db.BigInteger, default=0)
    is_flat = db.Column(db.Boolean, default=True)
    is_lookup = db.Column(db.Boolean, default=False)
    is_controller = db.Column(db.Boolean, default=False)
    sub_select = db.Column(db.Text)
    order_by_sql = db.Column(db.Text)
    
    # Relationships
    field_configurations = db.relationship('FieldConfiguration', backref='table', lazy='dynamic')
    field_default_values = db.relationship('FieldDefaultValue', backref='table', lazy='dynamic')
    primary_key_columns = db.relationship('PrimaryKeyColumn', backref='table', lazy='dynamic')
    parcel_maps = db.relationship('ParcelMap', backref='table', lazy='dynamic')

    def __repr__(self):
        return f"<TableConfiguration {self.name}>"

class FieldConfiguration(db.Model):
    """Configuration for fields in synchronized tables."""

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(128), db.ForeignKey('table_configuration.name', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    policy_type = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(256))
    cama_cloud_id = db.Column(db.String(256))
    type = db.Column(db.String(64), nullable=False)
    length = db.Column(db.Integer)
    precision = db.Column(db.Integer)
    scale = db.Column(db.Integer)
    
    def __repr__(self):
        return f"<FieldConfiguration {self.table_name}.{self.name}>"

class FieldDefaultValue(db.Model):
    """Default values for fields in synchronized tables."""

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(128), db.ForeignKey('table_configuration.name', ondelete='CASCADE'), nullable=False)
    column_name = db.Column(db.String(128), nullable=False)
    default_value = db.Column(db.String(1024), nullable=False)
    
    def __repr__(self):
        return f"<FieldDefaultValue {self.table_name}.{self.column_name}: {self.default_value}>"

class PrimaryKeyColumn(db.Model):
    """Primary key columns for synchronized tables."""

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(128), db.ForeignKey('table_configuration.name', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f"<PrimaryKeyColumn {self.table_name}.{self.name} (order: {self.order})>"

class DataChangeMap(SyncBase, db.Model):
    """Maps for tracking data changes."""

    table_name = db.Column(db.String(128), nullable=False)
    composite_key = db.Column(db.String(512), nullable=False)
    unique_cc_row_id = db.Column(db.String(256))
    
    __table_args__ = (
        Index('idx_data_change_map_table_key', 'table_name', 'composite_key'),
    )
    
    def __repr__(self):
        return f"<DataChangeMap {self.table_name} ({self.composite_key})>"

class ParcelMap(db.Model):
    """Maps tables/rows to parcel IDs."""

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(128), db.ForeignKey('table_configuration.name', ondelete='CASCADE'), nullable=False)
    composite_key = db.Column(db.String(512), nullable=False)
    parcel_id = db.Column(db.String(128))
    
    __table_args__ = (
        Index('idx_parcel_map_table_key', 'table_name', 'composite_key'),
    )
    
    def __repr__(self):
        return f"<ParcelMap {self.table_name} ({self.composite_key}) -> {self.parcel_id}>"

class PhotoMap(SyncBase, db.Model):
    """Maps for tracking photo data."""

    pacs_image_id = db.Column(db.String(256), nullable=False)
    cc_image_id = db.Column(db.String(256))
    
    __table_args__ = (
        Index('idx_photo_map_pacs_id', 'pacs_image_id'),
    )
    
    def __repr__(self):
        return f"<PhotoMap {self.pacs_image_id} -> {self.cc_image_id}>"

class LookupTableConfiguration(SyncBase, db.Model):
    """Configuration for lookup tables."""

    name = db.Column(db.String(128), primary_key=True)
    code_column_name = db.Column(db.String(128))
    desc_column_name = db.Column(db.String(128))
    where_condition = db.Column(db.Text)
    join_condition = db.Column(db.Text)
    order_by_sql = db.Column(db.Text)
    is_transferred = db.Column(db.Boolean, default=False)
    has_none = db.Column(db.Boolean, default=False)
    null_code = db.Column(db.String(128))
    null_description = db.Column(db.String(128))
    
    def __repr__(self):
        return f"<LookupTableConfiguration {self.name}>"

class UpSyncDataChange(SyncBase, db.Model):
    """Tracks data changes for upsync operations."""

    table_name = db.Column(db.String(128), nullable=False)
    field_name = db.Column(db.String(128), nullable=False)
    keys = db.Column(db.String(1024), nullable=False)
    new_value = db.Column(db.Text)
    old_value = db.Column(db.Text)
    action = db.Column(db.String(32), nullable=False)  # insert, update, delete
    date = db.Column(db.DateTime)
    record_inserted_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    is_processed_date = db.Column(db.DateTime)
    pacs_user = db.Column(db.String(128))
    cc_field_id = db.Column(db.String(128))
    parcel_id = db.Column(db.String(128))
    unique_cc_row_id = db.Column(db.String(256))
    unique_cc_parent_row_id = db.Column(db.String(256))
    is_processed = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        Index('idx_upsync_data_change_processed', 'is_processed'),
        Index('idx_upsync_data_change_table_keys', 'table_name', 'keys'),
    )
    
    def __repr__(self):
        return f"<UpSyncDataChange {self.table_name}.{self.field_name} {self.action}>"

class UpSyncDataChangeArchive(SyncBase, db.Model):
    """Archive of processed upsync data changes."""

    table_name = db.Column(db.String(128), nullable=False)
    field_name = db.Column(db.String(128), nullable=False)
    keys = db.Column(db.String(1024), nullable=False)
    new_value = db.Column(db.Text)
    old_value = db.Column(db.Text)
    action = db.Column(db.String(32), nullable=False)  # insert, update, delete
    date = db.Column(db.DateTime)
    record_inserted_date = db.Column(db.DateTime, nullable=False)
    is_processed_date = db.Column(db.DateTime)
    pacs_user = db.Column(db.String(128))
    cc_field_id = db.Column(db.String(128))
    parcel_id = db.Column(db.String(128))
    unique_cc_row_id = db.Column(db.String(256))
    unique_cc_parent_row_id = db.Column(db.String(256))
    is_processed = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        Index('idx_upsync_archive_processed_date', 'is_processed_date'),
    )
    
    def __repr__(self):
        return f"<UpSyncDataChangeArchive {self.table_name}.{self.field_name} {self.action}>"

class ParcelChangeIndexLog(SyncBase, db.Model):
    """Logs of changes to parcel data."""

    down_sync_id = db.Column(db.String(36), nullable=False)  # UUID
    table_name = db.Column(db.String(128), nullable=False)
    action = db.Column(db.String(32), nullable=False)  # insert, update, delete
    parcel_id = db.Column(db.Integer, nullable=False)
    aux_row_id = db.Column(db.String(256))
    parent_row_id = db.Column(db.String(256))
    keys = db.Column(db.String(1024))
    new_value = db.Column(db.Text)
    field_id = db.Column(db.Integer, nullable=False)
    reviewed_by = db.Column(db.String(128))
    review_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    qc_by = db.Column(db.String(128))
    qc_time = db.Column(db.String(128))  # This seems to be a string in the original schema
    pci_status = db.Column(db.String(128))
    pci_description = db.Column(db.String(512))
    
    __table_args__ = (
        Index('idx_parcel_change_index_log_parcel', 'parcel_id'),
        Index('idx_parcel_change_index_log_down_sync', 'down_sync_id'),
    )
    
    def __repr__(self):
        return f"<ParcelChangeIndexLog {self.parcel_id}.{self.field_id} {self.action}>"

class GlobalSetting(SyncBase, db.Model):
    """Global settings for the sync process."""

    cama_cloud_state = db.Column(db.String(128), nullable=False)
    last_sync_job_id = db.Column(db.String(36))
    last_assignment_group_sync_job_id = db.Column(db.String(36))
    last_change_schema_job_id = db.Column(db.String(36))
    last_photo_download_job_id = db.Column(db.String(36))
    is_photo_meta_data_schema_sent = db.Column(db.Boolean, default=False)
    last_sync_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    last_down_sync_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    image_upload_completed_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    current_table = db.Column(db.BigInteger, default=0)
    total_tables = db.Column(db.BigInteger, default=0)
    total_photo_pages = db.Column(db.BigInteger, default=0)
    current_photo_page = db.Column(db.BigInteger, default=0)
    user_queue_run_id = db.Column(db.Integer)
    image_queue_run_id = db.Column(db.Integer)
    up_sync_queue_run_id = db.Column(db.Integer)
    assignment_group_queue_run_id = db.Column(db.Integer)
    total_number_of_lookup_tables = db.Column(db.BigInteger, default=0)
    current_lookup_tables_uploaded = db.Column(db.BigInteger, default=0)
    is_property_table_complete = db.Column(db.Boolean, default=False)
    has_photos = db.Column(db.Boolean, default=False)
    is_finalized = db.Column(db.Boolean, default=False)
    last_change_id = db.Column(db.BigInteger, default=0)
    relink_assignment_group = db.Column(db.Boolean, default=False)
    last_clean_data_job_id = db.Column(db.String(36))
    clean_data_run_id = db.Column(db.Integer)
    
    def __repr__(self):
        return f"<GlobalSetting id={self.id} state={self.cama_cloud_state}>"
        
class SyncLog(SyncBase, db.Model):
    """Detailed logs for sync operations."""
    
    job_id = db.Column(db.String(36), nullable=False)  # UUID of related job
    level = db.Column(db.String(32), nullable=False, default='INFO')  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = db.Column(db.Text, nullable=False)
    component = db.Column(db.String(128))  # Extract, Transform, Load, etc.
    table_name = db.Column(db.String(128))
    record_count = db.Column(db.Integer)
    duration_ms = db.Column(db.Integer)  # Duration in milliseconds
    
    __table_args__ = (
        Index('idx_sync_log_job_level', 'job_id', 'level'),
    )
    
    def __repr__(self):
        return f"<SyncLog {self.job_id} {self.level}: {self.message[:50]}>"