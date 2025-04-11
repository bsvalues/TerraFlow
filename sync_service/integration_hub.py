"""
Benton County Assessment Data Integration Hub

This module provides centralized integration with various assessment data sources
specific to Benton County Assessor's Office needs. It standardizes connection to:
- CAMA (Computer Assisted Mass Appraisal) systems
- GIS (Geographic Information Systems)  
- Historical sales databases
- Washington Department of Revenue reporting systems

The Integration Hub ensures consistent data access, transformation, and synchronization
across all data sources, providing a unified interface for the MCP agents to work with.
"""

import os
import logging
import datetime
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
import sqlalchemy
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import geopandas as gpd
import pyodbc

from app import db
from sync_service.multi_format_exporter import MultiFormatExporter
from sync_service.data_sanitization import DataSanitizer
from sync_service.notification_system import SyncNotificationManager

# Configure logging
logger = logging.getLogger(__name__)

class DataSourceConfig:
    """Configuration for a data source in the integration hub"""
    
    def __init__(
        self,
        source_id: str,
        source_type: str,
        connection_string: str,
        refresh_interval: int = 60,  # minutes
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize data source configuration
        
        Args:
            source_id: Unique identifier for the data source
            source_type: Type of data source (cama, gis, sales, dor)
            connection_string: Connection string for the data source
            refresh_interval: How often to refresh data from this source (minutes)
            enabled: Whether this data source is enabled
            metadata: Additional metadata for the data source
        """
        self.source_id = source_id
        self.source_type = source_type
        self.connection_string = connection_string
        self.refresh_interval = refresh_interval
        self.enabled = enabled
        self.metadata = metadata or {}
        self.last_sync = None
        self.status = "configured"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "connection_string": self.connection_string.replace(
                os.environ.get("DB_PASSWORD", ""), "******"
            ) if "password" in self.connection_string.lower() else self.connection_string,
            "refresh_interval": self.refresh_interval,
            "enabled": self.enabled,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "status": self.status,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataSourceConfig':
        """Create from dictionary representation"""
        config = cls(
            source_id=data["source_id"],
            source_type=data["source_type"],
            connection_string=data["connection_string"],
            refresh_interval=data.get("refresh_interval", 60),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {})
        )
        
        if data.get("last_sync"):
            config.last_sync = datetime.datetime.fromisoformat(data["last_sync"])
        
        config.status = data.get("status", "configured")
        
        return config


class DataSourceConnection:
    """Connection to a data source in the integration hub"""
    
    def __init__(self, config: DataSourceConfig):
        """
        Initialize data source connection
        
        Args:
            config: Configuration for the data source
        """
        self.config = config
        self.connection = None
        self.engine = None
        self.connected = False
        self.error = None
        
    def connect(self) -> bool:
        """
        Connect to the data source
        
        Returns:
            True if connection succeeded, False otherwise
        """
        try:
            if self.config.source_type in ["sql_server", "cama"]:
                # SQL Server connection (used by many CAMA systems)
                self.connection = pyodbc.connect(self.config.connection_string)
                self.connected = True
                
            elif self.config.source_type in ["postgresql", "gis"]:
                # PostgreSQL connection (used by many GIS systems)
                self.engine = create_engine(self.config.connection_string)
                self.connection = self.engine.connect()
                self.connected = True
                
            elif self.config.source_type == "sqlite":
                # SQLite connection (used for local data)
                self.engine = create_engine(self.config.connection_string)
                self.connection = self.engine.connect()
                self.connected = True
                
            elif self.config.source_type == "file":
                # File-based connection (CSV, Excel, etc.)
                # Just verify the file exists
                file_path = self.config.connection_string.replace("file://", "")
                if os.path.exists(file_path):
                    self.connected = True
                else:
                    raise FileNotFoundError(f"File not found: {file_path}")
                    
            else:
                raise ValueError(f"Unsupported data source type: {self.config.source_type}")
                
            self.config.status = "connected"
            logger.info(f"Connected to data source: {self.config.source_id}")
            return True
            
        except Exception as e:
            self.error = str(e)
            self.config.status = "error"
            logger.error(f"Error connecting to data source {self.config.source_id}: {str(e)}")
            return False
            
    def disconnect(self) -> None:
        """Disconnect from the data source"""
        try:
            if self.connection:
                self.connection.close()
            
            self.connected = False
            self.config.status = "disconnected"
            logger.info(f"Disconnected from data source: {self.config.source_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting from data source {self.config.source_id}: {str(e)}")
            
    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute a query against the data source
        
        Args:
            query: SQL query to execute
            
        Returns:
            Pandas DataFrame with query results
        """
        if not self.connected:
            if not self.connect():
                raise ConnectionError(f"Not connected to data source: {self.config.source_id}")
        
        try:
            if self.config.source_type in ["sql_server", "cama"]:
                # Execute query with pyodbc
                return pd.read_sql(query, self.connection)
                
            elif self.config.source_type in ["postgresql", "gis", "sqlite"]:
                # Execute query with SQLAlchemy
                return pd.read_sql(query, self.connection)
                
            elif self.config.source_type == "file":
                # Read file based on extension
                file_path = self.config.connection_string.replace("file://", "")
                
                if file_path.endswith(".csv"):
                    return pd.read_csv(file_path)
                elif file_path.endswith((".xls", ".xlsx")):
                    return pd.read_excel(file_path)
                elif file_path.endswith(".json"):
                    return pd.read_json(file_path)
                elif file_path.endswith((".geojson", ".shp")):
                    return gpd.read_file(file_path)
                else:
                    raise ValueError(f"Unsupported file type: {file_path}")
                    
            else:
                raise ValueError(f"Unsupported data source type: {self.config.source_type}")
                
        except Exception as e:
            logger.error(f"Error executing query on data source {self.config.source_id}: {str(e)}")
            raise


class AssessmentDataIntegrationHub:
    """
    Centralized hub for integrating assessment data from various sources
    
    This class provides a unified interface for accessing and synchronizing data
    from different systems used by the Benton County Assessor's Office, enabling
    seamless data flow between systems while maintaining data quality and consistency.
    """
    
    def __init__(self):
        """Initialize the assessment data integration hub"""
        self.data_sources = {}
        self.connections = {}
        self.notification_manager = SyncNotificationManager()
        self.data_sanitizer = DataSanitizer()
        self.exporter = MultiFormatExporter()
        
        # Standard schemas for different data types
        self.schemas = {
            "property": {
                "parcel_id": "string",
                "property_type": "string",
                "address": "string",
                "owner_name": "string",
                "assessed_value": "float",
                "land_value": "float",
                "improvement_value": "float",
                "year_built": "int",
                "total_area_sqft": "float",
                "bedrooms": "int",
                "bathrooms": "float",
                "last_sale_date": "datetime",
                "last_sale_price": "float",
                "latitude": "float",
                "longitude": "float"
            },
            "sales": {
                "sale_id": "string",
                "parcel_id": "string",
                "sale_date": "datetime",
                "sale_price": "float",
                "buyer_name": "string",
                "seller_name": "string",
                "deed_type": "string",
                "verified": "boolean",
                "qualified": "boolean",
                "verification_notes": "string"
            },
            "valuation": {
                "valuation_id": "string",
                "parcel_id": "string",
                "valuation_date": "datetime",
                "land_value": "float",
                "improvement_value": "float",
                "total_value": "float",
                "assessment_year": "int",
                "assessment_method": "string",
                "assessor_name": "string",
                "notes": "string"
            }
        }
        
        # Initialize with default data sources if available
        self._load_data_sources()
        
        logger.info("Assessment Data Integration Hub initialized")
        
    def _load_data_sources(self) -> None:
        """Load data source configurations from the database"""
        try:
            # Query data source configurations from database
            data_sources = db.session.execute(
                text("SELECT * FROM integration_data_sources WHERE deleted_at IS NULL")
            ).fetchall()
            
            if not data_sources:
                logger.info("No data sources found in database")
                return
                
            # Create DataSourceConfig objects from database records
            for source in data_sources:
                config = DataSourceConfig(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    connection_string=source.connection_string,
                    refresh_interval=source.refresh_interval,
                    enabled=source.enabled,
                    metadata=json.loads(source.metadata) if source.metadata else {}
                )
                
                if source.last_sync:
                    config.last_sync = source.last_sync
                    
                config.status = source.status
                
                self.data_sources[source.source_id] = config
                
                logger.info(f"Loaded data source configuration: {source.source_id}")
                
        except Exception as e:
            # If table doesn't exist yet, this is ok
            if "integration_data_sources" in str(e):
                logger.info("Integration data sources table not found - will be created on first use")
            else:
                logger.error(f"Error loading data sources: {str(e)}")
    
    def add_data_source(self, config: DataSourceConfig) -> bool:
        """
        Add a new data source to the integration hub
        
        Args:
            config: Configuration for the data source
            
        Returns:
            True if data source was added successfully, False otherwise
        """
        try:
            # Add to in-memory registry
            self.data_sources[config.source_id] = config
            
            # Save to database
            self._save_data_source(config)
            
            logger.info(f"Added data source: {config.source_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding data source: {str(e)}")
            return False
    
    def update_data_source(self, config: DataSourceConfig) -> bool:
        """
        Update an existing data source configuration
        
        Args:
            config: Updated configuration for the data source
            
        Returns:
            True if data source was updated successfully, False otherwise
        """
        if config.source_id not in self.data_sources:
            logger.error(f"Data source not found: {config.source_id}")
            return False
            
        try:
            # Update in-memory registry
            self.data_sources[config.source_id] = config
            
            # Update in database
            self._save_data_source(config, update=True)
            
            # Close and remove any existing connection
            if config.source_id in self.connections:
                self.connections[config.source_id].disconnect()
                del self.connections[config.source_id]
                
            logger.info(f"Updated data source: {config.source_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating data source: {str(e)}")
            return False
    
    def remove_data_source(self, source_id: str) -> bool:
        """
        Remove a data source from the integration hub
        
        Args:
            source_id: ID of the data source to remove
            
        Returns:
            True if data source was removed successfully, False otherwise
        """
        if source_id not in self.data_sources:
            logger.error(f"Data source not found: {source_id}")
            return False
            
        try:
            # Close connection if exists
            if source_id in self.connections:
                self.connections[source_id].disconnect()
                del self.connections[source_id]
                
            # Remove from in-memory registry
            del self.data_sources[source_id]
            
            # Soft delete in database
            db.session.execute(
                text("UPDATE integration_data_sources SET deleted_at = :now WHERE source_id = :source_id"),
                {"now": datetime.datetime.utcnow(), "source_id": source_id}
            )
            db.session.commit()
            
            logger.info(f"Removed data source: {source_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing data source: {str(e)}")
            return False
    
    def _save_data_source(self, config: DataSourceConfig, update: bool = False) -> None:
        """
        Save a data source configuration to the database
        
        Args:
            config: Configuration to save
            update: Whether this is an update to an existing configuration
        """
        # Ensure the table exists
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS integration_data_sources (
                source_id VARCHAR(64) PRIMARY KEY,
                source_type VARCHAR(32) NOT NULL,
                connection_string TEXT NOT NULL,
                refresh_interval INTEGER NOT NULL DEFAULT 60,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                status VARCHAR(32) NOT NULL DEFAULT 'configured',
                metadata JSON,
                last_sync TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            )
        """))
        db.session.commit()
        
        if update:
            # Update existing record
            db.session.execute(
                text("""
                    UPDATE integration_data_sources
                    SET source_type = :source_type,
                        connection_string = :connection_string,
                        refresh_interval = :refresh_interval,
                        enabled = :enabled,
                        status = :status,
                        metadata = :metadata,
                        last_sync = :last_sync,
                        updated_at = :updated_at
                    WHERE source_id = :source_id
                """),
                {
                    "source_id": config.source_id,
                    "source_type": config.source_type,
                    "connection_string": config.connection_string,
                    "refresh_interval": config.refresh_interval,
                    "enabled": config.enabled,
                    "status": config.status,
                    "metadata": json.dumps(config.metadata),
                    "last_sync": config.last_sync,
                    "updated_at": datetime.datetime.utcnow()
                }
            )
        else:
            # Insert new record
            db.session.execute(
                text("""
                    INSERT INTO integration_data_sources (
                        source_id, source_type, connection_string, refresh_interval,
                        enabled, status, metadata, last_sync, created_at, updated_at
                    ) VALUES (
                        :source_id, :source_type, :connection_string, :refresh_interval,
                        :enabled, :status, :metadata, :last_sync, :created_at, :updated_at
                    )
                """),
                {
                    "source_id": config.source_id,
                    "source_type": config.source_type,
                    "connection_string": config.connection_string,
                    "refresh_interval": config.refresh_interval,
                    "enabled": config.enabled,
                    "status": config.status,
                    "metadata": json.dumps(config.metadata),
                    "last_sync": config.last_sync,
                    "created_at": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow()
                }
            )
            
        db.session.commit()
    
    def get_connection(self, source_id: str) -> Optional[DataSourceConnection]:
        """
        Get a connection to a data source
        
        Args:
            source_id: ID of the data source
            
        Returns:
            Connection to the data source, or None if not found or connection failed
        """
        if source_id not in self.data_sources:
            logger.error(f"Data source not found: {source_id}")
            return None
            
        # Return existing connection if available
        if source_id in self.connections and self.connections[source_id].connected:
            return self.connections[source_id]
            
        # Create new connection
        config = self.data_sources[source_id]
        connection = DataSourceConnection(config)
        
        if connection.connect():
            self.connections[source_id] = connection
            return connection
        else:
            logger.error(f"Failed to connect to data source: {source_id}")
            return None
    
    def query_data_source(
        self, 
        source_id: str, 
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[pd.DataFrame]:
        """
        Query a data source
        
        Args:
            source_id: ID of the data source
            query: SQL query to execute
            parameters: Query parameters
            
        Returns:
            Pandas DataFrame with query results, or None if query failed
        """
        connection = self.get_connection(source_id)
        if not connection:
            return None
            
        try:
            # If parameters provided, substitute them in the query
            if parameters:
                for key, value in parameters.items():
                    query = query.replace(f":{key}", f"'{value}'")
                    
            # Execute the query
            result = connection.execute_query(query)
            
            # Update last sync time
            self.data_sources[source_id].last_sync = datetime.datetime.utcnow()
            self._save_data_source(self.data_sources[source_id], update=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Error querying data source {source_id}: {str(e)}")
            return None
    
    def sync_property_data(self, source_id: str, target_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronize property data from a source to a target
        
        Args:
            source_id: ID of the source data source
            target_id: ID of the target data source, or None to sync to internal database
            
        Returns:
            Synchronization results
        """
        connection = self.get_connection(source_id)
        if not connection:
            return {"status": "error", "message": f"Failed to connect to source: {source_id}"}
            
        try:
            # Get property query based on source type
            if connection.config.source_type == "cama":
                query = self._get_cama_property_query()
            elif connection.config.source_type == "gis":
                query = self._get_gis_property_query()
            else:
                query = self._get_generic_property_query(connection.config.source_type)
                
            # Execute the query
            data = connection.execute_query(query)
            
            # Sanitize the data
            sanitized_data = self.data_sanitizer.sanitize_dataframe(data)
            
            # Transform to standard schema
            transformed_data = self._transform_to_schema(sanitized_data, "property")
            
            # Determine target
            if target_id:
                # Sync to another data source
                target_connection = self.get_connection(target_id)
                if not target_connection:
                    return {"status": "error", "message": f"Failed to connect to target: {target_id}"}
                    
                # Insert or update in target
                result = self._sync_to_external_target(transformed_data, target_connection, "property")
                
            else:
                # Sync to internal database
                result = self._sync_to_internal_db(transformed_data, "property")
                
            # Update last sync time
            self.data_sources[source_id].last_sync = datetime.datetime.utcnow()
            self._save_data_source(self.data_sources[source_id], update=True)
            
            return {
                "status": "success",
                "source": source_id,
                "target": target_id or "internal",
                "records": len(transformed_data),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Error syncing property data from {source_id}: {str(e)}")
            return {
                "status": "error",
                "source": source_id,
                "target": target_id or "internal",
                "message": str(e),
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
    
    def sync_sales_data(self, source_id: str, target_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronize sales data from a source to a target
        
        Args:
            source_id: ID of the source data source
            target_id: ID of the target data source, or None to sync to internal database
            
        Returns:
            Synchronization results
        """
        connection = self.get_connection(source_id)
        if not connection:
            return {"status": "error", "message": f"Failed to connect to source: {source_id}"}
            
        try:
            # Get sales query based on source type
            if connection.config.source_type == "cama":
                query = self._get_cama_sales_query()
            else:
                query = self._get_generic_sales_query(connection.config.source_type)
                
            # Execute the query
            data = connection.execute_query(query)
            
            # Sanitize the data
            sanitized_data = self.data_sanitizer.sanitize_dataframe(data)
            
            # Transform to standard schema
            transformed_data = self._transform_to_schema(sanitized_data, "sales")
            
            # Determine target
            if target_id:
                # Sync to another data source
                target_connection = self.get_connection(target_id)
                if not target_connection:
                    return {"status": "error", "message": f"Failed to connect to target: {target_id}"}
                    
                # Insert or update in target
                result = self._sync_to_external_target(transformed_data, target_connection, "sales")
                
            else:
                # Sync to internal database
                result = self._sync_to_internal_db(transformed_data, "sales")
                
            # Update last sync time
            self.data_sources[source_id].last_sync = datetime.datetime.utcnow()
            self._save_data_source(self.data_sources[source_id], update=True)
            
            return {
                "status": "success",
                "source": source_id,
                "target": target_id or "internal",
                "records": len(transformed_data),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Error syncing sales data from {source_id}: {str(e)}")
            return {
                "status": "error",
                "source": source_id,
                "target": target_id or "internal",
                "message": str(e),
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
    
    def sync_valuation_data(self, source_id: str, target_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronize valuation data from a source to a target
        
        Args:
            source_id: ID of the source data source
            target_id: ID of the target data source, or None to sync to internal database
            
        Returns:
            Synchronization results
        """
        connection = self.get_connection(source_id)
        if not connection:
            return {"status": "error", "message": f"Failed to connect to source: {source_id}"}
            
        try:
            # Get valuation query based on source type
            if connection.config.source_type == "cama":
                query = self._get_cama_valuation_query()
            else:
                query = self._get_generic_valuation_query(connection.config.source_type)
                
            # Execute the query
            data = connection.execute_query(query)
            
            # Sanitize the data
            sanitized_data = self.data_sanitizer.sanitize_dataframe(data)
            
            # Transform to standard schema
            transformed_data = self._transform_to_schema(sanitized_data, "valuation")
            
            # Determine target
            if target_id:
                # Sync to another data source
                target_connection = self.get_connection(target_id)
                if not target_connection:
                    return {"status": "error", "message": f"Failed to connect to target: {target_id}"}
                    
                # Insert or update in target
                result = self._sync_to_external_target(transformed_data, target_connection, "valuation")
                
            else:
                # Sync to internal database
                result = self._sync_to_internal_db(transformed_data, "valuation")
                
            # Update last sync time
            self.data_sources[source_id].last_sync = datetime.datetime.utcnow()
            self._save_data_source(self.data_sources[source_id], update=True)
            
            return {
                "status": "success",
                "source": source_id,
                "target": target_id or "internal",
                "records": len(transformed_data),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Error syncing valuation data from {source_id}: {str(e)}")
            return {
                "status": "error",
                "source": source_id,
                "target": target_id or "internal",
                "message": str(e),
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
    
    def export_data(
        self, 
        data_type: str, 
        export_format: str,
        filters: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export data to a file
        
        Args:
            data_type: Type of data to export (property, sales, valuation)
            export_format: Format to export (csv, excel, json, sqlite, etc.)
            filters: Filters to apply to the data
            output_path: Path to save the exported file, or None for default location
            
        Returns:
            Export results with file path
        """
        try:
            # Query data from internal database
            query = self._build_export_query(data_type, filters)
            
            # Execute query
            data = pd.read_sql(query, db.engine)
            
            if len(data) == 0:
                return {
                    "status": "warning",
                    "message": "No data found matching the filters",
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }
            
            # Generate default output path if not provided
            if not output_path:
                export_dir = os.path.join("exports", data_type)
                os.makedirs(export_dir, exist_ok=True)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{data_type}_{timestamp}.{export_format}"
                output_path = os.path.join(export_dir, filename)
            
            # Export data using MultiFormatExporter
            export_result = self.exporter.export_dataframe(
                data, 
                export_format, 
                output_path,
                {
                    "source": "integration_hub",
                    "export_time": datetime.datetime.utcnow().isoformat(),
                    "record_count": len(data),
                    "data_type": data_type
                }
            )
            
            return {
                "status": "success",
                "data_type": data_type,
                "format": export_format,
                "records": len(data),
                "file_path": output_path,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "details": export_result
            }
            
        except Exception as e:
            logger.error(f"Error exporting {data_type} data: {str(e)}")
            return {
                "status": "error",
                "data_type": data_type,
                "format": export_format,
                "message": str(e),
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
    
    def get_source_metadata(self, source_id: str) -> Dict[str, Any]:
        """
        Get metadata about a data source
        
        Args:
            source_id: ID of the data source
            
        Returns:
            Metadata about the data source
        """
        if source_id not in self.data_sources:
            return {"status": "error", "message": f"Data source not found: {source_id}"}
            
        config = self.data_sources[source_id]
        
        # Get connection to check schema
        connection = self.get_connection(source_id)
        
        schema_info = None
        if connection and connection.connected:
            try:
                if config.source_type in ["postgresql", "gis", "sqlite"]:
                    # Get schema info for database sources
                    inspector = inspect(connection.engine)
                    tables = inspector.get_table_names()
                    
                    schema_info = {
                        "tables": tables,
                        "columns": {
                            table: [
                                {
                                    "name": col["name"],
                                    "type": str(col["type"]),
                                    "nullable": col["nullable"]
                                }
                                for col in inspector.get_columns(table)
                            ]
                            for table in tables[:10]  # Limit to first 10 tables
                        }
                    }
                    
                elif config.source_type in ["sql_server", "cama"]:
                    # Get top tables for SQL Server
                    tables_query = """
                        SELECT TOP 10 
                            t.name AS table_name
                        FROM 
                            sys.tables t
                        ORDER BY 
                            t.name
                    """
                    
                    tables_df = pd.read_sql(tables_query, connection.connection)
                    tables = tables_df["table_name"].tolist()
                    
                    schema_info = {
                        "tables": tables,
                        "columns": {}
                    }
                    
                    # Get columns for each table
                    for table in tables:
                        columns_query = f"""
                            SELECT 
                                c.name AS column_name,
                                t.name AS data_type,
                                c.is_nullable
                            FROM 
                                sys.columns c
                            JOIN 
                                sys.types t ON c.user_type_id = t.user_type_id
                            WHERE 
                                c.object_id = OBJECT_ID('{table}')
                            ORDER BY 
                                c.column_id
                        """
                        
                        columns_df = pd.read_sql(columns_query, connection.connection)
                        
                        schema_info["columns"][table] = [
                            {
                                "name": row["column_name"],
                                "type": row["data_type"],
                                "nullable": bool(row["is_nullable"])
                            }
                            for _, row in columns_df.iterrows()
                        ]
                    
            except Exception as e:
                logger.error(f"Error getting schema for data source {source_id}: {str(e)}")
                schema_info = {"error": str(e)}
        
        return {
            "status": "success",
            "source_id": source_id,
            "config": config.to_dict(),
            "connected": connection.connected if connection else False,
            "schema_info": schema_info,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    
    def _get_cama_property_query(self) -> str:
        """Get query for property data from CAMA systems"""
        # This is a generic query - in a real implementation,
        # this would be customized for the specific CAMA system
        return """
            SELECT 
                Parcel.ParcelID as parcel_id,
                PropertyType.Description as property_type,
                Parcel.SitusAddress as address,
                Owner.Name as owner_name,
                Assessment.TotalValue as assessed_value,
                Assessment.LandValue as land_value,
                Assessment.ImprovementValue as improvement_value,
                Improvement.YearBuilt as year_built,
                Improvement.SquareFeet as total_area_sqft,
                Residential.Bedrooms as bedrooms,
                Residential.Bathrooms as bathrooms,
                Sale.SaleDate as last_sale_date,
                Sale.SalePrice as last_sale_price,
                Parcel.Latitude as latitude,
                Parcel.Longitude as longitude
            FROM 
                Parcel
            LEFT JOIN 
                PropertyType ON Parcel.PropertyTypeID = PropertyType.PropertyTypeID
            LEFT JOIN 
                Owner ON Parcel.ParcelID = Owner.ParcelID
            LEFT JOIN 
                Assessment ON Parcel.ParcelID = Assessment.ParcelID AND Assessment.IsActive = 1
            LEFT JOIN 
                Improvement ON Parcel.ParcelID = Improvement.ParcelID
            LEFT JOIN 
                Residential ON Improvement.ImprovementID = Residential.ImprovementID
            LEFT JOIN 
                Sale ON Parcel.ParcelID = Sale.ParcelID AND Sale.IsLatest = 1
            WHERE
                Parcel.IsActive = 1
        """
    
    def _get_gis_property_query(self) -> str:
        """Get query for property data from GIS systems"""
        # This is a generic query - in a real implementation,
        # this would be customized for the specific GIS system
        return """
            SELECT 
                p.parcel_id,
                p.property_type,
                p.situs_address as address,
                p.owner_name,
                p.assessed_value,
                p.land_value,
                p.improvement_value,
                p.year_built,
                p.total_sqft as total_area_sqft,
                p.bedrooms,
                p.bathrooms,
                p.last_sale_date,
                p.last_sale_price,
                ST_X(p.geom) as longitude,
                ST_Y(p.geom) as latitude
            FROM 
                parcels p
            WHERE
                p.active = true
        """
    
    def _get_generic_property_query(self, source_type: str) -> str:
        """Get query for property data from a generic source"""
        if source_type == "file":
            # For file sources, return an empty query since we'll read the whole file
            return ""
            
        # Generic query with column aliases to match our schema
        return """
            SELECT 
                parcel_id,
                property_type,
                address,
                owner_name,
                assessed_value,
                land_value,
                improvement_value,
                year_built,
                total_area_sqft,
                bedrooms,
                bathrooms,
                last_sale_date,
                last_sale_price,
                latitude,
                longitude
            FROM 
                properties
            WHERE
                active = true
        """
    
    def _get_cama_sales_query(self) -> str:
        """Get query for sales data from CAMA systems"""
        # This is a generic query - in a real implementation,
        # this would be customized for the specific CAMA system
        return """
            SELECT 
                Sale.SaleID as sale_id,
                Sale.ParcelID as parcel_id,
                Sale.SaleDate as sale_date,
                Sale.SalePrice as sale_price,
                Sale.BuyerName as buyer_name,
                Sale.SellerName as seller_name,
                DeedType.Description as deed_type,
                Sale.Verified as verified,
                Sale.Qualified as qualified,
                Sale.VerificationNotes as verification_notes
            FROM 
                Sale
            LEFT JOIN 
                DeedType ON Sale.DeedTypeID = DeedType.DeedTypeID
            WHERE
                Sale.SaleDate >= DATEADD(year, -3, GETDATE())
        """
    
    def _get_generic_sales_query(self, source_type: str) -> str:
        """Get query for sales data from a generic source"""
        if source_type == "file":
            # For file sources, return an empty query since we'll read the whole file
            return ""
            
        # Generic query with column aliases to match our schema
        return """
            SELECT 
                sale_id,
                parcel_id,
                sale_date,
                sale_price,
                buyer_name,
                seller_name,
                deed_type,
                verified,
                qualified,
                verification_notes
            FROM 
                sales
            WHERE
                sale_date >= date('now', '-3 years')
        """
    
    def _get_cama_valuation_query(self) -> str:
        """Get query for valuation data from CAMA systems"""
        # This is a generic query - in a real implementation,
        # this would be customized for the specific CAMA system
        return """
            SELECT 
                Assessment.AssessmentID as valuation_id,
                Assessment.ParcelID as parcel_id,
                Assessment.AssessmentDate as valuation_date,
                Assessment.LandValue as land_value,
                Assessment.ImprovementValue as improvement_value,
                Assessment.TotalValue as total_value,
                Assessment.AssessmentYear as assessment_year,
                AssessmentMethod.Description as assessment_method,
                Assessor.Name as assessor_name,
                Assessment.Notes as notes
            FROM 
                Assessment
            LEFT JOIN 
                AssessmentMethod ON Assessment.MethodID = AssessmentMethod.MethodID
            LEFT JOIN 
                Assessor ON Assessment.AssessorID = Assessor.AssessorID
            WHERE
                Assessment.AssessmentYear >= YEAR(GETDATE()) - 2
        """
    
    def _get_generic_valuation_query(self, source_type: str) -> str:
        """Get query for valuation data from a generic source"""
        if source_type == "file":
            # For file sources, return an empty query since we'll read the whole file
            return ""
            
        # Generic query with column aliases to match our schema
        return """
            SELECT 
                valuation_id,
                parcel_id,
                valuation_date,
                land_value,
                improvement_value,
                total_value,
                assessment_year,
                assessment_method,
                assessor_name,
                notes
            FROM 
                valuations
            WHERE
                assessment_year >= strftime('%Y', 'now') - 2
        """
    
    def _transform_to_schema(self, data: pd.DataFrame, schema_type: str) -> pd.DataFrame:
        """
        Transform data to match the standard schema
        
        Args:
            data: DataFrame to transform
            schema_type: Type of schema to transform to
            
        Returns:
            Transformed DataFrame
        """
        if schema_type not in self.schemas:
            raise ValueError(f"Unknown schema type: {schema_type}")
            
        schema = self.schemas[schema_type]
        
        # Create new DataFrame with schema columns
        result = pd.DataFrame(columns=schema.keys())
        
        # Copy data from source DataFrame, matching column names case-insensitively
        for col_name, col_type in schema.items():
            # Find matching column in source data
            source_col = next(
                (c for c in data.columns if c.lower() == col_name.lower()),
                None
            )
            
            if source_col is not None:
                # Copy and convert data
                result[col_name] = data[source_col]
                
                # Convert to appropriate type
                if col_type == "string":
                    result[col_name] = result[col_name].astype(str)
                elif col_type == "float":
                    result[col_name] = pd.to_numeric(result[col_name], errors="coerce")
                elif col_type == "int":
                    result[col_name] = pd.to_numeric(result[col_name], errors="coerce").astype(pd.Int64Dtype())
                elif col_type == "datetime":
                    result[col_name] = pd.to_datetime(result[col_name], errors="coerce")
                elif col_type == "boolean":
                    result[col_name] = result[col_name].astype(bool)
        
        return result
    
    def _sync_to_internal_db(self, data: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """
        Synchronize data to the internal database
        
        Args:
            data: DataFrame to synchronize
            data_type: Type of data (property, sales, valuation)
            
        Returns:
            Synchronization results
        """
        # Ensure the table exists
        table_name = f"integration_{data_type}"
        self._ensure_table_exists(table_name, data_type)
        
        # Get primary key column based on data type
        if data_type == "property":
            primary_key = "parcel_id"
        elif data_type == "sales":
            primary_key = "sale_id"
        elif data_type == "valuation":
            primary_key = "valuation_id"
        else:
            raise ValueError(f"Unknown data type: {data_type}")
        
        # Get existing records
        existing_records = pd.read_sql(
            f"SELECT {primary_key} FROM {table_name}",
            db.engine
        )
        
        # Split data into new and existing records
        existing_keys = set(existing_records[primary_key].tolist())
        
        new_records = data[~data[primary_key].isin(existing_keys)]
        update_records = data[data[primary_key].isin(existing_keys)]
        
        # Insert new records
        if len(new_records) > 0:
            new_records.to_sql(
                table_name,
                db.engine,
                if_exists="append",
                index=False
            )
        
        # Update existing records
        updated_count = 0
        if len(update_records) > 0:
            for _, row in update_records.iterrows():
                # Build SET clause
                set_clause = ", ".join([
                    f"{col} = :{col}"
                    for col in row.index
                    if col != primary_key
                ])
                
                # Build parameter dict
                params = {col: row[col] for col in row.index}
                
                # Execute update
                db.session.execute(
                    text(f"UPDATE {table_name} SET {set_clause} WHERE {primary_key} = :{primary_key}"),
                    params
                )
                
                updated_count += 1
                
            db.session.commit()
        
        return {
            "new_records": len(new_records),
            "updated_records": updated_count,
            "total_records": len(data)
        }
    
    def _sync_to_external_target(
        self, 
        data: pd.DataFrame, 
        target: DataSourceConnection,
        data_type: str
    ) -> Dict[str, Any]:
        """
        Synchronize data to an external target
        
        Args:
            data: DataFrame to synchronize
            target: Connection to the target data source
            data_type: Type of data (property, sales, valuation)
            
        Returns:
            Synchronization results
        """
        # Determine target table based on data type
        if data_type == "property":
            table_name = "properties"
            primary_key = "parcel_id"
        elif data_type == "sales":
            table_name = "sales"
            primary_key = "sale_id"
        elif data_type == "valuation":
            table_name = "valuations"
            primary_key = "valuation_id"
        else:
            raise ValueError(f"Unknown data type: {data_type}")
        
        # Different handling based on target type
        if target.config.source_type in ["postgresql", "gis", "sqlite"]:
            # For SQL databases, we can use to_sql
            data.to_sql(
                table_name,
                target.engine,
                if_exists="replace",  # For external targets, we replace the entire table
                index=False
            )
            
            return {
                "total_records": len(data),
                "target_table": table_name
            }
            
        elif target.config.source_type in ["sql_server", "cama"]:
            # For SQL Server, we need to use a different approach
            # Create a temporary table
            temp_table = f"temp_{table_name}"
            
            # Drop temp table if exists
            target.connection.execute(f"IF OBJECT_ID('tempdb..#{temp_table}') IS NOT NULL DROP TABLE #{temp_table}")
            
            # Create temp table with data
            columns = ", ".join([
                f"[{col}] NVARCHAR(MAX)" if dtype == "object" else
                f"[{col}] FLOAT" if dtype == "float64" else
                f"[{col}] INT" if dtype == "int64" else
                f"[{col}] DATETIME" if dtype == "datetime64[ns]" else
                f"[{col}] BIT" if dtype == "bool" else
                f"[{col}] NVARCHAR(MAX)"
                for col, dtype in zip(data.columns, data.dtypes.astype(str))
            ])
            
            target.connection.execute(f"CREATE TABLE #{temp_table} ({columns})")
            
            # Insert data into temp table
            for _, row in data.iterrows():
                # Build VALUES clause
                values = ", ".join([
                    "NULL" if pd.isna(row[col]) else
                    f"'{row[col]}'" if isinstance(row[col], str) else
                    "1" if row[col] is True else
                    "0" if row[col] is False else
                    str(row[col])
                    for col in data.columns
                ])
                
                # Execute insert
                target.connection.execute(f"INSERT INTO #{temp_table} VALUES ({values})")
            
            # Merge into target table
            target.connection.execute(f"""
                MERGE INTO {table_name} AS target
                USING #{temp_table} AS source
                ON target.{primary_key} = source.{primary_key}
                WHEN MATCHED THEN
                    UPDATE SET {", ".join([f"target.{col} = source.{col}" for col in data.columns if col != primary_key])}
                WHEN NOT MATCHED THEN
                    INSERT ({", ".join([f"[{col}]" for col in data.columns])})
                    VALUES ({", ".join([f"source.[{col}]" for col in data.columns])});
            """)
            
            # Drop temp table
            target.connection.execute(f"DROP TABLE #{temp_table}")
            
            return {
                "total_records": len(data),
                "target_table": table_name
            }
            
        elif target.config.source_type == "file":
            # For file targets, export to file
            file_path = target.config.connection_string.replace("file://", "")
            
            if file_path.endswith(".csv"):
                data.to_csv(file_path, index=False)
            elif file_path.endswith((".xls", ".xlsx")):
                data.to_excel(file_path, index=False)
            elif file_path.endswith(".json"):
                data.to_json(file_path, orient="records")
            elif file_path.endswith((".geojson", ".shp")):
                # Convert to GeoDataFrame if it has lat/long columns
                if "latitude" in data.columns and "longitude" in data.columns:
                    from shapely.geometry import Point
                    import geopandas as gpd
                    
                    # Create geometry from lat/long
                    geometry = [
                        Point(row["longitude"], row["latitude"])
                        if not pd.isna(row["longitude"]) and not pd.isna(row["latitude"])
                        else None
                        for _, row in data.iterrows()
                    ]
                    
                    # Create GeoDataFrame
                    gdf = gpd.GeoDataFrame(data, geometry=geometry)
                    
                    # Save to file
                    gdf.to_file(file_path)
                else:
                    raise ValueError("GeoJSON/Shapefile export requires latitude and longitude columns")
            else:
                raise ValueError(f"Unsupported file type: {file_path}")
            
            return {
                "total_records": len(data),
                "file_path": file_path
            }
            
        else:
            raise ValueError(f"Unsupported target type: {target.config.source_type}")
    
    def _ensure_table_exists(self, table_name: str, data_type: str) -> None:
        """
        Ensure a table exists in the database
        
        Args:
            table_name: Name of the table
            data_type: Type of data (property, sales, valuation)
        """
        if data_type == "property":
            db.session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    parcel_id VARCHAR(64) UNIQUE NOT NULL,
                    property_type VARCHAR(64),
                    address TEXT,
                    owner_name VARCHAR(128),
                    assessed_value FLOAT,
                    land_value FLOAT,
                    improvement_value FLOAT,
                    year_built INTEGER,
                    total_area_sqft FLOAT,
                    bedrooms INTEGER,
                    bathrooms FLOAT,
                    last_sale_date TIMESTAMP,
                    last_sale_price FLOAT,
                    latitude FLOAT,
                    longitude FLOAT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
        elif data_type == "sales":
            db.session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    sale_id VARCHAR(64) UNIQUE NOT NULL,
                    parcel_id VARCHAR(64) NOT NULL,
                    sale_date TIMESTAMP,
                    sale_price FLOAT,
                    buyer_name VARCHAR(128),
                    seller_name VARCHAR(128),
                    deed_type VARCHAR(64),
                    verified BOOLEAN,
                    qualified BOOLEAN,
                    verification_notes TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
        elif data_type == "valuation":
            db.session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    valuation_id VARCHAR(64) UNIQUE NOT NULL,
                    parcel_id VARCHAR(64) NOT NULL,
                    valuation_date TIMESTAMP,
                    land_value FLOAT,
                    improvement_value FLOAT,
                    total_value FLOAT,
                    assessment_year INTEGER,
                    assessment_method VARCHAR(64),
                    assessor_name VARCHAR(128),
                    notes TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
        else:
            raise ValueError(f"Unknown data type: {data_type}")
            
        db.session.commit()
    
    def _build_export_query(self, data_type: str, filters: Optional[Dict[str, Any]] = None) -> str:
        """
        Build a query for exporting data
        
        Args:
            data_type: Type of data to export (property, sales, valuation)
            filters: Filters to apply to the data
            
        Returns:
            SQL query string
        """
        table_name = f"integration_{data_type}"
        
        # Start with basic query
        query = f"SELECT * FROM {table_name}"
        
        # Add filters if provided
        if filters:
            where_clauses = []
            
            for field, value in filters.items():
                if isinstance(value, (list, tuple)):
                    # IN clause for lists
                    values_str = ", ".join([
                        f"'{v}'" if isinstance(v, str) else str(v)
                        for v in value
                    ])
                    where_clauses.append(f"{field} IN ({values_str})")
                elif isinstance(value, dict):
                    # Range filters
                    if "min" in value:
                        where_clauses.append(f"{field} >= {value['min']}")
                    if "max" in value:
                        where_clauses.append(f"{field} <= {value['max']}")
                    if "like" in value:
                        where_clauses.append(f"{field} LIKE '%{value['like']}%'")
                    if "not" in value:
                        where_clauses.append(f"{field} != '{value['not']}'")
                else:
                    # Exact match
                    if isinstance(value, str):
                        where_clauses.append(f"{field} = '{value}'")
                    else:
                        where_clauses.append(f"{field} = {value}")
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        return query


# Create a global instance
integration_hub = AssessmentDataIntegrationHub()