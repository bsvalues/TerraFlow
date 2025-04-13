"""
Property Model Module

This module provides the property model for interacting with the property data in Supabase.
It includes functions for CRUD operations on properties and related assessments.
"""

import os
import datetime
import uuid
from typing import List, Dict, Any, Optional, Union, Tuple

from supabase_client import get_supabase_client, handle_supabase_error
from service_supabase_client import get_service_supabase_client


# Schema Constants
PROPERTY_SCHEMA = "property"
PROPERTY_TABLE = "properties"
ASSESSMENT_TABLE = "property_assessments"
FILE_TABLE = "property_files"


def get_properties(
    page: int = 1,
    per_page: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int, bool]:
    """
    Get a list of properties with pagination and filtering
    
    Args:
        page: Page number (starting from 1)
        per_page: Number of items per page
        filters: Optional dictionary of filters
        user_id: Optional user ID for access control
        
    Returns:
        Tuple of (list of properties, total count, has more)
    """
    try:
        client = get_supabase_client()
        if client is None:
            return [], 0, False
        
        # Start query
        query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}")
        
        # Apply access control if user_id is provided
        if user_id:
            query = query.eq("created_by", user_id)
        
        # Apply filters
        if filters:
            query = _apply_property_filters(query, filters)
        
        # Get total count for pagination
        count_query = query
        total_count = len(count_query.execute().data)
        
        # Apply pagination
        start = (page - 1) * per_page
        end = start + per_page - 1
        
        # Get data with pagination
        query = query.order("created_at", desc=True).range(start, end)
        response = query.execute()
        
        properties = response.data
        
        # Check if there are more pages
        has_more = total_count > (page * per_page)
        
        return properties, total_count, has_more
    except Exception as e:
        handle_supabase_error(e, "Error fetching properties")
        return [], 0, False


def get_property(property_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get a single property by ID
    
    Args:
        property_id: Property ID
        user_id: Optional user ID for access control
        
    Returns:
        Property data or None if not found
    """
    try:
        client = get_supabase_client()
        if client is None:
            return None
        
        query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id)
        
        # Apply access control if user_id is provided
        if user_id:
            query = query.eq("created_by", user_id)
        
        response = query.execute()
        
        if not response.data:
            return None
        
        return response.data[0]
    except Exception as e:
        handle_supabase_error(e, f"Error fetching property {property_id}")
        return None


def create_property(property_data: Dict[str, Any], user_id: str) -> Optional[str]:
    """
    Create a new property
    
    Args:
        property_data: Property data
        user_id: User ID of the creator
        
    Returns:
        New property ID or None on error
    """
    try:
        client = get_supabase_client()
        if client is None:
            return None
        
        # Set created_by and created_at
        property_data["created_by"] = user_id
        property_data["created_at"] = datetime.datetime.now().isoformat()
        property_data["updated_at"] = datetime.datetime.now().isoformat()
        
        # Set default status if not provided
        if "status" not in property_data:
            property_data["status"] = "active"
        
        # Calculate total value if not provided
        if "total_value" not in property_data and "land_value" in property_data and "improvement_value" in property_data:
            land_value = float(property_data.get("land_value", 0) or 0)
            improvement_value = float(property_data.get("improvement_value", 0) or 0)
            property_data["total_value"] = land_value + improvement_value
        
        response = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").insert(property_data).execute()
        
        if not response.data:
            return None
        
        return response.data[0]["id"]
    except Exception as e:
        handle_supabase_error(e, "Error creating property")
        return None


def update_property(property_id: str, property_data: Dict[str, Any], user_id: Optional[str] = None) -> bool:
    """
    Update a property
    
    Args:
        property_id: Property ID
        property_data: Updated property data
        user_id: Optional user ID for access control
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_supabase_client()
        if client is None:
            return False
        
        # Set updated_at
        property_data["updated_at"] = datetime.datetime.now().isoformat()
        
        # Calculate total value if not provided
        if "total_value" not in property_data and "land_value" in property_data and "improvement_value" in property_data:
            land_value = float(property_data.get("land_value", 0) or 0)
            improvement_value = float(property_data.get("improvement_value", 0) or 0)
            property_data["total_value"] = land_value + improvement_value
        
        query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id)
        
        # Apply access control if user_id is provided
        if user_id:
            query = query.eq("created_by", user_id)
        
        response = query.update(property_data).execute()
        
        return bool(response.data)
    except Exception as e:
        handle_supabase_error(e, f"Error updating property {property_id}")
        return False


def delete_property(property_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a property
    
    Args:
        property_id: Property ID
        user_id: Optional user ID for access control
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_supabase_client()
        if client is None:
            return False
        
        query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id)
        
        # Apply access control if user_id is provided
        if user_id:
            query = query.eq("created_by", user_id)
        
        response = query.delete().execute()
        
        return bool(response.data)
    except Exception as e:
        handle_supabase_error(e, f"Error deleting property {property_id}")
        return False


def get_property_assessments(property_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get assessments for a property
    
    Args:
        property_id: Property ID
        user_id: Optional user ID for access control
        
    Returns:
        List of assessments
    """
    try:
        client = get_supabase_client()
        if client is None:
            return []
        
        # First check if user has access to the property
        if user_id:
            property_query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id).eq("created_by", user_id)
            property_response = property_query.execute()
            
            if not property_response.data:
                return []
        
        # Get assessments
        query = client.table(f"{PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}").eq("property_id", property_id).order("tax_year", desc=True)
        response = query.execute()
        
        return response.data or []
    except Exception as e:
        handle_supabase_error(e, f"Error fetching assessments for property {property_id}")
        return []


def get_property_assessment(property_id: str, assessment_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get a specific assessment for a property
    
    Args:
        property_id: Property ID
        assessment_id: Assessment ID
        user_id: Optional user ID for access control
        
    Returns:
        Assessment data or None if not found
    """
    try:
        client = get_supabase_client()
        if client is None:
            return None
        
        # First check if user has access to the property
        if user_id:
            property_query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id).eq("created_by", user_id)
            property_response = property_query.execute()
            
            if not property_response.data:
                return None
        
        # Get assessment
        query = client.table(f"{PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}").eq("id", assessment_id).eq("property_id", property_id)
        response = query.execute()
        
        if not response.data:
            return None
        
        return response.data[0]
    except Exception as e:
        handle_supabase_error(e, f"Error fetching assessment {assessment_id} for property {property_id}")
        return None


def create_property_assessment(property_id: str, assessment_data: Dict[str, Any], user_id: str) -> Optional[str]:
    """
    Create a new assessment for a property
    
    Args:
        property_id: Property ID
        assessment_data: Assessment data
        user_id: User ID of the creator
        
    Returns:
        New assessment ID or None on error
    """
    try:
        client = get_supabase_client()
        if client is None:
            return None
        
        # Check if user has access to the property
        property_query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id).eq("created_by", user_id)
        property_response = property_query.execute()
        
        if not property_response.data:
            return None
        
        # Set property_id, created_by, and created_at
        assessment_data["property_id"] = property_id
        assessment_data["created_by"] = user_id
        assessment_data["created_at"] = datetime.datetime.now().isoformat()
        assessment_data["updated_at"] = datetime.datetime.now().isoformat()
        
        # Set default status if not provided
        if "assessment_status" not in assessment_data:
            assessment_data["assessment_status"] = "pending"
        
        # Calculate taxable value if not provided
        if "taxable_value" not in assessment_data and "total_value" in assessment_data and "exemption_value" in assessment_data:
            total_value = float(assessment_data.get("total_value", 0) or 0)
            exemption_value = float(assessment_data.get("exemption_value", 0) or 0)
            assessment_data["taxable_value"] = max(0, total_value - exemption_value)
        
        response = client.table(f"{PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}").insert(assessment_data).execute()
        
        if not response.data:
            return None
        
        # Update property with latest assessment values
        if "total_value" in assessment_data:
            _update_property_value(property_id, assessment_data)
        
        return response.data[0]["id"]
    except Exception as e:
        handle_supabase_error(e, f"Error creating assessment for property {property_id}")
        return None


def update_property_assessment(property_id: str, assessment_id: str, assessment_data: Dict[str, Any], user_id: Optional[str] = None) -> bool:
    """
    Update a property assessment
    
    Args:
        property_id: Property ID
        assessment_id: Assessment ID
        assessment_data: Updated assessment data
        user_id: Optional user ID for access control
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_supabase_client()
        if client is None:
            return False
        
        # Check if user has access to the property
        if user_id:
            property_query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id).eq("created_by", user_id)
            property_response = property_query.execute()
            
            if not property_response.data:
                return False
        
        # Set updated_at
        assessment_data["updated_at"] = datetime.datetime.now().isoformat()
        
        # Calculate taxable value if not provided
        if "taxable_value" not in assessment_data and "total_value" in assessment_data and "exemption_value" in assessment_data:
            total_value = float(assessment_data.get("total_value", 0) or 0)
            exemption_value = float(assessment_data.get("exemption_value", 0) or 0)
            assessment_data["taxable_value"] = max(0, total_value - exemption_value)
        
        query = client.table(f"{PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}").eq("id", assessment_id).eq("property_id", property_id)
        response = query.update(assessment_data).execute()
        
        if not response.data:
            return False
        
        # Update property with latest assessment values
        if "total_value" in assessment_data:
            _update_property_value(property_id, assessment_data)
        
        return True
    except Exception as e:
        handle_supabase_error(e, f"Error updating assessment {assessment_id} for property {property_id}")
        return False


def delete_property_assessment(property_id: str, assessment_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a property assessment
    
    Args:
        property_id: Property ID
        assessment_id: Assessment ID
        user_id: Optional user ID for access control
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_supabase_client()
        if client is None:
            return False
        
        # Check if user has access to the property
        if user_id:
            property_query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id).eq("created_by", user_id)
            property_response = property_query.execute()
            
            if not property_response.data:
                return False
        
        query = client.table(f"{PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}").eq("id", assessment_id).eq("property_id", property_id)
        response = query.delete().execute()
        
        return bool(response.data)
    except Exception as e:
        handle_supabase_error(e, f"Error deleting assessment {assessment_id} for property {property_id}")
        return False


def get_property_files(property_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get files for a property
    
    Args:
        property_id: Property ID
        user_id: Optional user ID for access control
        
    Returns:
        List of files
    """
    try:
        client = get_supabase_client()
        if client is None:
            return []
        
        # First check if user has access to the property
        if user_id:
            property_query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id).eq("created_by", user_id)
            property_response = property_query.execute()
            
            if not property_response.data:
                return []
        
        # Get files
        query = client.table(f"{PROPERTY_SCHEMA}.{FILE_TABLE}").eq("property_id", property_id).order("created_at", desc=True)
        response = query.execute()
        
        files = response.data or []
        
        # Enhance with public URLs if storage is available
        storage_client = get_service_supabase_client()
        if storage_client:
            bucket_name = f"{PROPERTY_SCHEMA}_files"
            
            for file in files:
                file_path = f"{property_id}/{file['id']}/{file['file_name']}"
                try:
                    file["public_url"] = storage_client.storage.from_(bucket_name).get_public_url(file_path)
                except Exception:
                    file["public_url"] = ""
        
        return files
    except Exception as e:
        handle_supabase_error(e, f"Error fetching files for property {property_id}")
        return []


def create_property_file(property_id: str, file_data: Dict[str, Any], file_content: bytes, user_id: str) -> Optional[str]:
    """
    Create a new file for a property
    
    Args:
        property_id: Property ID
        file_data: File metadata
        file_content: File binary content
        user_id: User ID of the creator
        
    Returns:
        New file ID or None on error
    """
    try:
        client = get_supabase_client()
        storage_client = get_service_supabase_client()
        
        if client is None or storage_client is None:
            return None
        
        # Check if user has access to the property
        property_query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id).eq("created_by", user_id)
        property_response = property_query.execute()
        
        if not property_response.data:
            return None
        
        # Create file record
        file_id = str(uuid.uuid4())
        file_data["id"] = file_id
        file_data["property_id"] = property_id
        file_data["created_by"] = user_id
        file_data["created_at"] = datetime.datetime.now().isoformat()
        
        # Upload file to storage
        bucket_name = f"{PROPERTY_SCHEMA}_files"
        file_path = f"{property_id}/{file_id}/{file_data['file_name']}"
        
        try:
            # Ensure bucket exists
            response = storage_client.storage.get_bucket(bucket_name)
        except Exception:
            # Create bucket if it doesn't exist
            storage_client.storage.create_bucket(bucket_name, options={"public": True})
        
        # Upload file
        storage_client.storage.from_(bucket_name).upload(file_path, file_content)
        
        # Generate public URL
        file_data["public_url"] = storage_client.storage.from_(bucket_name).get_public_url(file_path)
        
        # Save file record
        response = client.table(f"{PROPERTY_SCHEMA}.{FILE_TABLE}").insert(file_data).execute()
        
        if not response.data:
            # Clean up storage if database insertion fails
            storage_client.storage.from_(bucket_name).remove(file_path)
            return None
        
        return file_id
    except Exception as e:
        handle_supabase_error(e, f"Error creating file for property {property_id}")
        return None


def delete_property_file(property_id: str, file_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a property file
    
    Args:
        property_id: Property ID
        file_id: File ID
        user_id: Optional user ID for access control
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_supabase_client()
        storage_client = get_service_supabase_client()
        
        if client is None:
            return False
        
        # Check if user has access to the property
        if user_id:
            property_query = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id).eq("created_by", user_id)
            property_response = property_query.execute()
            
            if not property_response.data:
                return False
        
        # Get file info to determine file name
        file_query = client.table(f"{PROPERTY_SCHEMA}.{FILE_TABLE}").eq("id", file_id).eq("property_id", property_id)
        file_response = file_query.execute()
        
        if not file_response.data:
            return False
        
        file_name = file_response.data[0]["file_name"]
        
        # Delete file record
        response = file_query.delete().execute()
        
        if not response.data:
            return False
        
        # Delete from storage if client is available
        if storage_client:
            bucket_name = f"{PROPERTY_SCHEMA}_files"
            file_path = f"{property_id}/{file_id}/{file_name}"
            
            try:
                storage_client.storage.from_(bucket_name).remove(file_path)
            except Exception:
                # Continue even if storage deletion fails
                pass
        
        return True
    except Exception as e:
        handle_supabase_error(e, f"Error deleting file {file_id} for property {property_id}")
        return False


def _apply_property_filters(query, filters: Dict[str, Any]):
    """Apply filters to a property query"""
    for key, value in filters.items():
        if not value:
            continue
        
        if key == "parcel_id":
            query = query.eq("parcel_id", value)
        elif key == "property_class":
            query = query.eq("property_class", value)
        elif key == "address_like":
            query = query.ilike("address", f"%{value}%")
        elif key == "city":
            query = query.eq("city", value)
        elif key == "state":
            query = query.eq("state", value)
        elif key == "status":
            query = query.eq("status", value)
        elif key == "zip_code":
            query = query.eq("zip_code", value)
        elif key == "total_value_gte":
            query = query.gte("total_value", float(value))
        elif key == "total_value_lte":
            query = query.lte("total_value", float(value))
        elif key == "year_built_gte":
            query = query.gte("year_built", int(value))
        elif key == "year_built_lte":
            query = query.lte("year_built", int(value))
        elif key == "land_area_gte":
            query = query.gte("land_area", float(value))
        elif key == "land_area_lte":
            query = query.lte("land_area", float(value))
        elif key == "living_area_gte":
            query = query.gte("living_area", float(value))
        elif key == "living_area_lte":
            query = query.lte("living_area", float(value))
    
    return query


def _update_property_value(property_id: str, assessment_data: Dict[str, Any]) -> bool:
    """Update property with latest assessment values"""
    try:
        client = get_supabase_client()
        if client is None:
            return False
        
        update_data = {
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        if "total_value" in assessment_data:
            update_data["total_value"] = assessment_data["total_value"]
        
        if "land_value" in assessment_data:
            update_data["land_value"] = assessment_data["land_value"]
        
        if "improvement_value" in assessment_data:
            update_data["improvement_value"] = assessment_data["improvement_value"]
        
        response = client.table(f"{PROPERTY_SCHEMA}.{PROPERTY_TABLE}").eq("id", property_id).update(update_data).execute()
        
        return bool(response.data)
    except Exception as e:
        handle_supabase_error(e, f"Error updating property values for {property_id}")
        return False


def get_schema_setup_sql() -> str:
    """
    Get SQL for setting up the property schema and tables
    
    Returns:
        SQL string for schema setup
    """
    return f"""
    -- Create schema if it doesn't exist
    CREATE SCHEMA IF NOT EXISTS {PROPERTY_SCHEMA};
    
    -- Create properties table
    CREATE TABLE IF NOT EXISTS {PROPERTY_SCHEMA}.{PROPERTY_TABLE} (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        parcel_id TEXT NOT NULL,
        account_number TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        zip_code TEXT,
        property_class TEXT,
        zoning TEXT,
        legal_description TEXT,
        land_area NUMERIC,
        lot_size NUMERIC,
        status TEXT DEFAULT 'active',
        owner_name TEXT,
        owner_address TEXT,
        owner_city TEXT,
        owner_state TEXT,
        owner_zip TEXT,
        year_built INTEGER,
        living_area NUMERIC,
        bedrooms INTEGER,
        bathrooms NUMERIC,
        latitude NUMERIC,
        longitude NUMERIC,
        land_value NUMERIC,
        improvement_value NUMERIC,
        total_value NUMERIC,
        last_sale_date DATE,
        last_sale_price NUMERIC,
        last_sale_document TEXT,
        created_by UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Create assessments table
    CREATE TABLE IF NOT EXISTS {PROPERTY_SCHEMA}.{ASSESSMENT_TABLE} (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        property_id UUID NOT NULL REFERENCES {PROPERTY_SCHEMA}.{PROPERTY_TABLE}(id) ON DELETE CASCADE,
        tax_year INTEGER NOT NULL,
        assessment_date DATE,
        land_value NUMERIC,
        improvement_value NUMERIC,
        total_value NUMERIC,
        exemption_value NUMERIC DEFAULT 0,
        taxable_value NUMERIC,
        assessment_type TEXT,
        assessment_status TEXT DEFAULT 'pending',
        notes TEXT,
        created_by UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Create files table
    CREATE TABLE IF NOT EXISTS {PROPERTY_SCHEMA}.{FILE_TABLE} (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        property_id UUID NOT NULL REFERENCES {PROPERTY_SCHEMA}.{PROPERTY_TABLE}(id) ON DELETE CASCADE,
        file_name TEXT NOT NULL,
        file_size INTEGER,
        file_type TEXT,
        file_category TEXT,
        description TEXT,
        public_url TEXT,
        created_by UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_{PROPERTY_TABLE}_parcel_id ON {PROPERTY_SCHEMA}.{PROPERTY_TABLE}(parcel_id);
    CREATE INDEX IF NOT EXISTS idx_{PROPERTY_TABLE}_address ON {PROPERTY_SCHEMA}.{PROPERTY_TABLE}(address);
    CREATE INDEX IF NOT EXISTS idx_{PROPERTY_TABLE}_created_by ON {PROPERTY_SCHEMA}.{PROPERTY_TABLE}(created_by);
    CREATE INDEX IF NOT EXISTS idx_{PROPERTY_TABLE}_property_class ON {PROPERTY_SCHEMA}.{PROPERTY_TABLE}(property_class);
    CREATE INDEX IF NOT EXISTS idx_{PROPERTY_TABLE}_status ON {PROPERTY_SCHEMA}.{PROPERTY_TABLE}(status);
    
    CREATE INDEX IF NOT EXISTS idx_{ASSESSMENT_TABLE}_property_id ON {PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}(property_id);
    CREATE INDEX IF NOT EXISTS idx_{ASSESSMENT_TABLE}_tax_year ON {PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}(tax_year);
    CREATE INDEX IF NOT EXISTS idx_{ASSESSMENT_TABLE}_assessment_status ON {PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}(assessment_status);
    
    CREATE INDEX IF NOT EXISTS idx_{FILE_TABLE}_property_id ON {PROPERTY_SCHEMA}.{FILE_TABLE}(property_id);
    CREATE INDEX IF NOT EXISTS idx_{FILE_TABLE}_file_category ON {PROPERTY_SCHEMA}.{FILE_TABLE}(file_category);
    
    -- Enable RLS
    ALTER TABLE {PROPERTY_SCHEMA}.{PROPERTY_TABLE} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {PROPERTY_SCHEMA}.{ASSESSMENT_TABLE} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {PROPERTY_SCHEMA}.{FILE_TABLE} ENABLE ROW LEVEL SECURITY;
    
    -- Create policies
    CREATE POLICY IF NOT EXISTS "Allow individual read access" ON {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
        FOR SELECT USING (auth.uid() = created_by);
        
    CREATE POLICY IF NOT EXISTS "Allow individual insert access" ON {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
        FOR INSERT WITH CHECK (auth.uid() = created_by);
        
    CREATE POLICY IF NOT EXISTS "Allow individual update access" ON {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
        FOR UPDATE USING (auth.uid() = created_by);
        
    CREATE POLICY IF NOT EXISTS "Allow individual delete access" ON {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
        FOR DELETE USING (auth.uid() = created_by);
    
    -- Assessment policies
    CREATE POLICY IF NOT EXISTS "Allow individual read access" ON {PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}
        FOR SELECT USING (
            auth.uid() IN (
                SELECT created_by FROM {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
                WHERE id = property_id
            )
        );
        
    CREATE POLICY IF NOT EXISTS "Allow individual insert access" ON {PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}
        FOR INSERT WITH CHECK (
            auth.uid() IN (
                SELECT created_by FROM {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
                WHERE id = property_id
            )
        );
        
    CREATE POLICY IF NOT EXISTS "Allow individual update access" ON {PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}
        FOR UPDATE USING (
            auth.uid() IN (
                SELECT created_by FROM {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
                WHERE id = property_id
            )
        );
        
    CREATE POLICY IF NOT EXISTS "Allow individual delete access" ON {PROPERTY_SCHEMA}.{ASSESSMENT_TABLE}
        FOR DELETE USING (
            auth.uid() IN (
                SELECT created_by FROM {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
                WHERE id = property_id
            )
        );
    
    -- File policies
    CREATE POLICY IF NOT EXISTS "Allow individual read access" ON {PROPERTY_SCHEMA}.{FILE_TABLE}
        FOR SELECT USING (
            auth.uid() IN (
                SELECT created_by FROM {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
                WHERE id = property_id
            )
        );
        
    CREATE POLICY IF NOT EXISTS "Allow individual insert access" ON {PROPERTY_SCHEMA}.{FILE_TABLE}
        FOR INSERT WITH CHECK (
            auth.uid() IN (
                SELECT created_by FROM {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
                WHERE id = property_id
            )
        );
        
    CREATE POLICY IF NOT EXISTS "Allow individual delete access" ON {PROPERTY_SCHEMA}.{FILE_TABLE}
        FOR DELETE USING (
            auth.uid() IN (
                SELECT created_by FROM {PROPERTY_SCHEMA}.{PROPERTY_TABLE}
                WHERE id = property_id
            )
        );
    """