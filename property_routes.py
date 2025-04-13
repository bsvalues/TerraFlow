"""
Property Routes Module

This module provides Flask routes for accessing property data and managing
property records, assessments, and files.
"""

import os
import uuid
import datetime
from typing import Dict, Any, Optional, List

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required

import property_model as pm
from auth import permission_required


# Create blueprint
property_bp = Blueprint('property', __name__, url_prefix='/property')


@property_bp.route('/')
@login_required
def property_list():
    """Render the property list page"""
    return render_template('property/property_list.html')


@property_bp.route('/api/properties')
@login_required
def property_api_list():
    """Get properties API endpoint"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Get filter parameters
        filters = {}
        for key, value in request.args.items():
            if key not in ['page', 'per_page'] and value:
                filters[key] = value
        
        # Get user ID for access control
        user_id = str(current_user.id) if current_user and current_user.is_authenticated else None
        
        # Get properties
        properties, total_count, has_more = pm.get_properties(page, per_page, filters, user_id)
        
        return jsonify({
            'success': True,
            'data': properties,
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'has_more': has_more
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@property_bp.route('/<property_id>')
@login_required
def property_detail(property_id):
    """Render the property detail page"""
    # Get user ID for access control
    user_id = str(current_user.id) if current_user and current_user.is_authenticated else None
    
    # Get property
    property_data = pm.get_property(property_id, user_id)
    
    if not property_data:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    return render_template('property/property_detail.html', property=property_data)


@property_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('property.create')
def property_create():
    """Create a new property"""
    if request.method == 'POST':
        # Get form data
        property_data = {}
        for key, value in request.form.items():
            if value:
                # Convert numeric values
                if key in ['land_area', 'lot_size', 'land_value', 'improvement_value', 
                           'total_value', 'living_area', 'bathrooms', 'last_sale_price',
                           'latitude', 'longitude']:
                    try:
                        property_data[key] = float(value)
                    except (ValueError, TypeError):
                        property_data[key] = None
                # Convert integer values
                elif key in ['year_built', 'bedrooms']:
                    try:
                        property_data[key] = int(value)
                    except (ValueError, TypeError):
                        property_data[key] = None
                # Convert date values
                elif key in ['last_sale_date']:
                    try:
                        property_data[key] = value if value else None
                    except (ValueError, TypeError):
                        property_data[key] = None
                else:
                    property_data[key] = value
        
        # Get user ID for access control
        user_id = str(current_user.id)
        
        # Create property
        property_id = pm.create_property(property_data, user_id)
        
        if property_id:
            flash('Property created successfully', 'success')
            return redirect(url_for('property.property_detail', property_id=property_id))
        else:
            flash('Failed to create property', 'danger')
    
    # Display form
    return render_template('property/property_form.html', property={})


@property_bp.route('/<property_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('property.edit')
def property_edit(property_id):
    """Edit a property"""
    # Get user ID for access control
    user_id = str(current_user.id)
    
    # Get property
    property_data = pm.get_property(property_id, user_id)
    
    if not property_data:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    if request.method == 'POST':
        # Get form data
        updated_data = {}
        for key, value in request.form.items():
            if key != 'id':  # Skip ID field
                # Convert numeric values
                if key in ['land_area', 'lot_size', 'land_value', 'improvement_value', 
                           'total_value', 'living_area', 'bathrooms', 'last_sale_price',
                           'latitude', 'longitude']:
                    try:
                        updated_data[key] = float(value) if value else None
                    except (ValueError, TypeError):
                        updated_data[key] = None
                # Convert integer values
                elif key in ['year_built', 'bedrooms']:
                    try:
                        updated_data[key] = int(value) if value else None
                    except (ValueError, TypeError):
                        updated_data[key] = None
                # Convert date values
                elif key in ['last_sale_date']:
                    try:
                        updated_data[key] = value if value else None
                    except (ValueError, TypeError):
                        updated_data[key] = None
                else:
                    updated_data[key] = value
        
        # Update property
        success = pm.update_property(property_id, updated_data, user_id)
        
        if success:
            flash('Property updated successfully', 'success')
            return redirect(url_for('property.property_detail', property_id=property_id))
        else:
            flash('Failed to update property', 'danger')
    
    # Display form
    return render_template('property/property_form.html', property=property_data)


@property_bp.route('/<property_id>/delete', methods=['POST'])
@login_required
@permission_required('property.delete')
def property_delete(property_id):
    """Delete a property"""
    # Get user ID for access control
    user_id = str(current_user.id)
    
    # Delete property
    success = pm.delete_property(property_id, user_id)
    
    if success:
        flash('Property deleted successfully', 'success')
    else:
        flash('Failed to delete property', 'danger')
    
    return redirect(url_for('property.property_list'))


@property_bp.route('/<property_id>/assessments')
@login_required
def property_assessments(property_id):
    """Render the property assessments page"""
    # Get user ID for access control
    user_id = str(current_user.id)
    
    # Get property
    property_data = pm.get_property(property_id, user_id)
    
    if not property_data:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    # Get assessments
    assessments = pm.get_property_assessments(property_id, user_id)
    
    return render_template('property/property_assessments.html', 
                           property=property_data,
                           assessments=assessments)


@property_bp.route('/api/properties/<property_id>/assessments')
@login_required
def property_assessments_api(property_id):
    """Get property assessments API endpoint"""
    try:
        # Get user ID for access control
        user_id = str(current_user.id)
        
        # Get assessments
        assessments = pm.get_property_assessments(property_id, user_id)
        
        return jsonify({
            'success': True,
            'data': assessments
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@property_bp.route('/<property_id>/assessments/create', methods=['GET', 'POST'])
@login_required
@permission_required('property.assessment.create')
def assessment_create(property_id):
    """Create a new assessment for a property"""
    # Get user ID for access control
    user_id = str(current_user.id)
    
    # Get property
    property_data = pm.get_property(property_id, user_id)
    
    if not property_data:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    if request.method == 'POST':
        # Get form data
        assessment_data = {}
        for key, value in request.form.items():
            if value:
                # Convert numeric values
                if key in ['land_value', 'improvement_value', 'total_value', 'exemption_value', 'taxable_value']:
                    try:
                        assessment_data[key] = float(value)
                    except (ValueError, TypeError):
                        assessment_data[key] = None
                # Convert integer values
                elif key in ['tax_year']:
                    try:
                        assessment_data[key] = int(value)
                    except (ValueError, TypeError):
                        assessment_data[key] = None
                # Convert date values
                elif key in ['assessment_date']:
                    try:
                        assessment_data[key] = value if value else None
                    except (ValueError, TypeError):
                        assessment_data[key] = None
                else:
                    assessment_data[key] = value
        
        # Create assessment
        assessment_id = pm.create_property_assessment(property_id, assessment_data, user_id)
        
        if assessment_id:
            flash('Assessment created successfully', 'success')
            return redirect(url_for('property.property_assessments', property_id=property_id))
        else:
            flash('Failed to create assessment', 'danger')
    
    # Display form
    return render_template('property/assessment_form.html', 
                           property=property_data,
                           assessment={})


@property_bp.route('/<property_id>/assessments/<assessment_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('property.assessment.edit')
def assessment_edit(property_id, assessment_id):
    """Edit a property assessment"""
    # Get user ID for access control
    user_id = str(current_user.id)
    
    # Get property
    property_data = pm.get_property(property_id, user_id)
    
    if not property_data:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    # Get assessment
    assessment = pm.get_property_assessment(property_id, assessment_id, user_id)
    
    if not assessment:
        flash('Assessment not found', 'danger')
        return redirect(url_for('property.property_assessments', property_id=property_id))
    
    if request.method == 'POST':
        # Get form data
        assessment_data = {}
        for key, value in request.form.items():
            if key != 'id' and key != 'property_id':  # Skip ID fields
                # Convert numeric values
                if key in ['land_value', 'improvement_value', 'total_value', 'exemption_value', 'taxable_value']:
                    try:
                        assessment_data[key] = float(value) if value else None
                    except (ValueError, TypeError):
                        assessment_data[key] = None
                # Convert integer values
                elif key in ['tax_year']:
                    try:
                        assessment_data[key] = int(value) if value else None
                    except (ValueError, TypeError):
                        assessment_data[key] = None
                # Convert date values
                elif key in ['assessment_date']:
                    try:
                        assessment_data[key] = value if value else None
                    except (ValueError, TypeError):
                        assessment_data[key] = None
                else:
                    assessment_data[key] = value
        
        # Update assessment
        success = pm.update_property_assessment(property_id, assessment_id, assessment_data, user_id)
        
        if success:
            flash('Assessment updated successfully', 'success')
            return redirect(url_for('property.property_assessments', property_id=property_id))
        else:
            flash('Failed to update assessment', 'danger')
    
    # Display form
    return render_template('property/assessment_form.html', 
                           property=property_data,
                           assessment=assessment)


@property_bp.route('/<property_id>/assessments/<assessment_id>/delete', methods=['POST'])
@login_required
@permission_required('property.assessment.delete')
def assessment_delete(property_id, assessment_id):
    """Delete a property assessment"""
    # Get user ID for access control
    user_id = str(current_user.id)
    
    # Delete assessment
    success = pm.delete_property_assessment(property_id, assessment_id, user_id)
    
    if success:
        flash('Assessment deleted successfully', 'success')
    else:
        flash('Failed to delete assessment', 'danger')
    
    return redirect(url_for('property.property_assessments', property_id=property_id))


@property_bp.route('/<property_id>/files')
@login_required
def property_files(property_id):
    """Render the property files page"""
    # Get user ID for access control
    user_id = str(current_user.id)
    
    # Get property
    property_data = pm.get_property(property_id, user_id)
    
    if not property_data:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    # Get files
    files = pm.get_property_files(property_id, user_id)
    
    return render_template('property/property_files.html', 
                           property=property_data,
                           files=files)


@property_bp.route('/<property_id>/files/upload', methods=['POST'])
@login_required
@permission_required('property.file.upload')
def property_file_upload(property_id):
    """Upload a file for a property"""
    # Get user ID for access control
    user_id = str(current_user.id)
    
    # Get property
    property_data = pm.get_property(property_id, user_id)
    
    if not property_data:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('property.property_files', property_id=property_id))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('property.property_files', property_id=property_id))
    
    if file:
        try:
            # Secure filename
            filename = secure_filename(file.filename)
            
            # Get file data
            file_data = {
                'file_name': filename,
                'file_size': len(file.read()),
                'file_type': file.content_type,
                'file_category': request.form.get('file_category', 'Other'),
                'description': request.form.get('description', '')
            }
            
            # Reset file pointer
            file.seek(0)
            
            # Create file
            file_id = pm.create_property_file(property_id, file_data, file.read(), user_id)
            
            if file_id:
                flash('File uploaded successfully', 'success')
            else:
                flash('Failed to upload file', 'danger')
        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'danger')
    
    return redirect(url_for('property.property_files', property_id=property_id))


@property_bp.route('/files/<file_id>/delete', methods=['POST'])
@login_required
@permission_required('property.file.delete')
def property_file_delete(file_id):
    """Delete a property file"""
    # Get user ID for access control
    user_id = str(current_user.id)
    
    # We need to find the property ID from the file ID
    try:
        client = get_supabase_client()
        if client is None:
            flash('Failed to connect to database', 'danger')
            return redirect(url_for('property.property_list'))
        
        # Get file to determine property ID
        query = client.table(f"{pm.PROPERTY_SCHEMA}.{pm.FILE_TABLE}").eq("id", file_id)
        response = query.execute()
        
        if not response.data:
            flash('File not found', 'danger')
            return redirect(url_for('property.property_list'))
        
        property_id = response.data[0]['property_id']
        
        # Delete file
        success = pm.delete_property_file(property_id, file_id, user_id)
        
        if success:
            flash('File deleted successfully', 'success')
        else:
            flash('Failed to delete file', 'danger')
        
        return redirect(url_for('property.property_files', property_id=property_id))
    except Exception as e:
        flash(f'Error deleting file: {str(e)}', 'danger')
        return redirect(url_for('property.property_list'))


# Register the blueprint
def register_property_routes(app):
    """Register property routes with the app"""
    app.register_blueprint(property_bp)
    
    # Add template context processors
    @app.context_processor
    def utility_processor():
        return {
            'has_role': lambda role: current_user.is_authenticated and hasattr(current_user, 'has_role') and current_user.has_role(role),
            'has_permission': lambda perm: current_user.is_authenticated and hasattr(current_user, 'has_permission') and current_user.has_permission(perm)
        }

    # Import the Supabase client
    from supabase_client import get_supabase_client