"""
MCP API Module

This module provides API endpoints for interacting with the MCP system.
It allows users to submit tasks to agents, check task status, and get results.
"""

from flask import Blueprint, request, jsonify, current_app, session
import logging
import time
from functools import wraps
from typing import Dict, Any, List

from auth import login_required, is_authenticated
from mcp.core import mcp_instance

# Create blueprint
mcp_api = Blueprint('mcp_api', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mcp_api')

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

@mcp_api.route('/agents', methods=['GET'])
@api_login_required
def list_agents():
    """Get a list of available agents and their capabilities"""
    agent_info = mcp_instance.get_agent_info()
    
    return jsonify({
        "status": "success",
        "agents": agent_info
    })

@mcp_api.route('/agents/<agent_id>', methods=['GET'])
@api_login_required
def get_agent_details(agent_id):
    """Get detailed information about a specific agent"""
    agent_info = mcp_instance.get_agent_info(agent_id)
    
    if not agent_info:
        return jsonify({
            "status": "error",
            "message": f"Agent not found: {agent_id}"
        }), 404
    
    return jsonify({
        "status": "success",
        "agent": agent_info
    })

@mcp_api.route('/tasks', methods=['POST'])
@api_login_required
def submit_task():
    """Submit a task to an agent"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "Missing request body"
        }), 400
    
    # Required fields
    agent_id = data.get('agent_id')
    task_data = data.get('task_data')
    
    if not agent_id or not task_data:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: agent_id, task_data"
        }), 400
    
    # Add user info to task data
    if is_authenticated():
        user_info = session.get('user', {})
        task_data['user_id'] = user_info.get('id')
        task_data['username'] = user_info.get('username')
    
    # Submit the task
    task_id = mcp_instance.submit_task(agent_id, task_data)
    
    if not task_id:
        return jsonify({
            "status": "error",
            "message": f"Failed to submit task to agent: {agent_id}"
        }), 500
    
    return jsonify({
        "status": "success",
        "task_id": task_id,
        "message": "Task submitted successfully"
    })

@mcp_api.route('/tasks/<task_id>', methods=['GET'])
@api_login_required
def get_task_status(task_id):
    """Get the status of a specific task"""
    task_status = mcp_instance.get_task_status(task_id)
    
    if not task_status:
        return jsonify({
            "status": "error",
            "message": f"Task not found: {task_id}"
        }), 404
    
    return jsonify({
        "status": "success",
        "task": task_status
    })

@mcp_api.route('/tasks/<task_id>/result', methods=['GET'])
@api_login_required
def get_task_result(task_id):
    """Get the result of a completed task"""
    task_status = mcp_instance.get_task_status(task_id)
    
    if not task_status:
        return jsonify({
            "status": "error",
            "message": f"Task not found: {task_id}"
        }), 404
    
    if task_status['status'] != 'completed':
        return jsonify({
            "status": "error",
            "message": f"Task not completed: {task_id}",
            "task_status": task_status['status']
        }), 400
    
    task_result = mcp_instance.get_task_result(task_id)
    
    return jsonify({
        "status": "success",
        "task_id": task_id,
        "result": task_result
    })

@mcp_api.route('/system/status', methods=['GET'])
@api_login_required
def get_system_status():
    """Get overall MCP system status"""
    # Get agent statuses
    agent_info = mcp_instance.get_agent_info()
    
    # Count tasks by status
    tasks = mcp_instance.tasks
    task_counts = {
        "total": len(tasks),
        "pending": sum(1 for t in tasks.values() if t['status'] == 'pending'),
        "processing": sum(1 for t in tasks.values() if t['status'] == 'processing'),
        "completed": sum(1 for t in tasks.values() if t['status'] == 'completed'),
        "failed": sum(1 for t in tasks.values() if t['status'] == 'failed')
    }
    
    return jsonify({
        "status": "success",
        "system_status": {
            "running": mcp_instance.running,
            "agent_count": len(agent_info),
            "tasks": task_counts
        },
        "agents": agent_info
    })

@mcp_api.route('/system/report', methods=['GET'])
@api_login_required
def get_system_report():
    """Get a human-readable system report"""
    report = mcp_instance.agent_status_report()
    
    return jsonify({
        "status": "success",
        "report": report
    })