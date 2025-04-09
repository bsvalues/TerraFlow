"""
Data Query API Module

This module provides endpoints for data querying and transformation services.
It interfaces with the Power Query functionality to access various data sources.
"""

from flask import Blueprint, request, jsonify, current_app, session, send_file
import logging
import time
import json
import os
import tempfile
from functools import wraps
from typing import Dict, Any, List, Optional
import uuid

from auth import login_required, is_authenticated
from mcp.core import mcp_instance
from api.gateway import api_login_required, api_rate_limit, log_api_call

# Create blueprint
data_query_api = Blueprint('data_query_api', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('data_query_api')


@data_query_api.route('/sources', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def list_data_sources():
    """List available data sources"""
    try:
        # Get the Power Query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        # Get the data sources
        task_data = {
            'task_type': 'list_data_sources'
        }
        
        result = agent.process_task(task_data)
        
        return jsonify({
            "status": "success",
            "data_sources": result.get('data_sources', [])
        })
    except Exception as e:
        logger.error(f"Error listing data sources: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@data_query_api.route('/sources/<source_id>', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def get_data_source_metadata(source_id):
    """Get metadata for a specific data source"""
    try:
        # Get the Power Query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        # Get the data source metadata
        task_data = {
            'task_type': 'get_source_metadata',
            'source_id': source_id
        }
        
        result = agent.process_task(task_data)
        
        if result.get('status') == 'error':
            return jsonify({
                "status": "error",
                "message": result.get('message', f"Source {source_id} not found")
            }), 404
        
        return jsonify({
            "status": "success",
            "metadata": result.get('metadata', {})
        })
    except Exception as e:
        logger.error(f"Error getting data source metadata: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@data_query_api.route('/sources/<source_id>/tables', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def list_source_tables(source_id):
    """List tables available in a data source"""
    try:
        # Get the Power Query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        # Get the tables for this source
        task_data = {
            'task_type': 'list_tables',
            'source_id': source_id
        }
        
        result = agent.process_task(task_data)
        
        if result.get('status') == 'error':
            return jsonify({
                "status": "error",
                "message": result.get('message', f"Source {source_id} not found or error listing tables")
            }), result.get('code', 500)
        
        return jsonify({
            "status": "success",
            "tables": result.get('tables', [])
        })
    except Exception as e:
        logger.error(f"Error listing source tables: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@data_query_api.route('/sources/<source_id>/tables/<table_name>', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def get_table_schema(source_id, table_name):
    """Get schema information for a specific table"""
    try:
        # Get the Power Query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        # Get the table schema
        task_data = {
            'task_type': 'get_table_schema',
            'source_id': source_id,
            'table_name': table_name
        }
        
        result = agent.process_task(task_data)
        
        if result.get('status') == 'error':
            return jsonify({
                "status": "error",
                "message": result.get('message', f"Table {table_name} not found in source {source_id}")
            }), result.get('code', 404)
        
        return jsonify({
            "status": "success",
            "schema": result.get('schema', [])
        })
    except Exception as e:
        logger.error(f"Error getting table schema: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@data_query_api.route('/sources/<source_id>/tables/<table_name>/data', methods=['GET'])
@api_login_required
@api_rate_limit
@log_api_call
def query_table_data(source_id, table_name):
    """Query data from a specific table"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Extract filters from query parameters
        filters = {}
        for key, value in request.args.items():
            if key not in ['limit', 'offset']:
                filters[key] = value
        
        # Get the Power Query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        # Query the table
        task_data = {
            'task_type': 'query_table',
            'source_id': source_id,
            'table_name': table_name,
            'limit': limit,
            'offset': offset,
            'filters': filters
        }
        
        result = agent.process_task(task_data)
        
        if result.get('status') == 'error':
            return jsonify({
                "status": "error",
                "message": result.get('message', f"Error querying table {table_name}")
            }), result.get('code', 500)
        
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
        logger.error(f"Error querying table data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@data_query_api.route('/query', methods=['POST'])
@api_login_required
@api_rate_limit
@log_api_call
def execute_custom_query():
    """Execute a custom SQL or Power Query"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Missing request body"
            }), 400
        
        # Required parameters
        source_id = data.get('source_id')
        query_type = data.get('query_type', 'sql')
        query = data.get('query')
        
        if not source_id:
            return jsonify({
                "status": "error",
                "message": "Missing source_id parameter"
            }), 400
        
        if not query:
            return jsonify({
                "status": "error",
                "message": "Missing query parameter"
            }), 400
        
        # Get the Power Query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        # Execute the query
        task_data = {
            'task_type': 'execute_query',
            'source_id': source_id,
            'query_type': query_type,
            'query': query,
            'parameters': data.get('parameters', {})
        }
        
        result = agent.process_task(task_data)
        
        if result.get('status') == 'error':
            return jsonify({
                "status": "error",
                "message": result.get('message', "Error executing query")
            }), result.get('code', 500)
        
        return jsonify({
            "status": "success",
            "data": result.get('data', []),
            "metadata": result.get('metadata', {})
        })
    except Exception as e:
        logger.error(f"Error executing custom query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@data_query_api.route('/transform', methods=['POST'])
@api_login_required
@api_rate_limit
@log_api_call
def transform_data():
    """Apply transformations to a dataset"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Missing request body"
            }), 400
        
        # Required parameters
        source_data = data.get('source_data')
        transformations = data.get('transformations')
        
        if not source_data:
            return jsonify({
                "status": "error",
                "message": "Missing source_data parameter"
            }), 400
        
        if not transformations:
            return jsonify({
                "status": "error",
                "message": "Missing transformations parameter"
            }), 400
        
        # Get the Power Query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        # Apply transformations
        task_data = {
            'task_type': 'transform_data',
            'source_data': source_data,
            'transformations': transformations
        }
        
        result = agent.process_task(task_data)
        
        if result.get('status') == 'error':
            return jsonify({
                "status": "error",
                "message": result.get('message', "Error transforming data")
            }), result.get('code', 500)
        
        return jsonify({
            "status": "success",
            "data": result.get('data', []),
            "metadata": result.get('metadata', {})
        })
    except Exception as e:
        logger.error(f"Error transforming data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500


@data_query_api.route('/export', methods=['POST'])
@api_login_required
@api_rate_limit
@log_api_call
def export_data():
    """Export data to a file format"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Missing request body"
            }), 400
        
        # Required parameters
        export_data = data.get('data')
        export_format = data.get('format', 'csv')
        
        if not export_data:
            return jsonify({
                "status": "error",
                "message": "Missing data parameter"
            }), 400
        
        # Get the Power Query agent
        agent = mcp_instance.get_agent('power_query')
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Power Query agent not available"
            }), 503
        
        # Export the data
        task_data = {
            'task_type': 'export_data',
            'data': export_data,
            'format': export_format,
            'options': data.get('options', {})
        }
        
        result = agent.process_task(task_data)
        
        if result.get('status') == 'error':
            return jsonify({
                "status": "error",
                "message": result.get('message', "Error exporting data")
            }), result.get('code', 500)
        
        # Check if the response includes a file path
        if 'file_path' in result:
            # Create unique filename
            filename = f"export_{uuid.uuid4().hex}.{export_format}"
            
            # Return the file
            return send_file(
                result['file_path'],
                as_attachment=True,
                download_name=filename
            )
        else:
            # Return the data directly
            return jsonify({
                "status": "success",
                "data": result.get('data', {}),
                "format": export_format
            })
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500