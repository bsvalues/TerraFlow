"""
Quality Report Routes

This module provides routes for generating and downloading data quality reports.
"""

import logging
import datetime
from flask import Blueprint, request, jsonify, send_file, render_template, abort, make_response
from io import BytesIO
from werkzeug.exceptions import BadRequest

from auth import login_required, permission_required
from sync_service.quality_report_generator import report_generator

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
quality_report_bp = Blueprint('quality_report', __name__, url_prefix='/data-quality/reports')

@quality_report_bp.route('/', methods=['GET'])
@login_required
def report_dashboard():
    """Render the report dashboard page."""
    return render_template('data_quality/reports.html')

@quality_report_bp.route('/generate', methods=['GET'])
@login_required
def generate_report_form():
    """Render the report generation form."""
    return render_template('data_quality/generate_report.html')

@quality_report_bp.route('/generate', methods=['POST'])
@login_required
@permission_required('data_quality_reports')
def generate_report():
    """Generate a data quality report based on form parameters."""
    try:
        # Get form parameters
        report_format = request.form.get('format', 'pdf')
        report_id = request.form.get('report_id')
        if report_id:
            try:
                report_id = int(report_id)
            except ValueError:
                report_id = None
                
        # Parse date parameters if provided
        start_date = None
        end_date = None
        
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        if start_date_str:
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                pass
                
        if end_date_str:
            try:
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
                # Set to end of day
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                pass
                
        # Generate report based on format
        if report_format == 'pdf':
            pdf_bytes, filename = report_generator.generate_pdf_report(
                report_id=report_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Return PDF as downloadable attachment
            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        # Future: support for Excel reports
        elif report_format == 'excel':
            # Not implemented yet
            return jsonify({'error': 'Excel format not implemented yet'}), 501
            
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
    except Exception as e:
        logger.exception(f"Error generating report: {str(e)}")
        return jsonify({'error': f'Error generating report: {str(e)}'}), 500

@quality_report_bp.route('/api/generate', methods=['POST'])
@login_required
@permission_required('data_quality_reports')
def api_generate_report():
    """API endpoint for generating a report."""
    try:
        # Get JSON parameters
        data = request.get_json() or {}
        
        report_format = data.get('format', 'pdf')
        report_id = data.get('report_id')
        
        # Parse date parameters
        start_date = None
        end_date = None
        
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if start_date_str:
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                pass
                
        if end_date_str:
            try:
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
                # Set to end of day
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                pass
                
        # Generate PDF report
        if report_format == 'pdf':
            pdf_bytes, filename = report_generator.generate_pdf_report(
                report_id=report_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Return base64 encoded PDF
            import base64
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            return jsonify({
                'success': True,
                'filename': filename,
                'data': pdf_base64,
                'format': 'pdf'
            })
            
        # Future: support for Excel reports
        elif report_format == 'excel':
            # Not implemented yet
            return jsonify({'error': 'Excel format not implemented yet'}), 501
            
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
    except Exception as e:
        logger.exception(f"Error generating report via API: {str(e)}")
        return jsonify({'error': f'Error generating report: {str(e)}'}), 500

@quality_report_bp.route('/download/<report_id>', methods=['GET'])
@login_required
def download_report(report_id):
    """Download a previously generated report by ID."""
    # For future implementation - store generated reports in database or filesystem
    abort(501, "Report download by ID not implemented yet")

def register_blueprint(app):
    """Register the blueprint with the app."""
    app.register_blueprint(quality_report_bp)
    logger.info("Quality Report blueprint registered")