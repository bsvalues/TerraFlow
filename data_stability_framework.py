"""
Data Stability and Security Framework

This module integrates all components of the comprehensive data stability
and security framework for the Benton County Washington Assessor's Office.
It provides a unified interface to access the various subsystems and features.
"""

import os
import logging
import json
import datetime
from typing import Dict, List, Any, Optional, Union, Tuple

# Import all framework components
from data_governance.data_classification import classification_manager
from data_governance.data_sovereignty import sovereignty_manager
from security.encryption import encryption_manager
from security.access_control import access_control_manager
from security.monitoring import security_monitor, audit_logger
from data_conversion.conversion_controls import conversion_manager
from disaster_recovery.recovery_manager import recovery_manager

logger = logging.getLogger(__name__)

class DataStabilityFramework:
    """
    Master controller for the data stability and security framework.
    Provides a unified interface to access and coordinate all framework components.
    """
    
    def __init__(self):
        """Initialize the framework"""
        # Framework components
        self.classification = classification_manager
        self.sovereignty = sovereignty_manager
        self.encryption = encryption_manager
        self.access_control = access_control_manager
        self.security_monitor = security_monitor
        self.audit = audit_logger
        self.conversion = conversion_manager
        self.recovery = recovery_manager
        
        # Framework configuration
        self.config = {
            'framework_version': '1.0.0',
            'environment': os.environ.get('ENV', 'development'),
            'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
            'components_enabled': {
                'classification': True,
                'sovereignty': True,
                'encryption': True,
                'access_control': True,
                'security_monitoring': True,
                'audit_logging': True,
                'conversion_controls': True,
                'disaster_recovery': True
            }
        }
        
        # Initialize framework
        self._initialize_framework()
        
        logger.info("Data Stability and Security Framework initialized")
    
    def _initialize_framework(self):
        """Initialize the framework components"""
        # Set up logging
        log_level = getattr(logging, self.config['log_level'], logging.INFO)
        logging.basicConfig(level=log_level)
        
        # Load additional configuration if available
        self._load_framework_config()
        
        # Disable components if needed
        for component, enabled in self.config['components_enabled'].items():
            if not enabled:
                logger.warning(f"Component disabled: {component}")
    
    def _load_framework_config(self):
        """Load framework configuration from file if available"""
        config_file = os.environ.get('FRAMEWORK_CONFIG', 'framework_config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # Update configuration
                    self.config.update(config)
                logger.info(f"Loaded framework configuration from {config_file}")
            except Exception as e:
                logger.error(f"Error loading framework configuration: {str(e)}")
    
    def encrypt_sensitive_data(self, data: Dict[str, Any], 
                              table_name: str) -> Dict[str, Any]:
        """
        Encrypt sensitive data based on classification.
        
        Args:
            data: Dictionary of field names and values
            table_name: Database table name
            
        Returns:
            Data with sensitive fields encrypted
        """
        if not self.config['components_enabled']['encryption']:
            logger.warning("Encryption component is disabled")
            return data
        
        result = {}
        
        for field_name, value in data.items():
            # Get classification level
            sensitivity = self.classification.get_field_classification(table_name, field_name)
            
            # Encrypt based on sensitivity level
            if sensitivity.value >= 3:  # CONFIDENTIAL or RESTRICTED
                if value is not None:
                    # Encrypt the field value
                    encrypted_value = self.encryption.encrypt_field(value, field_name, table_name)
                    result[field_name] = encrypted_value
                else:
                    result[field_name] = None
            else:
                # No encryption needed
                result[field_name] = value
        
        return result
    
    def decrypt_sensitive_data(self, data: Dict[str, Any], 
                              table_name: str) -> Dict[str, Any]:
        """
        Decrypt sensitive data.
        
        Args:
            data: Dictionary of field names and values
            table_name: Database table name
            
        Returns:
            Data with sensitive fields decrypted
        """
        if not self.config['components_enabled']['encryption']:
            logger.warning("Encryption component is disabled")
            return data
        
        result = {}
        
        for field_name, value in data.items():
            # Get classification level
            sensitivity = self.classification.get_field_classification(table_name, field_name)
            
            # Decrypt based on sensitivity level
            if sensitivity.value >= 3 and value is not None:  # CONFIDENTIAL or RESTRICTED
                try:
                    # Check if the value is encrypted (JSON string)
                    if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                        try:
                            # Try to parse as JSON
                            json.loads(value)
                            # Decrypt the field value
                            decrypted_value = self.encryption.decrypt_field(value)
                            result[field_name] = decrypted_value
                        except json.JSONDecodeError:
                            # Not valid JSON, just a regular string
                            result[field_name] = value
                    else:
                        # Not encrypted
                        result[field_name] = value
                except Exception as e:
                    logger.error(f"Error decrypting field {field_name}: {str(e)}")
                    # Return original value if decryption fails
                    result[field_name] = value
            else:
                # No decryption needed
                result[field_name] = value
        
        return result
    
    def check_access_permission(self, user_id: int, permission: str, 
                              context: Dict[str, Any] = None) -> bool:
        """
        Check if a user has permission to perform an action.
        
        Args:
            user_id: User ID
            permission: Permission to check
            context: Additional context for attribute-based access control
            
        Returns:
            True if access is permitted, False otherwise
        """
        if not self.config['components_enabled']['access_control']:
            logger.warning("Access control component is disabled")
            return True
        
        return self.access_control.has_permission(user_id, permission, context)
    
    def apply_data_masking(self, user_id: int, data: Dict[str, Any], 
                          table_name: str) -> Dict[str, Any]:
        """
        Apply data masking based on user permissions.
        
        Args:
            user_id: User ID
            data: Dictionary of field names and values
            table_name: Database table name
            
        Returns:
            Data with sensitive fields masked if user lacks permission
        """
        if not self.config['components_enabled']['classification'] or \
           not self.config['components_enabled']['access_control']:
            logger.warning("Classification or access control component is disabled")
            return data
        
        # Get user permissions
        user_roles = self.access_control.get_user_roles(user_id)
        user_permissions = self.access_control.get_role_permissions(user_roles)
        
        # Apply masking
        masked_data = self.classification.mask_sensitive_data(table_name, data, user_permissions)
        
        return masked_data
    
    def log_security_event(self, event_type: str, user_id: int, 
                          details: Dict[str, Any]) -> None:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            user_id: User ID associated with the event
            details: Event details
        """
        if not self.config['components_enabled']['audit_logging']:
            logger.warning("Audit logging component is disabled")
            return
        
        # Determine category based on event type
        if event_type.startswith('auth_'):
            category = 'user_authentication'
        elif event_type.startswith('data_'):
            category = 'data_access'
        elif event_type.startswith('admin_'):
            category = 'administrative'
        elif event_type.startswith('security_'):
            category = 'security_events'
        else:
            category = 'system_events'
        
        # Log the event
        self.audit.log_event(category, event_type, user_id, details)
        
        # Also log to security monitor if it's a security-relevant event
        if category in ['user_authentication', 'data_access', 'administrative', 'security_events']:
            activity_type = category
            activity_subtype = event_type
            
            ip_address = details.get('ip_address')
            source = details.get('source')
            
            self.security_monitor.log_activity(
                activity_type, activity_subtype, user_id, details, ip_address, source)
    
    def verify_data_sovereignty(self, storage_region: str, 
                              data_sensitivity: str) -> bool:
        """
        Verify that data storage complies with sovereignty requirements.
        
        Args:
            storage_region: Storage region or location
            data_sensitivity: Data sensitivity level
            
        Returns:
            True if compliant, False otherwise
        """
        if not self.config['components_enabled']['sovereignty']:
            logger.warning("Data sovereignty component is disabled")
            return True
        
        is_compliant, reason = self.sovereignty.verify_storage_compliance(storage_region, data_sensitivity)
        
        if not is_compliant:
            logger.warning(f"Data sovereignty violation: {reason}")
        
        return is_compliant
    
    def start_data_conversion(self, source_type: str, target_type: str, 
                             source_data: Any, validation_level: str = 'standard', 
                             error_handling: str = 'abort_on_error') -> str:
        """
        Start a data conversion job with all security controls applied.
        
        Args:
            source_type: Source data type or format
            target_type: Target data type or format
            source_data: Source data to convert
            validation_level: Validation level ('minimal', 'standard', 'strict')
            error_handling: Error handling mode
            
        Returns:
            Job ID for tracking
        """
        if not self.config['components_enabled']['conversion_controls']:
            logger.warning("Conversion controls component is disabled")
            return None
        
        # Register the conversion job
        job_id = self.conversion.register_conversion_job(
            source_type, target_type, validation_level, error_handling,
            f"Convert from {source_type} to {target_type}"
        )
        
        if not job_id:
            logger.error("Failed to register conversion job")
            return None
        
        # Start the conversion
        success = self.conversion.start_conversion_job(job_id, source_data)
        
        if not success:
            logger.error(f"Failed to start conversion job {job_id}")
            return None
        
        logger.info(f"Started conversion job {job_id}: {source_type} to {target_type}")
        return job_id
    
    def create_backup(self, backup_type: str, source: str, 
                     priority: str = 'normal') -> str:
        """
        Create a backup with all security controls applied.
        
        Args:
            backup_type: Type of backup ('database', 'files', 'configuration')
            source: Source to backup
            priority: Backup priority ('critical', 'important', 'normal', 'archival')
            
        Returns:
            Backup ID for tracking
        """
        if not self.config['components_enabled']['disaster_recovery']:
            logger.warning("Disaster recovery component is disabled")
            return None
        
        # Create the backup
        backup_id = self.recovery.create_backup(backup_type, source, priority)
        
        if not backup_id:
            logger.error(f"Failed to create {backup_type} backup for {source}")
            return None
        
        # Log the backup event
        self.log_security_event('backup_created', 0, {
            'backup_id': backup_id,
            'backup_type': backup_type,
            'source': source,
            'priority': priority
        })
        
        logger.info(f"Created backup {backup_id} for {source}")
        return backup_id
    
    def generate_security_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive security report.
        
        Returns:
            Dictionary with security report data
        """
        # Get current timestamp
        timestamp = datetime.datetime.now()
        
        # Generate report ID
        report_id = f"security_report_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize report data
        report = {
            'id': report_id,
            'generated_at': timestamp.isoformat(),
            'framework_version': self.config['framework_version'],
            'environment': self.config['environment'],
            'components': {}
        }
        
        # Get component status
        for component, enabled in self.config['components_enabled'].items():
            report['components'][component] = {
                'enabled': enabled,
                'status': 'active' if enabled else 'disabled'
            }
        
        # Get recovery readiness
        if self.config['components_enabled']['disaster_recovery']:
            readiness_result = self.recovery.analyze_recovery_readiness()
            if readiness_result['success']:
                report['recovery_readiness'] = readiness_result['report']
        
        # Save report to file
        os.makedirs('reports', exist_ok=True)
        report_file = os.path.join('reports', f"{report_id}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Generated security report: {report_id}")
        return report

# Create a singleton instance
framework = DataStabilityFramework()