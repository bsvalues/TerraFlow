"""
Validation Module

This module implements validation capabilities for data quality, consistency, and compliance.
"""

import os
import logging
import json
import datetime
import uuid
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ValidationManager:
    """
    Manager for data validation operations.
    """
    
    def __init__(self):
        """Initialize the validation manager"""
        # Validation rules by category
        self.validation_rules = {
            'property': [
                # Basic property validation rules
                {
                    'name': 'property_id_format',
                    'description': 'Validates property ID format',
                    'severity': 'error',
                    'validation_type': 'format'
                },
                {
                    'name': 'address_required',
                    'description': 'Validates property has address',
                    'severity': 'error',
                    'validation_type': 'required'
                },
                {
                    'name': 'valid_property_type',
                    'description': 'Validates property type is valid',
                    'severity': 'error',
                    'validation_type': 'enum'
                },
                {
                    'name': 'valid_zoning',
                    'description': 'Validates zoning is valid',
                    'severity': 'warning',
                    'validation_type': 'enum'
                },
                {
                    'name': 'valid_land_area',
                    'description': 'Validates land area is greater than zero',
                    'severity': 'warning',
                    'validation_type': 'range'
                }
            ],
            'assessment': [
                # Assessment validation rules
                {
                    'name': 'assessment_id_format',
                    'description': 'Validates assessment ID format',
                    'severity': 'error',
                    'validation_type': 'format'
                },
                {
                    'name': 'assessment_date_required',
                    'description': 'Validates assessment has date',
                    'severity': 'error',
                    'validation_type': 'required'
                },
                {
                    'name': 'valid_assessment_value',
                    'description': 'Validates assessment value is greater than zero',
                    'severity': 'error',
                    'validation_type': 'range'
                },
                {
                    'name': 'valid_assessment_method',
                    'description': 'Validates assessment method is valid',
                    'severity': 'warning',
                    'validation_type': 'enum'
                }
            ],
            'spatial': [
                # Spatial validation rules
                {
                    'name': 'valid_geometry',
                    'description': 'Validates geometry is valid',
                    'severity': 'error',
                    'validation_type': 'spatial'
                },
                {
                    'name': 'no_self_intersection',
                    'description': 'Validates geometry has no self-intersections',
                    'severity': 'error',
                    'validation_type': 'spatial'
                },
                {
                    'name': 'valid_topology',
                    'description': 'Validates topology is valid',
                    'severity': 'warning',
                    'validation_type': 'spatial'
                }
            ]
        }
        
        # Valid enum values
        self.valid_enums = {
            'property_type': [
                'residential_single', 'residential_multi', 'commercial',
                'industrial', 'agricultural', 'recreational', 'vacant'
            ],
            'zoning': [
                'residential', 'commercial', 'industrial', 'agricultural',
                'mixed_use', 'public', 'open_space'
            ],
            'assessment_method': [
                'market_value', 'income', 'cost', 'comparative'
            ]
        }
        
        # Initialize validation stats
        self.validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'validation_runs': [],
            'last_run': None
        }
        
        # Initialization state
        self._initialized = True
        
        logger.info("Validation Manager initialized")
    
    def is_initialized(self) -> bool:
        """
        Check if the validation manager is properly initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
    
    def validate_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate property data against defined rules.
        
        Args:
            property_data: Property data dictionary
            
        Returns:
            Validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'property_id': property_data.get('property_id')
        }
        
        # Apply each property validation rule
        for rule in self.validation_rules.get('property', []):
            self.validation_stats['total_validations'] += 1
            
            if rule['validation_type'] == 'format':
                if rule['name'] == 'property_id_format':
                    property_id = property_data.get('property_id')
                    if not property_id or not isinstance(property_id, str):
                        self._add_validation_issue(results, rule, 'Property ID missing or invalid format')
                        continue
            
            elif rule['validation_type'] == 'required':
                if rule['name'] == 'address_required':
                    address = property_data.get('address')
                    if not address:
                        self._add_validation_issue(results, rule, 'Property address is required')
                        continue
            
            elif rule['validation_type'] == 'enum':
                if rule['name'] == 'valid_property_type':
                    property_type = property_data.get('property_type')
                    if not property_type or property_type not in self.valid_enums['property_type']:
                        self._add_validation_issue(results, rule, f"Invalid property type: {property_type}")
                        continue
                
                elif rule['name'] == 'valid_zoning':
                    zoning = property_data.get('zoning')
                    if zoning and zoning not in self.valid_enums['zoning']:
                        self._add_validation_issue(results, rule, f"Invalid zoning: {zoning}")
                        continue
            
            elif rule['validation_type'] == 'range':
                if rule['name'] == 'valid_land_area':
                    land_area = property_data.get('land_area')
                    if land_area is not None and float(land_area) <= 0:
                        self._add_validation_issue(results, rule, f"Invalid land area: {land_area}")
                        continue
            
            # If we get here, the validation passed
            self.validation_stats['passed_validations'] += 1
        
        # Update overall validity
        if len(results['errors']) > 0:
            results['valid'] = False
        
        return results
    
    def validate_assessment(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate assessment data against defined rules.
        
        Args:
            assessment_data: Assessment data dictionary
            
        Returns:
            Validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'assessment_id': assessment_data.get('assessment_id')
        }
        
        # Apply each assessment validation rule
        for rule in self.validation_rules.get('assessment', []):
            self.validation_stats['total_validations'] += 1
            
            if rule['validation_type'] == 'format':
                if rule['name'] == 'assessment_id_format':
                    assessment_id = assessment_data.get('assessment_id')
                    if not assessment_id or not isinstance(assessment_id, str):
                        self._add_validation_issue(results, rule, 'Assessment ID missing or invalid format')
                        continue
            
            elif rule['validation_type'] == 'required':
                if rule['name'] == 'assessment_date_required':
                    assessment_date = assessment_data.get('assessment_date')
                    if not assessment_date:
                        self._add_validation_issue(results, rule, 'Assessment date is required')
                        continue
            
            elif rule['validation_type'] == 'range':
                if rule['name'] == 'valid_assessment_value':
                    assessment_value = assessment_data.get('value')
                    if assessment_value is None or float(assessment_value) <= 0:
                        self._add_validation_issue(results, rule, f"Invalid assessment value: {assessment_value}")
                        continue
            
            elif rule['validation_type'] == 'enum':
                if rule['name'] == 'valid_assessment_method':
                    method = assessment_data.get('method')
                    if method and method not in self.valid_enums['assessment_method']:
                        self._add_validation_issue(results, rule, f"Invalid assessment method: {method}")
                        continue
            
            # If we get here, the validation passed
            self.validation_stats['passed_validations'] += 1
        
        # Update overall validity
        if len(results['errors']) > 0:
            results['valid'] = False
        
        return results
    
    def validate_spatial(self, spatial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate spatial data against defined rules.
        
        Args:
            spatial_data: Spatial data dictionary
            
        Returns:
            Validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'property_id': spatial_data.get('property_id')
        }
        
        try:
            # Import shapely for geometry validation
            from shapely.geometry import shape
            from shapely.validation import explain_validity
            
            # Get the geometry
            geometry = spatial_data.get('geometry')
            if not geometry:
                results['valid'] = False
                results['errors'].append({
                    'rule': 'geometry_required',
                    'description': 'Geometry is required',
                    'severity': 'error'
                })
                return results
            
            # Convert to shapely geometry
            try:
                if isinstance(geometry, dict):
                    geom = shape(geometry)
                else:
                    geom = geometry
                
                # Apply each spatial validation rule
                for rule in self.validation_rules.get('spatial', []):
                    self.validation_stats['total_validations'] += 1
                    
                    if rule['validation_type'] == 'spatial':
                        if rule['name'] == 'valid_geometry':
                            if not geom.is_valid:
                                reason = explain_validity(geom)
                                self._add_validation_issue(results, rule, f"Invalid geometry: {reason}")
                                continue
                        
                        elif rule['name'] == 'no_self_intersection':
                            if hasattr(geom, 'is_simple') and not geom.is_simple:
                                self._add_validation_issue(results, rule, "Geometry has self-intersections")
                                continue
                        
                        elif rule['name'] == 'valid_topology':
                            # Basic topology checks (would be more comprehensive in real implementation)
                            if geom.is_empty:
                                self._add_validation_issue(results, rule, "Geometry is empty")
                                continue
                            
                            if hasattr(geom, 'area') and geom.area <= 0:
                                self._add_validation_issue(results, rule, "Geometry has zero area")
                                continue
                    
                    # If we get here, the validation passed
                    self.validation_stats['passed_validations'] += 1
            
            except Exception as e:
                results['valid'] = False
                results['errors'].append({
                    'rule': 'geometry_parsing',
                    'description': f"Error parsing geometry: {str(e)}",
                    'severity': 'error'
                })
                self.validation_stats['failed_validations'] += 1
                
        except ImportError:
            # Shapely not available, skip spatial validation
            results['warnings'].append({
                'rule': 'spatial_validation_skipped',
                'description': "Spatial validation skipped, shapely library not available",
                'severity': 'warning'
            })
        
        # Update overall validity
        if len(results['errors']) > 0:
            results['valid'] = False
        
        return results
    
    def validate_batch(self, data_type: str, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of records of the same type.
        
        Args:
            data_type: Type of data to validate ('property', 'assessment', 'spatial')
            data_list: List of data dictionaries
            
        Returns:
            Batch validation results
        """
        start_time = datetime.datetime.now()
        
        results = {
            'data_type': data_type,
            'total_records': len(data_list),
            'valid_records': 0,
            'invalid_records': 0,
            'validation_details': [],
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration_seconds': 0
        }
        
        # Select the appropriate validation method
        validation_method = None
        if data_type == 'property':
            validation_method = self.validate_property
        elif data_type == 'assessment':
            validation_method = self.validate_assessment
        elif data_type == 'spatial':
            validation_method = self.validate_spatial
        else:
            results['error'] = f"Unknown data type: {data_type}"
            return results
        
        # Validate each record
        for item in data_list:
            validation_result = validation_method(item)
            results['validation_details'].append(validation_result)
            
            if validation_result['valid']:
                results['valid_records'] += 1
            else:
                results['invalid_records'] += 1
        
        # Complete the results
        end_time = datetime.datetime.now()
        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = (end_time - start_time).total_seconds()
        
        # Update validation stats
        self.validation_stats['last_run'] = end_time.isoformat()
        self.validation_stats['validation_runs'].append({
            'timestamp': end_time.isoformat(),
            'data_type': data_type,
            'total_records': results['total_records'],
            'valid_records': results['valid_records'],
            'invalid_records': results['invalid_records']
        })
        
        # Limit the number of validation runs stored
        if len(self.validation_stats['validation_runs']) > 100:
            self.validation_stats['validation_runs'] = self.validation_stats['validation_runs'][-100:]
        
        return results
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics.
        
        Returns:
            Dictionary of validation statistics
        """
        return self.validation_stats
    
    def add_validation_rule(self, category: str, rule: Dict[str, Any]) -> bool:
        """
        Add a custom validation rule.
        
        Args:
            category: Rule category ('property', 'assessment', 'spatial')
            rule: Rule definition
            
        Returns:
            True if rule was added, False otherwise
        """
        if category not in self.validation_rules:
            self.validation_rules[category] = []
        
        # Check if rule with this name already exists
        for existing_rule in self.validation_rules[category]:
            if existing_rule['name'] == rule['name']:
                # Update existing rule
                existing_rule.update(rule)
                logger.info(f"Updated validation rule: {rule['name']}")
                return True
        
        # Add new rule
        self.validation_rules[category].append(rule)
        logger.info(f"Added new validation rule: {rule['name']}")
        return True
    
    def _add_validation_issue(self, results: Dict[str, Any], rule: Dict[str, Any], message: str) -> None:
        """
        Add a validation issue to results.
        
        Args:
            results: Results dictionary to update
            rule: Rule that triggered the issue
            message: Issue message
        """
        issue = {
            'rule': rule['name'],
            'description': message,
            'severity': rule['severity']
        }
        
        if rule['severity'] == 'error':
            results['errors'].append(issue)
        else:
            results['warnings'].append(issue)
        
        self.validation_stats['failed_validations'] += 1

# Create singleton instance
validation_manager = ValidationManager()