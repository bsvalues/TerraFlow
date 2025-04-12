"""
Data Quality Routes Module

This module provides Flask routes for accessing the data quality functions.
"""

import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, render_template, jsonify, redirect, url_for

from mcp.data_quality import alert_manager, QualityAlert
from mcp.integrators.data_quality_integrator import data_quality_integrator
from auth import login_required, permission_required

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
data_quality_bp = Blueprint('data_quality', __name__, url_prefix='/data-quality')

@data_quality_bp.route('/', methods=['GET'])
@login_required
def data_quality_dashboard():
    """Render the data quality dashboard page"""
    return render_template(
        'data_quality_dashboard.html',
        title="Data Quality Dashboard",
        description="Monitor and manage data quality across the platform"
    )

@data_quality_bp.route('/alerts', methods=['GET'])
@login_required
def alerts_page():
    """Render the data quality alerts page"""
    alerts = alert_manager.get_all_alerts()
    return render_template(
        'data_quality_alerts.html',
        title="Data Quality Alerts",
        alerts=alerts
    )

@data_quality_bp.route('/checks', methods=['GET'])
@login_required
def checks_page():
    """Render the data quality checks page"""
    return render_template(
        'data_quality_checks.html',
        title="Data Quality Checks"
    )

@data_quality_bp.route('/reports', methods=['GET'])
@login_required
def reports_page():
    """Render the data quality reports page"""
    return render_template(
        'data_quality_reports.html',
        title="Data Quality Reports"
    )

# API routes for data quality

@data_quality_bp.route('/api/alerts', methods=['GET'])
@login_required
@permission_required('data_quality_api_access')
def api_get_alerts():
    """Get all quality alerts"""
    alerts = alert_manager.get_all_alerts()
    return jsonify({
        "success": True,
        "total": len(alerts),
        "alerts": [alert.to_dict() for alert in alerts]
    })

@data_quality_bp.route('/api/alerts/<alert_id>', methods=['GET'])
@login_required
@permission_required('data_quality_api_access')
def api_get_alert(alert_id):
    """Get a specific quality alert"""
    alert = alert_manager.get_alert(alert_id)
    if not alert:
        return jsonify({
            "success": False,
            "error": f"Alert not found: {alert_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "alert": alert.to_dict()
    })

@data_quality_bp.route('/api/alerts', methods=['POST'])
@login_required
@permission_required('data_quality_management')
def api_create_alert():
    """Create a new quality alert"""
    try:
        data = request.json
        
        # Create alert from request data
        alert = QualityAlert(
            name=data.get("name", ""),
            description=data.get("description", ""),
            check_type=data.get("check_type", ""),
            parameters=data.get("parameters", {}),
            threshold=data.get("threshold", 0.95),
            severity=data.get("severity", "medium"),
            notification_channels=data.get("notification_channels", ["log"]),
            enabled=data.get("enabled", True)
        )
        
        # Add the alert
        success = alert_manager.add_alert(alert)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to add alert. Check configuration."
            }), 400
        
        return jsonify({
            "success": True,
            "alert": alert.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating quality alert: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error creating alert: {str(e)}"
        }), 400

@data_quality_bp.route('/api/alerts/<alert_id>', methods=['PUT'])
@login_required
@permission_required('data_quality_management')
def api_update_alert(alert_id):
    """Update an existing quality alert"""
    try:
        data = request.json
        
        # Update the alert
        success = alert_manager.update_alert(alert_id, data)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to update alert. Check configuration or alert ID."
            }), 400
        
        # Get the updated alert
        alert = alert_manager.get_alert(alert_id)
        
        return jsonify({
            "success": True,
            "alert": alert.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating quality alert: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error updating alert: {str(e)}"
        }), 400

@data_quality_bp.route('/api/alerts/<alert_id>', methods=['DELETE'])
@login_required
@permission_required('data_quality_management')
def api_delete_alert(alert_id):
    """Delete a quality alert"""
    success = alert_manager.delete_alert(alert_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": f"Failed to delete alert: {alert_id}"
        }), 400
    
    return jsonify({
        "success": True,
        "message": f"Alert {alert_id} deleted successfully"
    })

@data_quality_bp.route('/api/alerts/<alert_id>/check', methods=['POST'])
@login_required
@permission_required('data_quality_api_access')
def api_check_alert(alert_id):
    """Check a specific quality alert"""
    result = alert_manager.check_alert(alert_id)
    
    if not result.get("success"):
        return jsonify(result), 400
    
    return jsonify(result)

@data_quality_bp.route('/api/alerts/check-all', methods=['POST'])
@login_required
@permission_required('data_quality_api_access')
def api_check_all_alerts():
    """Check all quality alerts"""
    results = alert_manager.check_all_alerts()
    return jsonify(results)

@data_quality_bp.route('/api/check/completeness', methods=['POST'])
@login_required
@permission_required('data_quality_api_access')
def api_check_completeness():
    """Check data completeness"""
    try:
        data = request.json
        
        result = data_quality_integrator.process_quality_request(
            request_type="completeness_check",
            data=data
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in completeness check: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Check failed: {str(e)}"
        }), 400

@data_quality_bp.route('/api/check/format', methods=['POST'])
@login_required
@permission_required('data_quality_api_access')
def api_check_format():
    """Check data format"""
    try:
        data = request.json
        
        result = data_quality_integrator.process_quality_request(
            request_type="format_validation",
            data=data
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in format validation: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Check failed: {str(e)}"
        }), 400

@data_quality_bp.route('/api/check/range', methods=['POST'])
@login_required
@permission_required('data_quality_api_access')
def api_check_range():
    """Check data ranges"""
    try:
        data = request.json
        
        result = data_quality_integrator.process_quality_request(
            request_type="range_validation",
            data=data
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in range validation: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Check failed: {str(e)}"
        }), 400

@data_quality_bp.route('/api/check/valuation', methods=['POST'])
@login_required
@permission_required('data_quality_api_access')
def api_check_valuation():
    """Check valuation data"""
    try:
        data = request.json
        
        result = data_quality_integrator.process_quality_request(
            request_type="valuation_validation",
            data=data
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in valuation validation: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Check failed: {str(e)}"
        }), 400

@data_quality_bp.route('/api/report', methods=['POST'])
@login_required
@permission_required('data_quality_api_access')
def api_get_quality_report():
    """Get a quality report"""
    try:
        data = request.json
        
        result = data_quality_integrator.process_quality_request(
            request_type="data_quality_report",
            data=data
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error generating quality report: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Report generation failed: {str(e)}"
        }), 400