"""
API Gateway Module

This module provides the central API gateway functionality for the Benton County Data Hub.
It maps incoming API requests to the appropriate internal services, implements
authentication, rate limiting, and logging for all API access.
"""

from flask import Blueprint, request, jsonify, current_app, session
import logging
import time
import json
from functools import wraps
from typing import Dict, Any, List, Optional
import uuid

from auth import login_required, is_authenticated
from mcp.core import mcp_instance

# Create blueprint
api_gateway = Blueprint('api_gateway', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('api_gateway')

# In-memory rate limit storage
# In production, this should be replaced with a distributed cache like Redis
rate_limits = {}
rate_limit_window = 60  # seconds
rate_limit_max_requests = 30  # requests per window


def api_login_required(f):
    """Decorator to require login for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def api_rate_limit(f):
    """Decorator to implement rate limiting for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if is_authenticated():
            # Use user ID for rate limiting if authenticated
            key = f"user_{session.get('user', {}).get('id', 'anonymous')}:{request.path}"
        else:
            # Use IP address for rate limiting if not authenticated
            key = f"ip_{request.remote_addr}:{request.path}"
        
        # Check if rate limit exceeded
        now = time.time()
        window_start = int(now - rate_limit_window)
        
        # Clean up old entries
        for k in list(rate_limits.keys()):
            if all(ts < window_start for ts in rate_limits[k]):
                del rate_limits[k]
        
        # Initialize if needed
        if key not in rate_limits:
            rate_limits[key] = []
        
        # Filter out old timestamps
        rate_limits[key] = [ts for ts in rate_limits[key] if ts >= window_start]
        
        # Check rate limit
        if len(rate_limits[key]) >= rate_limit_max_requests:
            return jsonify({
                "status": "error",
                "message": "Rate limit exceeded",
                "retry_after": int(min(rate_limits[key]) + rate_limit_window - now)
            }), 429
        
        # Add current timestamp
        rate_limits[key].append(now)
        
        # Add rate limit headers
        response = f(*args, **kwargs)
        if isinstance(response, tuple):
            response_obj, status_code = response
            headers = {}
        else:
            response_obj = response
            status_code = 200
            headers = {}
        
        # Add rate limit headers
        headers['X-RateLimit-Limit'] = str(rate_limit_max_requests)
        headers['X-RateLimit-Remaining'] = str(rate_limit_max_requests - len(rate_limits[key]))
        headers['X-RateLimit-Reset'] = str(int(now) + rate_limit_window)
        
        # Convert response back to tuple with headers
        return response_obj, status_code, headers
    
    return decorated_function


def log_api_call(f):
    """Decorator to log API calls"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Log the request
        logger.info(f"API Request [{request_id}]: {request.method} {request.path} - User: {session.get('user', {}).get('username', 'anonymous')} - IP: {request.remote_addr}")
        
        # Time the request
        start_time = time.time()
        
        # Execute the actual function
        response = f(*args, **kwargs)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log the response
        if isinstance(response, tuple):
            status_code = response[1] if len(response) > 1 else 200
        else:
            status_code = 200
        
        logger.info(f"API Response [{request_id}]: Status {status_code} - Duration: {duration:.4f}s")
        
        return response
    
    return decorated_function


# API endpoints
@api_gateway.route('/', methods=['GET'])
def api_index():
    """API root endpoint with documentation links"""
    return jsonify({
        "name": "Benton County Data Hub API",
        "version": "1.0",
        "documentation": "/api/docs",
        "endpoints": {
            "data": "/api/data",
            "gis": "/api/gis",
            "search": "/api/search"
        }
    })


@api_gateway.route('/docs', methods=['GET'])
def api_docs():
    """API documentation endpoint"""
    # This would be expanded with comprehensive documentation
    # Could use a tool like Swagger/OpenAPI for this
    return jsonify({
        "name": "Benton County Data Hub API Documentation",
        "version": "1.0",
        "endpoints": {
            "data": {
                "description": "Access to SQL Server and other database sources",
                "endpoints": [
                    {"path": "/api/data/sql/<database>/<table>", "method": "GET", "description": "Query SQL Server data"},
                    {"path": "/api/data/sources", "method": "GET", "description": "List available data sources"}
                ]
            },
            "gis": {
                "description": "Access to geospatial data",
                "endpoints": [
                    {"path": "/api/gis/features/<dataset>", "method": "GET", "description": "Get GeoJSON features"},
                    {"path": "/api/gis/datasets", "method": "GET", "description": "List available GIS datasets"}
                ]
            },
            "search": {
                "description": "Natural language search across data sources",
                "endpoints": [
                    {"path": "/api/search", "method": "POST", "description": "Perform a natural language search"}
                ]
            }
        }
    })


@api_gateway.route('/data/sources', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def list_data_sources():
    """List available data sources"""
    try:
        # Get a list of registered data sources via the power query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        task_data = {
            'task_type': 'list_sources'
        }
        
        result = agent.process_task(task_data)
        
        return jsonify({
            "status": "success",
            "data_sources": result.get('sources', [])
        })
    except Exception as e:
        logger.error(f"Error listing data sources: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@api_gateway.route('/data/sql/<database>/<table>', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def sql_data_endpoint(database, table):
    """Endpoint for accessing SQL Server data"""
    try:
        # Validate parameters (basic sanitization)
        # This would be expanded with more robust validation
        if not database or not table:
            return jsonify({
                "status": "error",
                "message": "Missing database or table parameter"
            }), 400
        
        # Process filter parameters
        filters = {}
        limit = request.args.get('limit', 1000)
        offset = request.args.get('offset', 0)
        
        # Extract filter conditions from query parameters
        for key, value in request.args.items():
            if key not in ['limit', 'offset']:
                filters[key] = value
        
        # Submit task to Power Query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        task_data = {
            'task_type': 'query_data',
            'source_type': 'sql',
            'database': database,
            'table': table,
            'filters': filters,
            'limit': limit,
            'offset': offset
        }
        
        result = agent.process_task(task_data)
        
        return jsonify({
            "status": "success",
            "data": result.get('data', []),
            "metadata": {
                "total_rows": result.get('total_rows', 0),
                "limit": limit,
                "offset": offset,
                "filters": filters
            }
        })
    except Exception as e:
        logger.error(f"API error in SQL data endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@api_gateway.route('/gis/datasets', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def list_gis_datasets():
    """List available GIS datasets"""
    try:
        # Get GIS files from the database
        from app import db
        from models import File
        from flask import session
        
        # Query for GeoJSON files
        gis_files = File.query.filter(
            File.file_type.in_(['geojson', 'shp', 'kml', 'kmz', 'gpkg']),
            File.user_id == session['user']['id']
        ).all()
        
        # Format the response
        datasets = [{
            'id': file.id,
            'name': file.original_filename,
            'type': file.file_type,
            'upload_date': file.upload_date.isoformat() if file.upload_date else None,
            'description': file.description,
            'metadata': file.file_metadata
        } for file in gis_files]
        
        return jsonify({
            "status": "success",
            "datasets": datasets
        })
    except Exception as e:
        logger.error(f"Error listing GIS datasets: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@api_gateway.route('/gis/features/<int:dataset_id>', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def get_gis_features(dataset_id):
    """Get GeoJSON features from a dataset"""
    try:
        from app import db, app
        from models import File
        import os
        import json
        
        # Get the file record
        file_record = File.query.get_or_404(dataset_id)
        
        # Check if user has access to this file
        if file_record.user_id != session['user']['id']:
            return jsonify({
                "status": "error",
                "message": "Access denied"
            }), 403
        
        # Check file type and convert if needed
        if file_record.file_type == 'geojson':
            # Direct read for GeoJSON
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                                     str(dataset_id), 
                                     file_record.filename)
            
            with open(file_path, 'r') as f:
                geojson_data = json.load(f)
            
            return jsonify({
                "status": "success",
                "data": geojson_data,
                "metadata": file_record.file_metadata
            })
        else:
            # For other types, request conversion from a GIS agent
            agent = mcp_instance.get_agent('spatial_analysis')
            if not agent:
                return jsonify({
                    "status": "error",
                    "message": "GIS processing agent not available"
                }), 503
            
            task_data = {
                'task_type': 'convert_to_geojson',
                'file_id': dataset_id
            }
            
            result = agent.process_task(task_data)
            
            if result.get('status') != 'success':
                return jsonify({
                    "status": "error",
                    "message": result.get('message', 'Conversion failed')
                }), 500
            
            return jsonify({
                "status": "success",
                "data": result.get('data', {}),
                "metadata": result.get('metadata', {})
            })
    except Exception as e:
        logger.error(f"Error accessing GIS features: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@api_gateway.route('/search', methods=['POST'])
@api_login_required
@api_rate_limit
@log_api_call
def api_search():
    """Perform a natural language search across data sources"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Missing request body"
            }), 400
        
        query = data.get('query')
        if not query:
            return jsonify({
                "status": "error",
                "message": "Missing query parameter"
            }), 400
        
        # Process the search using RAG
        from rag import process_query
        
        # Log the query
        from app import db
        from models import QueryLog
        import datetime
        
        start_time = time.time()
        query_log = QueryLog(
            user_id=session['user']['id'],
            query=query,
            timestamp=datetime.datetime.now()
        )
        db.session.add(query_log)
        db.session.commit()
        
        # Run the search
        results = process_query(query, user_id=session['user']['id'])
        
        # Update the log with response
        end_time = time.time()
        query_log.response = json.dumps(results)
        query_log.processing_time = end_time - start_time
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "query": query,
            "results": results
        })
    except Exception as e:
        logger.error(f"Search API error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Search error: {str(e)}"
        }), 500