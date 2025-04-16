"""
Assessment API Module

This module provides API endpoints for property assessment data and functionality.
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import func, desc, cast, Float
from shapely.geometry import Point, shape
import geopandas as gpd

from models import db, Property, User, GISProject, File
from app import login_required, permission_required

# Custom JSON encoder for handling special types
class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle UUID, Decimal, datetime and date objects"""
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super(CustomJSONEncoder, self).default(obj)

# Create blueprint
assessment_bp = Blueprint('assessment', __name__, url_prefix='/api/assessment')

# Setup logging
logger = logging.getLogger(__name__)

@assessment_bp.route('/properties', methods=['GET'])
@login_required
@permission_required('view_properties')
def get_properties():
    """
    Get properties based on filter criteria
    
    Query parameters:
    - property_type: Filter by property type (residential, commercial, etc.)
    - min_value: Minimum assessed value
    - max_value: Maximum assessed value
    - year_built_min: Minimum year built
    - year_built_max: Maximum year built
    - limit: Maximum number of properties to return (default 100)
    - offset: Offset for pagination (default 0)
    
    Returns:
        JSON response with properties
    """
    try:
        # Get query parameters
        property_type = request.args.get('property_type')
        min_value = request.args.get('min_value', type=float)
        max_value = request.args.get('max_value', type=float)
        year_built_min = request.args.get('year_built_min', type=int)
        year_built_max = request.args.get('year_built_max', type=int)
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = Property.query
        
        # Apply filters
        if property_type:
            query = query.filter(Property.property_type == property_type)
        
        if min_value is not None:
            query = query.filter(cast(Property.assessed_value, Float) >= min_value)
        
        if max_value is not None:
            query = query.filter(cast(Property.assessed_value, Float) <= max_value)
        
        if year_built_min is not None:
            query = query.filter(Property.year_built >= year_built_min)
        
        if year_built_max is not None:
            query = query.filter(Property.year_built <= year_built_max)
        
        # Execute query with limit and offset
        properties = query.limit(limit).offset(offset).all()
        
        # Convert to dictionaries
        property_list = []
        for prop in properties:
            # Get coordinates from location GeoJSON
            coordinates = None
            if prop.location and isinstance(prop.location, dict) and 'coordinates' in prop.location:
                coordinates = prop.location['coordinates']
            
            # Build property dictionary
            property_dict = {
                'id': str(prop.id),
                'parcel_id': prop.parcel_id,
                'address': prop.address,
                'property_type': prop.property_type,
                'assessed_value': float(prop.assessed_value) if prop.assessed_value else None,
                'lot_size': prop.lot_size,
                'year_built': prop.year_built,
                'owner_name': prop.owner_name,
                'zoning': prop.property_metadata.get('zoning', None) if prop.property_metadata else None
            }
            
            # Add property-type specific fields
            if prop.property_type == 'residential':
                property_dict.update({
                    'bedrooms': prop.features.get('bedrooms', None) if prop.features else None,
                    'bathrooms': prop.features.get('bathrooms', None) if prop.features else None,
                    'total_area': prop.total_area
                })
            elif prop.property_type in ['commercial', 'industrial']:
                property_dict.update({
                    'building_area': prop.features.get('building_area', None) if prop.features else None
                })
            
            # Add coordinates if available
            if coordinates:
                property_dict.update({
                    'lng': coordinates[0],
                    'lat': coordinates[1]
                })
            else:
                # Fallback to dummy coordinates if not available
                # In real app, this would come from geocoding or stored coordinates
                property_dict.update({
                    'lng': -119.2 + (offset * 0.01),
                    'lat': 46.2 + (offset * 0.01)
                })
            
            property_list.append(property_dict)
        
        # Return JSON response
        return jsonify({
            'success': True,
            'count': len(property_list),
            'properties': property_list
        })
    
    except Exception as e:
        logger.error(f"Error getting properties: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting properties: {str(e)}"
        }), 500

@assessment_bp.route('/properties/<property_id>', methods=['GET'])
@login_required
@permission_required('view_properties')
def get_property(property_id):
    """
    Get a specific property by ID
    
    Args:
        property_id: Property ID (UUID)
    
    Returns:
        JSON response with property details
    """
    try:
        # Get property
        property = Property.query.get(property_id)
        
        if not property:
            return jsonify({
                'success': False,
                'message': 'Property not found'
            }), 404
        
        # Get coordinates from location GeoJSON
        coordinates = None
        if property.location and isinstance(property.location, dict) and 'coordinates' in property.location:
            coordinates = property.location['coordinates']
        
        # Build property dictionary with all details
        property_data = {
            'id': str(property.id),
            'parcel_id': property.parcel_id,
            'address': property.address,
            'city': property.city,
            'state': property.state,
            'zip_code': property.zip_code,
            'property_type': property.property_type,
            'assessed_value': float(property.assessed_value) if property.assessed_value else None,
            'lot_size': property.lot_size,
            'total_area': property.total_area,
            'year_built': property.year_built,
            'bedrooms': property.bedrooms,
            'bathrooms': property.bathrooms,
            'owner_name': property.owner_name,
            'owner_address': property.owner_address,
            'purchase_date': property.purchase_date.isoformat() if property.purchase_date else None,
            'purchase_price': float(property.purchase_price) if property.purchase_price else None,
            'features': property.features,
            'metadata': property.property_metadata
        }
        
        # Add coordinates if available
        if coordinates:
            property_data.update({
                'location': {
                    'type': 'Point',
                    'coordinates': coordinates
                }
            })
        
        # Return JSON response
        return jsonify({
            'success': True,
            'property': property_data
        })
    
    except Exception as e:
        logger.error(f"Error getting property {property_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting property: {str(e)}"
        }), 500

@assessment_bp.route('/properties/<property_id>', methods=['PUT'])
@login_required
@permission_required('edit_properties')
def update_property(property_id):
    """
    Update a property
    
    Args:
        property_id: Property ID (UUID)
    
    Returns:
        JSON response with updated property
    """
    try:
        # Get property
        property = Property.query.get(property_id)
        
        if not property:
            return jsonify({
                'success': False,
                'message': 'Property not found'
            }), 404
        
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Update fields
        for field in ['address', 'city', 'state', 'zip_code', 'property_type', 
                    'lot_size', 'total_area', 'year_built', 'bedrooms', 'bathrooms',
                    'owner_name', 'owner_address']:
            if field in data:
                setattr(property, field, data[field])
        
        # Update decimal fields
        if 'assessed_value' in data:
            property.assessed_value = Decimal(str(data['assessed_value']))
            
        if 'purchase_price' in data:
            property.purchase_price = Decimal(str(data['purchase_price']))
        
        # Update date fields
        if 'purchase_date' in data and data['purchase_date']:
            property.purchase_date = datetime.fromisoformat(data['purchase_date'])
        
        # Update JSON fields
        if 'features' in data:
            property.features = data['features']
            
        if 'metadata' in data:
            property.property_metadata = data['metadata']
        
        # Update location
        if 'location' in data and data['location']:
            property.location = data['location']
        
        # Save changes
        db.session.commit()
        
        # Return success
        return jsonify({
            'success': True,
            'message': 'Property updated successfully',
            'property_id': str(property.id)
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating property {property_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error updating property: {str(e)}"
        }), 500

@assessment_bp.route('/zoning', methods=['GET'])
@login_required
def get_zoning():
    """
    Get zoning data as GeoJSON
    
    Returns:
        JSON response with zoning GeoJSON
    """
    try:
        # In a real app, this would fetch zoning data from the database
        # or a GIS service. For demo purposes, we'll return sample data.
        
        # Check if we have a zoning file available
        zoning_file = File.query.filter(
            File.filename.like('%zoning%'),
            File.filename.like('%.geojson')
        ).first()
        
        if zoning_file:
            # Load the zoning GeoJSON file
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                    str(zoning_file.id), 
                                    zoning_file.filename)
            
            with open(file_path, 'r') as f:
                zoning_data = json.load(f)
            
            return jsonify({
                'success': True,
                'zoning': zoning_data
            })
        else:
            # Return empty data
            return jsonify({
                'success': True,
                'zoning': {
                    'type': 'FeatureCollection',
                    'features': []
                }
            })
    
    except Exception as e:
        logger.error(f"Error getting zoning data: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting zoning data: {str(e)}"
        }), 500

@assessment_bp.route('/valuation/<property_id>', methods=['GET'])
@login_required
@permission_required('view_properties')
def get_valuation_history(property_id):
    """
    Get valuation history for a property
    
    Args:
        property_id: Property ID (UUID)
    
    Returns:
        JSON response with valuation history
    """
    try:
        # Get property
        property = Property.query.get(property_id)
        
        if not property:
            return jsonify({
                'success': False,
                'message': 'Property not found'
            }), 404
        
        # In a real app, this would fetch valuation history from the database
        # For demo purposes, we'll generate sample data
        
        # Get current year
        current_year = datetime.now().year
        
        # Generate 5 years of history
        history = []
        base_value = float(property.assessed_value) if property.assessed_value else 300000
        
        for i in range(5):
            year = current_year - 4 + i
            
            # Each previous year is a percentage of the current value
            if i < 4:
                value = base_value * (0.75 + (i * 0.1))
            else:
                value = base_value  # Current year value
            
            history.append({
                'year': year,
                'assessed_value': value,
                'land_value': value * 0.3,  # Land value is approximately 30% of total
                'improvement_value': value * 0.7  # Improvement value is approximately 70% of total
            })
        
        # Return JSON response
        return jsonify({
            'success': True,
            'property_id': str(property.id),
            'valuation_history': history
        })
    
    except Exception as e:
        logger.error(f"Error getting valuation history for property {property_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting valuation history: {str(e)}"
        }), 500

@assessment_bp.route('/comparable-properties/<property_id>', methods=['GET'])
@login_required
@permission_required('view_properties')
def get_comparable_properties(property_id):
    """
    Get comparable properties for a property
    
    Args:
        property_id: Property ID (UUID)
    
    Returns:
        JSON response with comparable properties
    """
    try:
        # Get property
        property = Property.query.get(property_id)
        
        if not property:
            return jsonify({
                'success': False,
                'message': 'Property not found'
            }), 404
        
        # Get property type and assessed value
        property_type = property.property_type
        assessed_value = property.assessed_value
        
        if not assessed_value:
            return jsonify({
                'success': False,
                'message': 'Property has no assessed value'
            }), 400
        
        # Find comparable properties
        # - Same property type
        # - Similar assessed value (within 20%)
        # - Not the same property
        min_value = float(assessed_value) * 0.8
        max_value = float(assessed_value) * 1.2
        
        query = Property.query.filter(
            Property.id != property.id,
            Property.property_type == property_type,
            cast(Property.assessed_value, Float) >= min_value,
            cast(Property.assessed_value, Float) <= max_value
        ).limit(5)
        
        comparable_properties = query.all()
        
        # Format result
        result = []
        for comp in comparable_properties:
            # Get coordinates from location GeoJSON
            coordinates = None
            if comp.location and isinstance(comp.location, dict) and 'coordinates' in comp.location:
                coordinates = comp.location['coordinates']
            
            comp_dict = {
                'id': str(comp.id),
                'parcel_id': comp.parcel_id,
                'address': comp.address,
                'property_type': comp.property_type,
                'assessed_value': float(comp.assessed_value) if comp.assessed_value else None,
                'lot_size': comp.lot_size,
                'year_built': comp.year_built
            }
            
            # Add property-type specific fields
            if comp.property_type == 'residential':
                comp_dict.update({
                    'bedrooms': comp.features.get('bedrooms', None) if comp.features else None,
                    'bathrooms': comp.features.get('bathrooms', None) if comp.features else None,
                    'total_area': comp.total_area
                })
            
            # Add coordinates if available
            if coordinates:
                comp_dict.update({
                    'lng': coordinates[0],
                    'lat': coordinates[1]
                })
            
            result.append(comp_dict)
        
        # Return JSON response
        return jsonify({
            'success': True,
            'property_id': str(property.id),
            'comparable_properties': result
        })
    
    except Exception as e:
        logger.error(f"Error getting comparable properties for property {property_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting comparable properties: {str(e)}"
        }), 500

@assessment_bp.route('/statistics', methods=['GET'])
@login_required
def get_statistics():
    """
    Get property assessment statistics
    
    Returns:
        JSON response with statistics
    """
    try:
        # In a real app, this would fetch statistics from the database
        # For demo purposes, we'll return sample data
        
        # Get property type counts
        property_type_counts = db.session.query(
            Property.property_type,
            func.count(Property.id)
        ).group_by(Property.property_type).all()
        
        # Format property type counts
        property_types = {}
        for property_type, count in property_type_counts:
            property_types[property_type] = count
        
        # Get value distribution
        value_distribution = {
            'under_250k': db.session.query(Property).filter(cast(Property.assessed_value, Float) < 250000).count(),
            '250k_to_500k': db.session.query(Property).filter(
                cast(Property.assessed_value, Float) >= 250000,
                cast(Property.assessed_value, Float) < 500000
            ).count(),
            '500k_to_1m': db.session.query(Property).filter(
                cast(Property.assessed_value, Float) >= 500000,
                cast(Property.assessed_value, Float) < 1000000
            ).count(),
            'over_1m': db.session.query(Property).filter(cast(Property.assessed_value, Float) >= 1000000).count()
        }
        
        # Get total assessed value by property type
        value_by_type = db.session.query(
            Property.property_type,
            func.sum(cast(Property.assessed_value, Float))
        ).group_by(Property.property_type).all()
        
        # Format value by type
        value_by_property_type = {}
        for property_type, total_value in value_by_type:
            value_by_property_type[property_type] = total_value
        
        # Return statistics
        return jsonify({
            'success': True,
            'property_count': db.session.query(Property).count(),
            'property_types': property_types,
            'value_distribution': value_distribution,
            'value_by_property_type': value_by_property_type,
            'latest_update': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting statistics: {str(e)}"
        }), 500

def register_blueprint(app):
    """
    Register assessment blueprint with the application
    
    Args:
        app: Flask application
    """
    app.register_blueprint(assessment_bp)
    app.json_encoder = CustomJSONEncoder
    logger.info("Assessment API routes registered")