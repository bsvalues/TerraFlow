"""
Spatial API Module

This module provides endpoints for geospatial data access and management.
It handles GIS data querying, transformation, and basic spatial operations.
"""

from flask import Blueprint, request, jsonify, current_app, session, send_file
import logging
import json
import os
import tempfile
from functools import wraps
from typing import Dict, Any, List, Optional

from auth import login_required, is_authenticated
from mcp.core import mcp_instance
from api.gateway import api_login_required, api_rate_limit, log_api_call

# Create blueprint
spatial_api = Blueprint('spatial_api', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('spatial_api')


@spatial_api.route('/layers', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def list_spatial_layers():
    """List available GIS layers"""
    try:
        from app import db
        from models import File
        
        # Query for GIS file types
        gis_files = File.query.filter(
            File.file_type.in_(['geojson', 'shp', 'kml', 'kmz', 'gpkg']),
            File.user_id == session['user']['id']
        ).all()
        
        # Format the response
        layers = []
        for file in gis_files:
            layer = {
                'id': file.id,
                'name': file.original_filename,
                'type': file.file_type,
                'description': file.description,
                'upload_date': file.upload_date.isoformat() if file.upload_date else None
            }
            
            # Add metadata if available
            if file.file_metadata:
                if isinstance(file.file_metadata, str):
                    try:
                        metadata = json.loads(file.file_metadata)
                    except json.JSONDecodeError:
                        metadata = {}
                else:
                    metadata = file.file_metadata
                
                # Add selected metadata fields
                layer['feature_count'] = metadata.get('feature_count')
                layer['geometry_type'] = metadata.get('geometry_type')
                layer['crs'] = metadata.get('crs')
                layer['bounds'] = metadata.get('bounds')
            
            layers.append(layer)
        
        return jsonify({
            "status": "success",
            "layers": layers
        })
    except Exception as e:
        logger.error(f"Error listing spatial layers: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@spatial_api.route('/layers/<int:layer_id>', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def get_layer_details(layer_id):
    """Get detailed information about a specific GIS layer"""
    try:
        from app import db
        from models import File
        
        # Get the file record
        file_record = File.query.get_or_404(layer_id)
        
        # Check if user has access to this file
        if file_record.user_id != session['user']['id']:
            return jsonify({
                "status": "error",
                "message": "Access denied"
            }), 403
        
        # Format metadata
        if file_record.file_metadata:
            if isinstance(file_record.file_metadata, str):
                try:
                    metadata = json.loads(file_record.file_metadata)
                except json.JSONDecodeError:
                    metadata = {}
            else:
                metadata = file_record.file_metadata
        else:
            metadata = {}
        
        return jsonify({
            "status": "success",
            "layer": {
                "id": file_record.id,
                "name": file_record.original_filename,
                "type": file_record.file_type,
                "description": file_record.description,
                "upload_date": file_record.upload_date.isoformat() if file_record.upload_date else None,
                "metadata": metadata
            }
        })
    except Exception as e:
        logger.error(f"Error getting layer details: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@spatial_api.route('/layers/<int:layer_id>/data', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def get_layer_data(layer_id):
    """Get GIS data from a specific layer"""
    try:
        from app import db, app
        from models import File
        import os
        
        # Get the file record
        file_record = File.query.get_or_404(layer_id)
        
        # Check if user has access to this file
        if file_record.user_id != session['user']['id']:
            return jsonify({
                "status": "error",
                "message": "Access denied"
            }), 403
        
        # Get the requested format (default to GeoJSON)
        output_format = request.args.get('format', 'geojson').lower()
        
        # File path
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                                 str(layer_id), 
                                 file_record.filename)
        
        # Process based on the source file type and requested output format
        if file_record.file_type.lower() == 'geojson' and output_format == 'geojson':
            # Direct read for GeoJSON
            with open(file_path, 'r') as f:
                geojson_data = json.load(f)
            
            return jsonify({
                "status": "success",
                "data": geojson_data,
                "metadata": file_record.file_metadata
            })
        else:
            # Need conversion - use a spatial agent
            agent = mcp_instance.get_agent('spatial_analysis')
            if not agent:
                # Check if the spatial agent is available - if not, try to handle conversion ourselves
                if output_format == 'geojson' and file_record.file_type.lower() in ['geojson', 'shp']:
                    try:
                        import geopandas as gpd
                        
                        # Read the file with GeoPandas
                        gdf = gpd.read_file(file_path)
                        
                        # Convert to GeoJSON
                        geojson_data = json.loads(gdf.to_json())
                        
                        return jsonify({
                            "status": "success",
                            "data": geojson_data
                        })
                    except ImportError:
                        return jsonify({
                            "status": "error",
                            "message": "Spatial analysis agent not available and GeoPandas not installed"
                        }), 503
                    except Exception as e:
                        return jsonify({
                            "status": "error",
                            "message": f"Conversion error: {str(e)}"
                        }), 500
                else:
                    return jsonify({
                        "status": "error",
                        "message": "Spatial analysis agent not available"
                    }), 503
            
            # Use the spatial agent for conversion
            task_data = {
                'task_type': 'convert_format',
                'file_id': layer_id,
                'output_format': output_format
            }
            
            result = agent.process_task(task_data)
            
            # Check if the result contains a file path or direct data
            if result.get('status') != 'success':
                return jsonify({
                    "status": "error",
                    "message": result.get('message', 'Conversion failed')
                }), 500
            
            if 'file_path' in result:
                # Send the file
                return send_file(
                    result['file_path'],
                    as_attachment=True,
                    download_name=f"{file_record.original_filename}.{output_format}"
                )
            else:
                # Return the data directly
                return jsonify({
                    "status": "success",
                    "data": result.get('data', {}),
                    "metadata": result.get('metadata', {})
                })
    except Exception as e:
        logger.error(f"Error getting layer data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@spatial_api.route('/analyze', methods=['POST'])
@api_login_required
@api_rate_limit
@log_api_call
def analyze_spatial_data():
    """Perform spatial analysis on GIS data"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Missing request body"
            }), 400
        
        # Required parameters
        layer_id = data.get('layer_id')
        analysis_type = data.get('analysis_type')
        
        if not layer_id:
            return jsonify({
                "status": "error",
                "message": "Missing layer_id parameter"
            }), 400
        
        if not analysis_type:
            return jsonify({
                "status": "error",
                "message": "Missing analysis_type parameter"
            }), 400
        
        # Check if the layer exists and user has access
        from app import db
        from models import File
        
        file_record = File.query.get(layer_id)
        if not file_record:
            return jsonify({
                "status": "error",
                "message": "Layer not found"
            }), 404
        
        if file_record.user_id != session['user']['id']:
            return jsonify({
                "status": "error",
                "message": "Access denied"
            }), 403
        
        # Get the spatial analysis agent
        agent = mcp_instance.get_agent('spatial_analysis')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Spatial analysis agent not available"
            }), 503
        
        # Submit the analysis task
        task_data = {
            'task_type': 'analyze',
            'file_id': layer_id,
            'analysis_type': analysis_type,
            'parameters': data.get('parameters', {})
        }
        
        result = agent.process_task(task_data)
        
        return jsonify({
            "status": "success",
            "result": result
        })
    except Exception as e:
        logger.error(f"Error in spatial analysis: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500