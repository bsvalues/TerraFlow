"""
Property Model Module

This module defines the Property model and related models for property assessment.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from supabase_client import (
    get_supabase_client, execute_query, insert_record, update_record, delete_record
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Property:
    """
    Property model for managing property data in Supabase.
    """
    
    TABLE_NAME = "properties"
    
    def __init__(self, data: Dict[str, Any] = None):
        """
        Initialize a property object.
        
        Args:
            data: Optional dictionary of property data
        """
        self.id = None
        self.parcel_id = None
        self.account_number = None
        self.legal_description = None
        self.address = None
        self.city = None
        self.state = "WA"
        self.zip_code = None
        self.latitude = None
        self.longitude = None
        self.geometry = None
        self.property_class = None
        self.zoning = None
        self.land_area = None
        self.land_value = None
        self.improvement_value = None
        self.total_value = None
        self.year_built = None
        self.bedrooms = None
        self.bathrooms = None
        self.living_area = None
        self.lot_size = None
        self.owner_name = None
        self.owner_address = None
        self.owner_city = None
        self.owner_state = None
        self.owner_zip = None
        self.last_sale_date = None
        self.last_sale_price = None
        self.last_sale_document = None
        self.status = "active"
        self.created_at = None
        self.updated_at = None
        self.data = {}
        
        # Load data if provided
        if data:
            self.load_data(data)
    
    def load_data(self, data: Dict[str, Any]) -> None:
        """
        Load property data from a dictionary.
        
        Args:
            data: Dictionary of property data
        """
        # Map dictionary keys to object attributes
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the property to a dictionary.
        
        Returns:
            Dictionary representation of the property
        """
        # Get all properties of the object that don't start with _
        return {
            key: value 
            for key, value in self.__dict__.items()
            if not key.startswith('_') and value is not None
        }
    
    def save(self) -> bool:
        """
        Save the property to the database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            data = self.to_dict()
            
            # If the property has an ID, update it
            if self.id:
                result = update_record(self.TABLE_NAME, self.id, data)
                if result:
                    logger.info(f"Updated property: {self.parcel_id}")
                    self.load_data(result)
                    return True
                return False
            
            # Otherwise, insert a new property
            result = insert_record(self.TABLE_NAME, data)
            if result:
                logger.info(f"Created property: {self.parcel_id}")
                self.load_data(result)
                return True
            return False
        except Exception as e:
            logger.error(f"Error saving property: {str(e)}")
            return False
    
    def delete(self) -> bool:
        """
        Delete the property from the database.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.id:
            logger.error("Cannot delete property without ID")
            return False
        
        try:
            result = delete_record(self.TABLE_NAME, self.id)
            if result:
                logger.info(f"Deleted property: {self.parcel_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting property: {str(e)}")
            return False
    
    @classmethod
    def get_by_id(cls, property_id: Union[str, uuid.UUID]) -> Optional['Property']:
        """
        Get a property by ID.
        
        Args:
            property_id: Property ID
            
        Returns:
            Property object or None if not found
        """
        try:
            result = execute_query(cls.TABLE_NAME, "*", {"id": str(property_id)})
            if result and len(result) > 0:
                return cls(result[0])
            return None
        except Exception as e:
            logger.error(f"Error getting property by ID: {str(e)}")
            return None
    
    @classmethod
    def get_by_parcel_id(cls, parcel_id: str) -> Optional['Property']:
        """
        Get a property by parcel ID.
        
        Args:
            parcel_id: Parcel ID
            
        Returns:
            Property object or None if not found
        """
        try:
            result = execute_query(cls.TABLE_NAME, "*", {"parcel_id": parcel_id})
            if result and len(result) > 0:
                return cls(result[0])
            return None
        except Exception as e:
            logger.error(f"Error getting property by parcel ID: {str(e)}")
            return None
    
    @classmethod
    def search(cls, query: Dict[str, Any], limit: int = 100, offset: int = 0) -> List['Property']:
        """
        Search for properties.
        
        Args:
            query: Search query dictionary
            limit: Maximum number of results
            offset: Result offset
            
        Returns:
            List of Property objects
        """
        try:
            # Get a client for custom query
            client = get_supabase_client()
            if not client:
                return []
            
            # Start building the query
            db_query = client.table(cls.TABLE_NAME).select("*")
            
            # Apply filters
            for key, value in query.items():
                if isinstance(value, dict):
                    # Handle operators
                    for op, op_value in value.items():
                        if op == "eq":
                            db_query = db_query.eq(key, op_value)
                        elif op == "neq":
                            db_query = db_query.neq(key, op_value)
                        elif op == "gt":
                            db_query = db_query.gt(key, op_value)
                        elif op == "gte":
                            db_query = db_query.gte(key, op_value)
                        elif op == "lt":
                            db_query = db_query.lt(key, op_value)
                        elif op == "lte":
                            db_query = db_query.lte(key, op_value)
                        elif op == "like":
                            db_query = db_query.ilike(key, f"%{op_value}%")
                else:
                    # Simple equality
                    db_query = db_query.eq(key, value)
            
            # Apply pagination
            db_query = db_query.range(offset, offset + limit - 1)
            
            # Execute the query
            result = db_query.execute()
            
            # Convert to Property objects
            if result.data:
                return [cls(item) for item in result.data]
            return []
        except Exception as e:
            logger.error(f"Error searching properties: {str(e)}")
            return []
    
    @classmethod
    def find_nearby(cls, latitude: float, longitude: float, distance_meters: float = 1000, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find properties near a location.
        
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            distance_meters: Maximum distance in meters
            limit: Maximum number of results
            
        Returns:
            List of nearby properties with distance
        """
        try:
            # Get a client for custom function call
            client = get_supabase_client()
            if not client:
                return []
            
            # Call the PostGIS-based function
            result = client.rpc(
                'find_nearby_properties',
                {
                    'p_latitude': latitude,
                    'p_longitude': longitude,
                    'p_distance_meters': distance_meters,
                    'p_limit': limit
                }
            ).execute()
            
            if hasattr(result, 'data'):
                return result.data
            return []
        except Exception as e:
            logger.error(f"Error finding nearby properties: {str(e)}")
            return []
    
    @classmethod
    def find_comparables(cls, property_id: Union[str, uuid.UUID], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find comparable properties for a given property.
        
        Args:
            property_id: ID of the property to find comparables for
            limit: Maximum number of results
            
        Returns:
            List of comparable properties with similarity scores
        """
        try:
            # Get a client for custom function call
            client = get_supabase_client()
            if not client:
                return []
            
            # Call the comparable properties function
            result = client.rpc(
                'find_comparable_properties',
                {
                    'p_property_id': str(property_id),
                    'p_limit': limit
                }
            ).execute()
            
            if hasattr(result, 'data'):
                return result.data
            return []
        except Exception as e:
            logger.error(f"Error finding comparable properties: {str(e)}")
            return []
    
    def get_assessments(self) -> List[Dict[str, Any]]:
        """
        Get all assessments for this property.
        
        Returns:
            List of assessment records
        """
        if not self.id:
            logger.error("Cannot get assessments without property ID")
            return []
        
        try:
            result = execute_query("assessments", "*", {"property_id": str(self.id)})
            return result or []
        except Exception as e:
            logger.error(f"Error getting property assessments: {str(e)}")
            return []
    
    def get_inspection_records(self) -> List[Dict[str, Any]]:
        """
        Get all inspection records for this property.
        
        Returns:
            List of inspection records
        """
        if not self.id:
            logger.error("Cannot get inspection records without property ID")
            return []
        
        try:
            result = execute_query("inspection_records", "*", {"property_id": str(self.id)})
            return result or []
        except Exception as e:
            logger.error(f"Error getting property inspection records: {str(e)}")
            return []
    
    def get_tax_appeals(self) -> List[Dict[str, Any]]:
        """
        Get all tax appeals for this property.
        
        Returns:
            List of tax appeal records
        """
        if not self.id:
            logger.error("Cannot get tax appeals without property ID")
            return []
        
        try:
            result = execute_query("tax_appeals", "*", {"property_id": str(self.id)})
            return result or []
        except Exception as e:
            logger.error(f"Error getting property tax appeals: {str(e)}")
            return []
    
    def get_files(self) -> List[Dict[str, Any]]:
        """
        Get all files for this property.
        
        Returns:
            List of file records
        """
        if not self.id:
            logger.error("Cannot get files without property ID")
            return []
        
        try:
            result = execute_query("property_files", "*", {"property_id": str(self.id)})
            return result or []
        except Exception as e:
            logger.error(f"Error getting property files: {str(e)}")
            return []


class Assessment:
    """
    Assessment model for managing property assessments in Supabase.
    """
    
    TABLE_NAME = "assessments"
    
    def __init__(self, data: Dict[str, Any] = None):
        """
        Initialize an assessment object.
        
        Args:
            data: Optional dictionary of assessment data
        """
        self.id = None
        self.property_id = None
        self.tax_year = None
        self.assessment_date = None
        self.land_value = None
        self.improvement_value = None
        self.total_value = None
        self.exemption_value = 0
        self.taxable_value = None
        self.assessment_type = None
        self.assessment_status = "pending"
        self.assessor_id = None
        self.notes = None
        self.created_at = None
        self.updated_at = None
        self.data = {}
        
        # Load data if provided
        if data:
            self.load_data(data)
    
    def load_data(self, data: Dict[str, Any]) -> None:
        """
        Load assessment data from a dictionary.
        
        Args:
            data: Dictionary of assessment data
        """
        # Map dictionary keys to object attributes
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the assessment to a dictionary.
        
        Returns:
            Dictionary representation of the assessment
        """
        # Get all properties of the object that don't start with _
        return {
            key: value 
            for key, value in self.__dict__.items()
            if not key.startswith('_') and value is not None
        }
    
    def calculate_taxable_value(self) -> float:
        """
        Calculate the taxable value of the property.
        
        Returns:
            Calculated taxable value
        """
        if self.total_value is None:
            return 0
        
        exemption = self.exemption_value or 0
        return max(0, self.total_value - exemption)
    
    def save(self) -> bool:
        """
        Save the assessment to the database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate taxable value
            if self.total_value is not None:
                self.taxable_value = self.calculate_taxable_value()
            
            data = self.to_dict()
            
            # If the assessment has an ID, update it
            if self.id:
                result = update_record(self.TABLE_NAME, self.id, data)
                if result:
                    logger.info(f"Updated assessment for property {self.property_id}, year {self.tax_year}")
                    self.load_data(result)
                    return True
                return False
            
            # Otherwise, insert a new assessment
            result = insert_record(self.TABLE_NAME, data)
            if result:
                logger.info(f"Created assessment for property {self.property_id}, year {self.tax_year}")
                self.load_data(result)
                return True
            return False
        except Exception as e:
            logger.error(f"Error saving assessment: {str(e)}")
            return False
    
    def delete(self) -> bool:
        """
        Delete the assessment from the database.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.id:
            logger.error("Cannot delete assessment without ID")
            return False
        
        try:
            result = delete_record(self.TABLE_NAME, self.id)
            if result:
                logger.info(f"Deleted assessment: {self.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting assessment: {str(e)}")
            return False
    
    @classmethod
    def get_by_id(cls, assessment_id: Union[str, uuid.UUID]) -> Optional['Assessment']:
        """
        Get an assessment by ID.
        
        Args:
            assessment_id: Assessment ID
            
        Returns:
            Assessment object or None if not found
        """
        try:
            result = execute_query(cls.TABLE_NAME, "*", {"id": str(assessment_id)})
            if result and len(result) > 0:
                return cls(result[0])
            return None
        except Exception as e:
            logger.error(f"Error getting assessment by ID: {str(e)}")
            return None
    
    @classmethod
    def get_by_property_and_year(cls, property_id: Union[str, uuid.UUID], tax_year: int) -> Optional['Assessment']:
        """
        Get an assessment by property ID and tax year.
        
        Args:
            property_id: Property ID
            tax_year: Tax year
            
        Returns:
            Assessment object or None if not found
        """
        try:
            result = execute_query(
                cls.TABLE_NAME, 
                "*", 
                {
                    "property_id": str(property_id),
                    "tax_year": tax_year
                }
            )
            if result and len(result) > 0:
                return cls(result[0])
            return None
        except Exception as e:
            logger.error(f"Error getting assessment by property and year: {str(e)}")
            return None