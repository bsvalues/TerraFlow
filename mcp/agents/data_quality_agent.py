"""
Data Quality Agent for GeoAssessmentPro

This agent is responsible for proactive data quality monitoring, validation, and anomaly detection.
It works alongside the Data Sanitization Framework to ensure data integrity throughout the system.
"""

import os
import logging
import datetime
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import text, exc, inspect
from app import db
from mcp.base_agent import BaseAgent
from sync_service.notification_system import SyncNotificationManager
from sync_service.data_sanitization import DataSanitizer

# Configure logging
logger = logging.getLogger(__name__)

class DataQualityAgent(BaseAgent):
    """
    Data Quality Agent for monitoring and validating data quality across the system.
    
    Features:
    - Proactive data validation before sync operations
    - Statistical anomaly detection in property records
    - Data completeness and consistency checks
    - Custom validation rules for GIS datasets
    """
    
    def __init__(self):
        """Initialize the Data Quality Agent"""
        super().__init__("data_quality")
        self.notification_manager = SyncNotificationManager()
        self.data_sanitizer = DataSanitizer()
        self.validation_rules = {}
        self.anomaly_thresholds = {}
        self.load_configuration()
        logger.info(f"Agent {self.agent_id} initialized")
    
    def load_configuration(self):
        """Load configuration settings for data quality checks"""
        try:
            # Default configuration - in production, this would be loaded from database
            self.validation_rules = {
                "owner": {
                    "required_fields": ["id", "name"],
                    "format_rules": {
                        "email": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
                        "phone": r"^\d{3}-\d{3}-\d{4}$"
                    },
                    "value_ranges": {}
                },
                "property": {
                    "required_fields": ["id", "parcel_id", "address"],
                    "format_rules": {
                        "parcel_id": r"^\d{2}-\d{2}-\d{2}-\d{3}-\d{4}$",
                        "zip_code": r"^\d{5}(-\d{4})?$"
                    },
                    "value_ranges": {
                        "land_value": (0, None),  # Min value 0, no max
                        "year_built": (1800, datetime.datetime.now().year)
                    }
                }
            }
            
            self.anomaly_thresholds = {
                "property": {
                    "land_value_change_pct": 0.5,  # Flag changes over 50%
                    "building_value_change_pct": 0.5
                }
            }
            
            logger.info("Data quality configuration loaded")
        except Exception as e:
            logger.error(f"Error loading data quality configuration: {str(e)}")
    
    def process_task(self, task_data):
        """Process a data quality task"""
        logger.info(f"Processing task: {task_data.get('task_type', 'unknown')}")
        
        task_type = task_data.get("task_type")
        result = {"success": False, "message": "Unknown task type"}
        
        try:
            if task_type == "validate_table":
                table_name = task_data.get("table_name")
                result = self.validate_table(table_name)
            
            elif task_type == "detect_anomalies":
                table_name = task_data.get("table_name")
                result = self.detect_anomalies(table_name)
            
            elif task_type == "check_consistency":
                tables = task_data.get("tables", [])
                result = self.check_referential_consistency(tables)
            
            elif task_type == "validate_field_values":
                table_name = task_data.get("table_name")
                field_name = task_data.get("field_name")
                values = task_data.get("values", [])
                result = self.validate_field_values(table_name, field_name, values)
            
            elif task_type == "validate_gis_data":
                file_path = task_data.get("file_path")
                result = self.validate_gis_data(file_path)
            
            else:
                result = {"success": False, "message": f"Unknown task type: {task_type}"}
        
        except Exception as e:
            logger.error(f"Error processing task: {str(e)}")
            result = {"success": False, "message": f"Error: {str(e)}"}
        
        return result
    
    def validate_table(self, table_name: str) -> Dict[str, Any]:
        """
        Validate an entire database table against defined rules
        
        Args:
            table_name: Name of the table to validate
            
        Returns:
            Dict containing validation results
        """
        logger.info(f"Validating table: {table_name}")
        
        if table_name not in self.validation_rules:
            return {
                "success": False,
                "message": f"No validation rules defined for table: {table_name}"
            }
        
        try:
            # Get table rules
            rules = self.validation_rules[table_name]
            required_fields = rules.get("required_fields", [])
            format_rules = rules.get("format_rules", {})
            value_ranges = rules.get("value_ranges", {})
            
            # Query sample data to validate
            query = text(f"SELECT * FROM {table_name} LIMIT 1000")
            result = db.session.execute(query)
            
            columns = result.keys()
            records = [dict(zip(columns, row)) for row in result.fetchall()]
            
            if not records:
                return {
                    "success": True,
                    "message": f"No records found in {table_name}",
                    "issues": []
                }
            
            # Check for required fields
            missing_fields = [field for field in required_fields if field not in columns]
            
            # Validate records
            issues = []
            
            for i, record in enumerate(records):
                record_issues = []
                
                # Check required fields have values
                for field in required_fields:
                    if field in record and (record[field] is None or record[field] == ""):
                        record_issues.append({
                            "type": "missing_required_value",
                            "field": field,
                            "message": f"Required field '{field}' has no value"
                        })
                
                # Check format rules
                for field, pattern in format_rules.items():
                    if field in record and record[field] and isinstance(record[field], str):
                        import re
                        if not re.match(pattern, record[field]):
                            record_issues.append({
                                "type": "invalid_format",
                                "field": field,
                                "value": record[field],
                                "message": f"Field '{field}' has invalid format"
                            })
                
                # Check value ranges
                for field, (min_val, max_val) in value_ranges.items():
                    if field in record and record[field] is not None:
                        value = record[field]
                        if min_val is not None and value < min_val:
                            record_issues.append({
                                "type": "out_of_range",
                                "field": field,
                                "value": value,
                                "message": f"Field '{field}' is below minimum value {min_val}"
                            })
                        if max_val is not None and value > max_val:
                            record_issues.append({
                                "type": "out_of_range",
                                "field": field,
                                "value": value,
                                "message": f"Field '{field}' is above maximum value {max_val}"
                            })
                
                if record_issues:
                    issues.append({
                        "record_id": record.get("id", i),
                        "issues": record_issues
                    })
            
            # Prepare results
            success = len(missing_fields) == 0 and len(issues) == 0
            
            if not success:
                # Send notification if issues found
                self.notification_manager.send_notification(
                    level="warning" if issues else "info",
                    title=f"Data Quality Issues in {table_name}",
                    message=f"Found {len(issues)} records with issues in {table_name}",
                    metadata={
                        "table": table_name,
                        "missing_fields": missing_fields,
                        "issue_count": len(issues)
                    }
                )
            
            return {
                "success": success,
                "message": f"Validation completed for {table_name}",
                "missing_fields": missing_fields,
                "records_checked": len(records),
                "issues_found": len(issues),
                "issues": issues[:50]  # Limit number of issues returned
            }
            
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error validating {table_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error validating {table_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    def detect_anomalies(self, table_name: str) -> Dict[str, Any]:
        """
        Detect anomalies in data using statistical methods
        
        Args:
            table_name: Name of the table to analyze
            
        Returns:
            Dict containing detected anomalies
        """
        logger.info(f"Detecting anomalies in table: {table_name}")
        
        if table_name not in self.anomaly_thresholds:
            return {
                "success": False,
                "message": f"No anomaly thresholds defined for table: {table_name}"
            }
        
        try:
            thresholds = self.anomaly_thresholds[table_name]
            
            # For property table, check for unusual value changes
            if table_name == "property":
                # Query current and historical property values
                query = text("""
                    SELECT p.id, p.parcel_id, p.land_value, p.building_value, 
                           h.land_value as prev_land_value,
                           h.building_value as prev_building_value
                    FROM property p
                    JOIN property_history h ON p.id = h.property_id
                    WHERE h.timestamp = (
                        SELECT MAX(timestamp) 
                        FROM property_history
                        WHERE property_id = p.id
                    )
                    LIMIT 1000
                """)
                
                result = db.session.execute(query)
                records = [dict(zip(result.keys(), row)) for row in result.fetchall()]
                
                anomalies = []
                
                for record in records:
                    record_anomalies = []
                    
                    # Check land value changes
                    if (record.get('land_value') and record.get('prev_land_value') and 
                        record['prev_land_value'] > 0):
                        change_pct = abs(record['land_value'] - record['prev_land_value']) / record['prev_land_value']
                        
                        if change_pct > thresholds.get('land_value_change_pct', 0.5):
                            record_anomalies.append({
                                "type": "unusual_value_change",
                                "field": "land_value",
                                "current": record['land_value'],
                                "previous": record['prev_land_value'],
                                "change_pct": round(change_pct * 100, 2),
                                "message": f"Unusual land value change of {round(change_pct * 100, 2)}%"
                            })
                    
                    # Check building value changes
                    if (record.get('building_value') and record.get('prev_building_value') and 
                        record['prev_building_value'] > 0):
                        change_pct = abs(record['building_value'] - record['prev_building_value']) / record['prev_building_value']
                        
                        if change_pct > thresholds.get('building_value_change_pct', 0.5):
                            record_anomalies.append({
                                "type": "unusual_value_change",
                                "field": "building_value",
                                "current": record['building_value'],
                                "previous": record['prev_building_value'],
                                "change_pct": round(change_pct * 100, 2),
                                "message": f"Unusual building value change of {round(change_pct * 100, 2)}%"
                            })
                    
                    if record_anomalies:
                        anomalies.append({
                            "record_id": record.get("id"),
                            "parcel_id": record.get("parcel_id"),
                            "anomalies": record_anomalies
                        })
                
                # Send notification if anomalies found
                if anomalies:
                    self.notification_manager.send_notification(
                        level="warning",
                        title=f"Data Anomalies Detected in {table_name}",
                        message=f"Found {len(anomalies)} records with unusual value changes",
                        metadata={
                            "table": table_name,
                            "anomaly_count": len(anomalies)
                        }
                    )
                
                return {
                    "success": True,
                    "message": f"Anomaly detection completed for {table_name}",
                    "records_checked": len(records),
                    "anomalies_found": len(anomalies),
                    "anomalies": anomalies[:50]  # Limit number of anomalies returned
                }
            
            # For other tables, implement appropriate anomaly detection
            return {
                "success": True,
                "message": f"No anomaly detection implemented for {table_name}",
                "anomalies_found": 0
            }
            
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error detecting anomalies in {table_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error detecting anomalies in {table_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    def check_referential_consistency(self, tables: List[str]) -> Dict[str, Any]:
        """
        Check referential consistency between related tables
        
        Args:
            tables: List of tables to check
            
        Returns:
            Dict containing consistency check results
        """
        logger.info(f"Checking referential consistency between tables: {tables}")
        
        if not tables or len(tables) < 2:
            return {
                "success": False,
                "message": "At least two tables are required for consistency check"
            }
        
        try:
            # Get table relationships from inspection
            inspector = inspect(db.engine)
            relationships = {}
            
            for table in tables:
                foreign_keys = inspector.get_foreign_keys(table)
                relationships[table] = foreign_keys
            
            # Check for orphaned records
            consistency_issues = []
            
            for table, fks in relationships.items():
                for fk in fks:
                    if fk["referred_table"] in tables:
                        # Check for orphaned records
                        constrained_columns = ", ".join(fk["constrained_columns"])
                        referred_columns = ", ".join(fk["referred_columns"])
                        
                        query = text(f"""
                            SELECT COUNT(*) as orphan_count
                            FROM {table} t
                            LEFT JOIN {fk["referred_table"]} r 
                                ON t.{constrained_columns} = r.{referred_columns}
                            WHERE r.{referred_columns} IS NULL
                        """)
                        
                        result = db.session.execute(query).fetchone()
                        orphan_count = result["orphan_count"] if result else 0
                        
                        if orphan_count > 0:
                            issue = {
                                "type": "orphaned_records",
                                "source_table": table,
                                "referenced_table": fk["referred_table"],
                                "source_column": constrained_columns,
                                "referenced_column": referred_columns,
                                "orphan_count": orphan_count,
                                "message": f"Found {orphan_count} orphaned records in {table} referencing {fk['referred_table']}"
                            }
                            consistency_issues.append(issue)
            
            # Send notification if issues found
            if consistency_issues:
                self.notification_manager.send_notification(
                    level="warning",
                    title="Referential Consistency Issues",
                    message=f"Found {len(consistency_issues)} referential consistency issues between tables",
                    metadata={
                        "tables": tables,
                        "issue_count": len(consistency_issues)
                    }
                )
            
            return {
                "success": True,
                "message": "Referential consistency check completed",
                "tables_checked": tables,
                "issues_found": len(consistency_issues),
                "issues": consistency_issues
            }
            
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error checking consistency: {str(e)}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error checking consistency: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    def validate_field_values(self, table_name: str, field_name: str, values: List[Any]) -> Dict[str, Any]:
        """
        Validate specific field values against defined rules
        
        Args:
            table_name: Name of the table containing the field
            field_name: Name of the field to validate
            values: List of values to validate
            
        Returns:
            Dict containing validation results
        """
        logger.info(f"Validating field values: {table_name}.{field_name}")
        
        if table_name not in self.validation_rules:
            return {
                "success": False,
                "message": f"No validation rules defined for table: {table_name}"
            }
        
        try:
            rules = self.validation_rules[table_name]
            format_rules = rules.get("format_rules", {})
            value_ranges = rules.get("value_ranges", {})
            
            is_required = field_name in rules.get("required_fields", [])
            format_pattern = format_rules.get(field_name)
            value_range = value_ranges.get(field_name)
            
            validation_results = []
            
            for i, value in enumerate(values):
                issues = []
                
                # Check required value
                if is_required and (value is None or value == ""):
                    issues.append({
                        "type": "missing_required_value",
                        "message": f"Required field '{field_name}' has no value"
                    })
                
                # Check format
                if format_pattern and value and isinstance(value, str):
                    import re
                    if not re.match(format_pattern, value):
                        issues.append({
                            "type": "invalid_format",
                            "message": f"Value '{value}' has invalid format"
                        })
                
                # Check value range
                if value_range and value is not None:
                    min_val, max_val = value_range
                    if min_val is not None and value < min_val:
                        issues.append({
                            "type": "out_of_range",
                            "message": f"Value {value} is below minimum value {min_val}"
                        })
                    if max_val is not None and value > max_val:
                        issues.append({
                            "type": "out_of_range",
                            "message": f"Value {value} is above maximum value {max_val}"
                        })
                
                # Additionally, check for data type consistency
                if value is not None:
                    # Get the expected data type from database schema
                    column_info = next((col for col in inspect(db.engine).get_columns(table_name) 
                                     if col["name"] == field_name), None)
                    
                    if column_info:
                        expected_type = column_info["type"]
                        # This is a basic check and might need refinement for complex types
                        if expected_type.python_type != type(value):
                            issues.append({
                                "type": "invalid_data_type",
                                "message": f"Value '{value}' has type {type(value).__name__}, expected {expected_type.python_type.__name__}"
                            })
                
                validation_results.append({
                    "value": value,
                    "is_valid": len(issues) == 0,
                    "issues": issues
                })
            
            invalid_count = sum(1 for result in validation_results if not result["is_valid"])
            
            return {
                "success": True,
                "message": f"Validation completed for {table_name}.{field_name}",
                "values_checked": len(values),
                "invalid_values": invalid_count,
                "validation_results": validation_results
            }
            
        except Exception as e:
            logger.error(f"Error validating field values: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    def validate_gis_data(self, file_path: str) -> Dict[str, Any]:
        """
        Validate GIS data file for quality and consistency
        
        Args:
            file_path: Path to the GIS data file
            
        Returns:
            Dict containing validation results
        """
        logger.info(f"Validating GIS data file: {file_path}")
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File not found: {file_path}"
            }
        
        try:
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # GeoJSON validation
            if file_ext == '.geojson':
                with open(file_path, 'r') as f:
                    geojson_data = json.load(f)
                
                # Basic structure validation
                if not isinstance(geojson_data, dict):
                    return {"success": False, "message": "Invalid GeoJSON: root must be an object"}
                
                if "type" not in geojson_data:
                    return {"success": False, "message": "Invalid GeoJSON: missing 'type' property"}
                
                if geojson_data["type"] not in ["FeatureCollection", "Feature"]:
                    return {"success": False, "message": f"Invalid GeoJSON type: {geojson_data['type']}"}
                
                # Check features
                features = []
                if geojson_data["type"] == "FeatureCollection":
                    if "features" not in geojson_data:
                        return {"success": False, "message": "Invalid FeatureCollection: missing 'features' array"}
                    features = geojson_data["features"]
                else:  # Feature
                    features = [geojson_data]
                
                issues = []
                feature_count = len(features)
                
                # Check each feature
                for i, feature in enumerate(features):
                    feature_issues = []
                    
                    if "geometry" not in feature:
                        feature_issues.append({
                            "type": "missing_geometry",
                            "message": "Feature missing 'geometry' property"
                        })
                    elif not isinstance(feature["geometry"], dict):
                        feature_issues.append({
                            "type": "invalid_geometry",
                            "message": "Feature 'geometry' must be an object"
                        })
                    elif "type" not in feature["geometry"]:
                        feature_issues.append({
                            "type": "invalid_geometry",
                            "message": "Geometry missing 'type' property"
                        })
                    elif "coordinates" not in feature["geometry"]:
                        feature_issues.append({
                            "type": "invalid_geometry",
                            "message": "Geometry missing 'coordinates' property"
                        })
                    
                    if "properties" not in feature:
                        feature_issues.append({
                            "type": "missing_properties",
                            "message": "Feature missing 'properties' property"
                        })
                    
                    if feature_issues:
                        issues.append({
                            "feature_index": i,
                            "issues": feature_issues
                        })
                
                # Validate geometry
                invalid_geometry_count = 0
                empty_geometry_count = 0
                
                for feature in features:
                    if "geometry" not in feature or not isinstance(feature["geometry"], dict):
                        continue
                    
                    if feature["geometry"] is None:
                        empty_geometry_count += 1
                        continue
                        
                    geom_type = feature["geometry"].get("type")
                    coordinates = feature["geometry"].get("coordinates")
                    
                    if not coordinates:
                        empty_geometry_count += 1
                    elif geom_type == "Point" and not isinstance(coordinates, list):
                        invalid_geometry_count += 1
                    elif geom_type in ["LineString", "MultiPoint"] and not (
                        isinstance(coordinates, list) and all(isinstance(p, list) for p in coordinates)
                    ):
                        invalid_geometry_count += 1
                    elif geom_type in ["Polygon", "MultiLineString"] and not (
                        isinstance(coordinates, list) and 
                        all(isinstance(r, list) and all(isinstance(p, list) for p in r) for r in coordinates)
                    ):
                        invalid_geometry_count += 1
                
                return {
                    "success": len(issues) == 0 and invalid_geometry_count == 0,
                    "message": "GeoJSON validation completed",
                    "file_type": "GeoJSON",
                    "feature_count": feature_count,
                    "issues_found": len(issues),
                    "invalid_geometry_count": invalid_geometry_count,
                    "empty_geometry_count": empty_geometry_count,
                    "issues": issues[:50]  # Limit number of issues returned
                }
            
            # Shapefile validation
            elif file_ext == '.shp':
                try:
                    import geopandas as gpd
                    gdf = gpd.read_file(file_path)
                    
                    feature_count = len(gdf)
                    empty_geometry_count = gdf.geometry.isna().sum()
                    invalid_geometry_count = 0
                    
                    # Check for invalid geometries
                    for geom in gdf.geometry:
                        if geom is not None and not geom.is_valid:
                            invalid_geometry_count += 1
                    
                    return {
                        "success": invalid_geometry_count == 0,
                        "message": "Shapefile validation completed",
                        "file_type": "Shapefile",
                        "feature_count": feature_count,
                        "column_count": len(gdf.columns) - 1,  # Excluding geometry column
                        "columns": list(gdf.columns),
                        "empty_geometry_count": empty_geometry_count,
                        "invalid_geometry_count": invalid_geometry_count
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "message": f"Error validating shapefile: {str(e)}",
                        "file_type": "Shapefile"
                    }
            
            # Other file types - basic validation
            else:
                return {
                    "success": False,
                    "message": f"Unsupported GIS file type: {file_ext}",
                    "file_type": file_ext
                }
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in GeoJSON file: {str(e)}")
            return {
                "success": False,
                "message": f"Invalid JSON: {str(e)}",
                "file_type": "GeoJSON"
            }
        except Exception as e:
            logger.error(f"Error validating GIS data: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    def run_data_quality_report(self, tables: List[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive data quality report for specified tables
        
        Args:
            tables: List of tables to include in the report (None for all)
            
        Returns:
            Dict containing the data quality report
        """
        logger.info(f"Generating data quality report for tables: {tables}")
        
        try:
            # If no tables specified, get all tables with validation rules
            if tables is None:
                tables = list(self.validation_rules.keys())
            
            report = {
                "timestamp": datetime.datetime.now().isoformat(),
                "tables_checked": tables,
                "table_reports": {},
                "overall_quality_score": None,
                "critical_issues": []
            }
            
            total_records = 0
            total_issues = 0
            
            # Check each table
            for table in tables:
                if table not in self.validation_rules:
                    report["table_reports"][table] = {
                        "status": "skipped",
                        "message": "No validation rules defined"
                    }
                    continue
                
                # Run validation
                validation_result = self.validate_table(table)
                
                # Check for anomalies
                anomaly_result = self.detect_anomalies(table)
                
                # Combine results
                table_report = {
                    "status": "checked",
                    "records_checked": validation_result.get("records_checked", 0),
                    "validation_issues": validation_result.get("issues_found", 0),
                    "anomalies_found": anomaly_result.get("anomalies_found", 0),
                    "missing_fields": validation_result.get("missing_fields", [])
                }
                
                # Calculate table quality score (simple version)
                records = table_report["records_checked"]
                if records > 0:
                    issues = table_report["validation_issues"] + table_report["anomalies_found"]
                    table_report["quality_score"] = max(0, 100 - (issues / records * 100))
                else:
                    table_report["quality_score"] = None
                
                # Track totals
                total_records += table_report["records_checked"]
                total_issues += table_report["validation_issues"] + table_report["anomalies_found"]
                
                # Add to report
                report["table_reports"][table] = table_report
            
            # Calculate overall quality score
            if total_records > 0:
                report["overall_quality_score"] = max(0, 100 - (total_issues / total_records * 100))
            
            # Identify critical issues
            for table, table_report in report["table_reports"].items():
                if table_report.get("status") != "checked":
                    continue
                    
                # Missing required fields is critical
                if table_report.get("missing_fields"):
                    report["critical_issues"].append({
                        "table": table,
                        "type": "missing_required_fields",
                        "fields": table_report["missing_fields"],
                        "message": f"Table {table} is missing required fields: {', '.join(table_report['missing_fields'])}"
                    })
                
                # Low quality score is critical
                if table_report.get("quality_score") is not None and table_report["quality_score"] < 50:
                    report["critical_issues"].append({
                        "table": table,
                        "type": "low_quality_score",
                        "score": table_report["quality_score"],
                        "message": f"Table {table} has a low quality score: {table_report['quality_score']:.1f}%"
                    })
            
            # Send notification if critical issues found
            if report["critical_issues"]:
                self.notification_manager.send_notification(
                    level="error",
                    title="Critical Data Quality Issues",
                    message=f"Found {len(report['critical_issues'])} critical data quality issues",
                    metadata={
                        "tables": tables,
                        "critical_issue_count": len(report["critical_issues"])
                    }
                )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating data quality report: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }