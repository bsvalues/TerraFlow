"""
Data Quality Models for MCP

This module provides SQLAlchemy models for data quality components
"""

import json
import datetime
from app import db
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Index, JSON, DateTime

# Use JSONB for PostgreSQL, fallback to JSON for other databases
try:
    JsonType = JSONB
except:
    JsonType = JSON

class QualityAlertModel(db.Model):
    """
    Database model for data quality alerts
    """
    __tablename__ = 'data_quality_alert'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    check_type = db.Column(db.String(64), nullable=False)
    parameters = db.Column(JsonType, nullable=False, default={})
    threshold = db.Column(db.Float, nullable=False, default=0.95)
    severity = db.Column(db.String(32), nullable=False, default='medium')
    notification_channels = db.Column(JsonType, nullable=False, default=["log"])
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_checked = db.Column(DateTime, nullable=True)
    last_status = db.Column(db.String(32), nullable=True)
    last_value = db.Column(db.String(128), nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    triggered_count = db.Column(db.Integer, nullable=False, default=0)
    created_date = db.Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    # Create indices
    __table_args__ = (
        Index('ix_quality_alert_check_type', 'check_type'),
        Index('ix_quality_alert_severity', 'severity')
    )
    
    def to_dict(self):
        """
        Convert model to dictionary
        """
        nc = self.notification_channels
        if isinstance(nc, str):
            nc = json.loads(nc)
            
        params = self.parameters
        if isinstance(params, str):
            params = json.loads(params)
            
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "check_type": self.check_type,
            "parameters": params,
            "threshold": self.threshold,
            "severity": self.severity,
            "notification_channels": nc,
            "enabled": self.enabled,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "last_status": self.last_status,
            "last_value": self.last_value,
            "last_error": self.last_error,
            "triggered_count": self.triggered_count,
            "created_date": self.created_date.isoformat() if self.created_date else None
        }
        
    @classmethod
    def from_dict(cls, data):
        """
        Create model from dictionary
        """
        nc = data.get('notification_channels', ['log'])
        if not isinstance(nc, str):
            nc = json.dumps(nc)
            
        params = data.get('parameters', {})
        if not isinstance(params, str):
            params = json.dumps(params)
            
        model = cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description'),
            check_type=data.get('check_type', ''),
            parameters=params,
            threshold=data.get('threshold', 0.95),
            severity=data.get('severity', 'medium'),
            notification_channels=nc,
            enabled=data.get('enabled', True),
            last_checked=data.get('last_checked'),
            last_status=data.get('last_status'),
            last_value=data.get('last_value'),
            last_error=data.get('last_error'),
            triggered_count=data.get('triggered_count', 0),
            created_date=data.get('created_date')
        )
        
        return model