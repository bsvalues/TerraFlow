"""
Field Mapping Loader

This module loads field mapping configurations from JSON files
and provides them to the ETL system.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MappingLoader:
    """Loads and manages field mappings for ETL operations"""
    
    def __init__(self, mappings_directory: str = None):
        """
        Initialize the mapping loader
        
        Args:
            mappings_directory: Directory where mapping JSON files are stored
        """
        if mappings_directory is None:
            # Default to the mappings directory within sync_service
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.mappings_directory = os.path.join(base_dir, 'mappings')
        else:
            self.mappings_directory = mappings_directory
            
        # Ensure the directory exists
        os.makedirs(self.mappings_directory, exist_ok=True)
        
        # Cache for loaded mappings
        self.mappings_cache = {}
        
        # Initialize the loader
        self._load_all_mappings()
        
    def _load_all_mappings(self) -> None:
        """Load all mapping files into the cache"""
        if not os.path.exists(self.mappings_directory):
            logger.warning(f"Mappings directory not found: {self.mappings_directory}")
            return
            
        # Load each JSON file in the directory
        for filename in os.listdir(self.mappings_directory):
            if filename.endswith('.json'):
                try:
                    file_path = os.path.join(self.mappings_directory, filename)
                    with open(file_path, 'r') as f:
                        mapping_data = json.load(f)
                        
                    # Extract mapping info
                    data_type = mapping_data.get('data_type')
                    name = mapping_data.get('name')
                    
                    if data_type and name:
                        # Cache the mapping by data_type and name
                        if data_type not in self.mappings_cache:
                            self.mappings_cache[data_type] = {}
                            
                        self.mappings_cache[data_type][name] = mapping_data
                        logger.info(f"Loaded mapping: {data_type}/{name} from {filename}")
                except Exception as e:
                    logger.error(f"Error loading mapping file {filename}: {str(e)}")
    
    def get_mapping(self, data_type: str, name: str = 'default') -> Optional[Dict[str, str]]:
        """
        Get a specific field mapping
        
        Args:
            data_type: Type of data ('property', 'sales', 'valuation', 'tax')
            name: Name of the mapping ('default' or custom name)
            
        Returns:
            Dictionary with field mappings or None if not found
        """
        # Refresh cache if needed
        if not self.mappings_cache:
            self._load_all_mappings()
            
        # Get mapping from cache
        type_mappings = self.mappings_cache.get(data_type, {})
        mapping_data = type_mappings.get(name)
        
        if mapping_data:
            return mapping_data.get('mapping', {})
        else:
            logger.warning(f"Mapping not found: {data_type}/{name}")
            
            # Check if there's a default mapping for this data type
            if name != 'default':
                logger.info(f"Falling back to default mapping for {data_type}")
                return self.get_mapping(data_type, 'default')
                
            return None
    
    def list_mappings(self, data_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        List available mappings
        
        Args:
            data_type: Optional filter by data type
            
        Returns:
            Dictionary with data types as keys and lists of mapping names as values
        """
        result = {}
        
        if data_type:
            # List mappings for a specific data type
            type_mappings = self.mappings_cache.get(data_type, {})
            result[data_type] = list(type_mappings.keys())
        else:
            # List all mappings
            for dt, mappings in self.mappings_cache.items():
                result[dt] = list(mappings.keys())
                
        return result
    
    def create_mapping(self, data_type: str, name: str, mapping: Dict[str, str]) -> bool:
        """
        Create a new field mapping
        
        Args:
            data_type: Type of data ('property', 'sales', 'valuation', 'tax')
            name: Name of the mapping
            mapping: Dictionary with field mappings (target_field: source_field)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare mapping data
            mapping_data = {
                'data_type': data_type,
                'name': name,
                'mapping': mapping,
                'created': datetime.now().isoformat()
            }
            
            # Save to file
            filename = f"{data_type}_{name}.json"
            file_path = os.path.join(self.mappings_directory, filename)
            
            with open(file_path, 'w') as f:
                json.dump(mapping_data, f, indent=2)
                
            # Update cache
            if data_type not in self.mappings_cache:
                self.mappings_cache[data_type] = {}
                
            self.mappings_cache[data_type][name] = mapping_data
            
            logger.info(f"Created mapping: {data_type}/{name}")
            return True
        except Exception as e:
            logger.error(f"Error creating mapping {data_type}/{name}: {str(e)}")
            return False
    
    def update_mapping(self, data_type: str, name: str, mapping: Dict[str, str]) -> bool:
        """
        Update an existing field mapping
        
        Args:
            data_type: Type of data ('property', 'sales', 'valuation', 'tax')
            name: Name of the mapping
            mapping: Dictionary with field mappings (target_field: source_field)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if mapping exists
            if data_type in self.mappings_cache and name in self.mappings_cache[data_type]:
                # Get existing mapping
                existing = self.mappings_cache[data_type][name]
                
                # Update mapping data
                mapping_data = {
                    'data_type': data_type,
                    'name': name,
                    'mapping': mapping,
                    'created': existing.get('created'),
                    'updated': datetime.now().isoformat()
                }
                
                # Save to file
                filename = f"{data_type}_{name}.json"
                file_path = os.path.join(self.mappings_directory, filename)
                
                with open(file_path, 'w') as f:
                    json.dump(mapping_data, f, indent=2)
                    
                # Update cache
                self.mappings_cache[data_type][name] = mapping_data
                
                logger.info(f"Updated mapping: {data_type}/{name}")
                return True
            else:
                logger.warning(f"Cannot update non-existent mapping: {data_type}/{name}")
                return False
        except Exception as e:
            logger.error(f"Error updating mapping {data_type}/{name}: {str(e)}")
            return False
    
    def delete_mapping(self, data_type: str, name: str) -> bool:
        """
        Delete a field mapping
        
        Args:
            data_type: Type of data ('property', 'sales', 'valuation', 'tax')
            name: Name of the mapping
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Don't allow deletion of default mappings
            if name == 'default':
                logger.warning("Cannot delete default mapping")
                return False
                
            # Check if mapping exists
            if data_type in self.mappings_cache and name in self.mappings_cache[data_type]:
                # Remove from cache
                del self.mappings_cache[data_type][name]
                
                # Remove file
                filename = f"{data_type}_{name}.json"
                file_path = os.path.join(self.mappings_directory, filename)
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                logger.info(f"Deleted mapping: {data_type}/{name}")
                return True
            else:
                logger.warning(f"Cannot delete non-existent mapping: {data_type}/{name}")
                return False
        except Exception as e:
            logger.error(f"Error deleting mapping {data_type}/{name}: {str(e)}")
            return False

# Singleton instance
_mapping_loader = None

def get_mapping_loader() -> MappingLoader:
    """
    Get the singleton mapping loader instance
    
    Returns:
        MappingLoader instance
    """
    global _mapping_loader
    
    if _mapping_loader is None:
        _mapping_loader = MappingLoader()
        
    return _mapping_loader