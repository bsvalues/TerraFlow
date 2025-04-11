"""
Data Quality Routes

This module defines the routes for the Data Quality Agent dashboard and API endpoints.
"""

import logging
import json
import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from sqlalchemy import inspect, text, func, and_, desc
import pandas as pd
import io
import numpy as np
from datetime import datetime, timedelta

from app import db
from auth import login_required, permission_required
from mcp import mcp
from sync_service.models.data_quality import (
    DataQualityRule, DataQualityIssue, DataQualityReport, 
    AnomalyDetectionConfig, DataAnomaly
)

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
data_quality_bp = Blueprint('data_quality', __name__, url_prefix='/data-quality')

@data_quality_bp.route('/')
@login_required
def dashboard():
    """Data Quality dashboard page"""
    try:
        # Get dashboard data
        overall_score = 0
        latest_report = DataQualityReport.query.order_by(DataQualityReport.created_at.desc()).first()
        if latest_report:
            overall_score = latest_report.overall_score

        # Get open issues count
        open_issues_count = DataQualityIssue.query.filter_by(status='open').count()
        
        # Get anomalies count
        anomalies_count = DataAnomaly.query.filter_by(status='open').count()
        
        # Get active rules count
        active_rules_count = DataQualityRule.query.filter_by(is_active=True).count()
        
        # Get recent issues
        issues = DataQualityIssue.query.order_by(DataQualityIssue.detected_at.desc()).limit(50).all()
        
        # Get recent anomalies
        anomaly_list = DataAnomaly.query.order_by(DataAnomaly.detected_at.desc()).limit(50).all()
        
        # Get all rules
        rules = DataQualityRule.query.all()
        
        # Get recent reports
        reports = DataQualityReport.query.order_by(DataQualityReport.created_at.desc()).limit(10).all()
        
        # Get database tables for rule configuration
        inspector = inspect(db.engine)
        database_tables = inspector.get_table_names()
        
        return render_template(
            'data_quality/dashboard.html',
            overall_score=overall_score,
            open_issues=open_issues_count,
            anomalies=anomalies_count,
            active_rules=active_rules_count,
            issues=issues,
            anomaly_list=anomaly_list,
            rules=rules,
            reports=reports,
            database_tables=database_tables
        )
    except Exception as e:
        logger.error(f"Error loading data quality dashboard: {str(e)}")
        return render_template('error.html', message=f"Error loading data quality dashboard: {str(e)}")

@data_quality_bp.route('/rule', methods=['POST'])
@login_required
@permission_required('data_quality.edit')
def create_rule():
    """Create a new data quality rule"""
    try:
        data = request.json
        
        # Create rule
        rule = DataQualityRule(
            table_name=data['table_name'],
            field_name=data['field_name'],
            rule_type=data['rule_type'],
            rule_config=data['rule_config'],
            description=data.get('description', ''),
            severity=data.get('severity', 'warning'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(rule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Rule created successfully',
            'rule_id': rule.id
        })
    except Exception as e:
        logger.error(f"Error creating data quality rule: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error creating rule: {str(e)}"
        }), 400

@data_quality_bp.route('/rule/<int:rule_id>', methods=['GET'])
@login_required
def get_rule(rule_id):
    """Get a specific data quality rule"""
    try:
        rule = DataQualityRule.query.get(rule_id)
        
        if not rule:
            return jsonify({
                'success': False,
                'message': f"Rule with ID {rule_id} not found"
            }), 404
        
        return jsonify({
            'success': True,
            'rule': {
                'id': rule.id,
                'table_name': rule.table_name,
                'field_name': rule.field_name,
                'rule_type': rule.rule_type,
                'rule_config': rule.config,
                'description': rule.description,
                'severity': rule.severity,
                'is_active': rule.is_active
            }
        })
    except Exception as e:
        logger.error(f"Error getting data quality rule: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting rule: {str(e)}"
        }), 400

@data_quality_bp.route('/rule/<int:rule_id>', methods=['PUT'])
@login_required
@permission_required('data_quality.edit')
def update_rule(rule_id):
    """Update a data quality rule"""
    try:
        rule = DataQualityRule.query.get(rule_id)
        
        if not rule:
            return jsonify({
                'success': False,
                'message': f"Rule with ID {rule_id} not found"
            }), 404
        
        data = request.json
        
        # Update rule
        rule.table_name = data['table_name']
        rule.field_name = data['field_name']
        rule.rule_type = data['rule_type']
        rule.rule_config = data['rule_config']
        rule.description = data.get('description', '')
        rule.severity = data.get('severity', 'warning')
        rule.is_active = data.get('is_active', True)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Rule updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating data quality rule: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error updating rule: {str(e)}"
        }), 400

@data_quality_bp.route('/rule/<int:rule_id>', methods=['DELETE'])
@login_required
@permission_required('data_quality.edit')
def delete_rule(rule_id):
    """Delete a data quality rule"""
    try:
        rule = DataQualityRule.query.get(rule_id)
        
        if not rule:
            return jsonify({
                'success': False,
                'message': f"Rule with ID {rule_id} not found"
            }), 404
        
        db.session.delete(rule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Rule deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting data quality rule: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error deleting rule: {str(e)}"
        }), 400

@data_quality_bp.route('/rule/<int:rule_id>/status', methods=['PUT'])
@login_required
@permission_required('data_quality.edit')
def update_rule_status(rule_id):
    """Update the active status of a data quality rule"""
    try:
        rule = DataQualityRule.query.get(rule_id)
        
        if not rule:
            return jsonify({
                'success': False,
                'message': f"Rule with ID {rule_id} not found"
            }), 404
        
        data = request.json
        rule.is_active = data.get('is_active', True)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Rule status updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating rule status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error updating rule status: {str(e)}"
        }), 400

@data_quality_bp.route('/issue/<int:issue_id>', methods=['GET'])
@login_required
def get_issue(issue_id):
    """Get a specific data quality issue"""
    try:
        issue = DataQualityIssue.query.get(issue_id)
        
        if not issue:
            return jsonify({
                'success': False,
                'message': f"Issue with ID {issue_id} not found"
            }), 404
        
        issue_data = {
            'id': issue.id,
            'table_name': issue.table_name,
            'field_name': issue.field_name,
            'record_id': issue.record_id,
            'issue_type': issue.issue_type,
            'issue_value': issue.issue_value,
            'issue_details': issue.issue_details,
            'severity': issue.severity,
            'status': issue.status,
            'detected_at': issue.detected_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add rule info if available
        if issue.rule:
            issue_data['rule'] = {
                'id': issue.rule.id,
                'rule_type': issue.rule.rule_type,
                'description': issue.rule.description
            }
        
        return jsonify({
            'success': True,
            'issue': issue_data
        })
    except Exception as e:
        logger.error(f"Error getting data quality issue: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting issue: {str(e)}"
        }), 400

@data_quality_bp.route('/issue/<int:issue_id>/resolve', methods=['PUT'])
@login_required
@permission_required('data_quality.edit')
def resolve_issue(issue_id):
    """Mark a data quality issue as resolved"""
    try:
        issue = DataQualityIssue.query.get(issue_id)
        
        if not issue:
            return jsonify({
                'success': False,
                'message': f"Issue with ID {issue_id} not found"
            }), 404
        
        # Update issue status
        issue.status = 'resolved'
        issue.resolved_at = datetime.datetime.utcnow()
        issue.resolved_by = request.user.id if hasattr(request, 'user') else None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Issue marked as resolved'
        })
    except Exception as e:
        logger.error(f"Error resolving data quality issue: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error resolving issue: {str(e)}"
        }), 400

@data_quality_bp.route('/report', methods=['POST'])
@login_required
@permission_required('data_quality.edit')
def generate_report():
    """Generate a new data quality report"""
    try:
        data = request.json
        report_name = data.get('report_name', f"Data Quality Report {datetime.datetime.now().strftime('%Y-%m-%d')}")
        tables = data.get('tables', [])
        
        if not tables:
            return jsonify({
                'success': False,
                'message': 'No tables specified for report'
            }), 400
        
        # Execute task with Data Quality Agent
        agent = mcp.get_agent('data_quality')
        if not agent:
            return jsonify({
                'success': False,
                'message': 'Data Quality Agent not available'
            }), 500
        
        # Run data quality report
        result = agent.run_data_quality_report(tables)
        
        if not result or not isinstance(result, dict):
            return jsonify({
                'success': False,
                'message': 'Error generating report: No result returned from agent'
            }), 500
        
        # Save report to database
        report = DataQualityReport(
            report_name=report_name,
            tables_checked=tables,
            overall_score=result.get('overall_quality_score', 0),
            report_data=result,
            critical_issues=len(result.get('critical_issues', [])),
            high_issues=0,  # Calculate from result if available
            medium_issues=0,  # Calculate from result if available
            low_issues=0,  # Calculate from result if available
            created_by=request.user.id if hasattr(request, 'user') else None
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Report generated successfully',
            'report_id': report.id
        })
    except Exception as e:
        logger.error(f"Error generating data quality report: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error generating report: {str(e)}"
        }), 400

@data_quality_bp.route('/report/<int:report_id>', methods=['GET'])
@login_required
def get_report(report_id):
    """Get a specific data quality report"""
    try:
        report = DataQualityReport.query.get(report_id)
        
        if not report:
            return jsonify({
                'success': False,
                'message': f"Report with ID {report_id} not found"
            }), 404
        
        return jsonify({
            'success': True,
            'report': {
                'id': report.id,
                'report_name': report.report_name,
                'tables_checked': report.tables_checked,
                'overall_score': report.overall_score,
                'critical_issues': report.critical_issues,
                'high_issues': report.high_issues,
                'medium_issues': report.medium_issues,
                'low_issues': report.low_issues,
                'report_data': report.report_data,
                'created_at': report.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        logger.error(f"Error getting data quality report: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting report: {str(e)}"
        }), 400

@data_quality_bp.route('/report/<int:report_id>/download', methods=['GET'])
@login_required
def download_report(report_id):
    """Download a data quality report as Excel file"""
    try:
        report = DataQualityReport.query.get(report_id)
        
        if not report:
            return jsonify({
                'success': False,
                'message': f"Report with ID {report_id} not found"
            }), 404
        
        # Create Excel file
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        
        # Summary sheet
        summary_data = {
            'Report Name': [report.report_name],
            'Generated At': [report.created_at.strftime('%Y-%m-%d %H:%M:%S')],
            'Overall Score': [f"{report.overall_score:.1f}%"],
            'Critical Issues': [report.critical_issues],
            'High Issues': [report.high_issues],
            'Medium Issues': [report.medium_issues],
            'Low Issues': [report.low_issues],
            'Tables Checked': [', '.join(report.tables_checked)]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Tables sheet
        if report.report_data and 'table_reports' in report.report_data:
            tables_data = []
            
            for table_name, table_report in report.report_data['table_reports'].items():
                if table_report.get('status') == 'checked':
                    tables_data.append({
                        'Table': table_name,
                        'Records Checked': table_report.get('records_checked', 0),
                        'Validation Issues': table_report.get('validation_issues', 0),
                        'Anomalies': table_report.get('anomalies_found', 0),
                        'Quality Score': f"{table_report.get('quality_score', 0):.1f}%" if table_report.get('quality_score') is not None else 'N/A'
                    })
            
            if tables_data:
                tables_df = pd.DataFrame(tables_data)
                tables_df.to_excel(writer, sheet_name='Tables', index=False)
        
        # Critical Issues sheet
        if report.report_data and 'critical_issues' in report.report_data and report.report_data['critical_issues']:
            issues_data = []
            
            for issue in report.report_data['critical_issues']:
                issues_data.append({
                    'Table': issue.get('table', ''),
                    'Type': issue.get('type', ''),
                    'Message': issue.get('message', '')
                })
            
            if issues_data:
                issues_df = pd.DataFrame(issues_data)
                issues_df.to_excel(writer, sheet_name='Critical Issues', index=False)
        
        writer.save()
        output.seek(0)
        
        filename = f"data_quality_report_{report_id}_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Error downloading data quality report: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error downloading report: {str(e)}"
        }), 400

@data_quality_bp.route('/api/table-fields', methods=['GET'])
@login_required
def get_table_fields():
    """Get fields for a specific table"""
    try:
        table_name = request.args.get('table_name')
        
        if not table_name:
            return jsonify({
                'success': False,
                'message': 'Table name is required'
            }), 400
        
        # Get columns from table
        inspector = inspect(db.engine)
        columns = inspector.get_columns(table_name)
        
        field_names = [col['name'] for col in columns]
        
        return jsonify({
            'success': True,
            'fields': field_names
        })
    except Exception as e:
        logger.error(f"Error getting table fields: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting table fields: {str(e)}"
        }), 400

def register_data_quality_blueprint(app):
    """Register the data_quality blueprint with the app"""
    app.register_blueprint(data_quality_bp)
    logger.info("Data Quality blueprint registered successfully")