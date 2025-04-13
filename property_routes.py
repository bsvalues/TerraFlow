"""
Property Routes Module

This module provides Flask routes for property management and assessment.
"""

import os
import uuid
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename

from auth import login_required, permission_required, has_role
from property_model import Property, Assessment
from storage_handlers import store_file, delete_stored_file, get_file_url

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
property_bp = Blueprint('property', __name__, url_prefix='/property')

@property_bp.route('/')
@login_required
def property_list():
    """Property listing page"""
    return render_template('property/property_list.html')

@property_bp.route('/<property_id>')
@login_required
def property_detail(property_id):
    """Property detail page"""
    property_obj = Property.get_by_id(property_id)
    if not property_obj:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    return render_template('property/property_detail.html', property=property_obj)

@property_bp.route('/search')
@login_required
def property_search():
    """Property search page"""
    return render_template('property/property_search.html')

@property_bp.route('/new', methods=['GET', 'POST'])
@login_required
@permission_required('property:create')
def property_create():
    """Create a new property"""
    if request.method == 'POST':
        try:
            # Extract property data from form
            property_data = {
                'parcel_id': request.form.get('parcel_id'),
                'account_number': request.form.get('account_number'),
                'legal_description': request.form.get('legal_description'),
                'address': request.form.get('address'),
                'city': request.form.get('city'),
                'state': request.form.get('state', 'WA'),
                'zip_code': request.form.get('zip_code'),
                'latitude': float(request.form.get('latitude')) if request.form.get('latitude') else None,
                'longitude': float(request.form.get('longitude')) if request.form.get('longitude') else None,
                'property_class': request.form.get('property_class'),
                'zoning': request.form.get('zoning'),
                'land_area': float(request.form.get('land_area')) if request.form.get('land_area') else None,
                'land_value': float(request.form.get('land_value')) if request.form.get('land_value') else None,
                'improvement_value': float(request.form.get('improvement_value')) if request.form.get('improvement_value') else None,
                'total_value': float(request.form.get('total_value')) if request.form.get('total_value') else None,
                'year_built': int(request.form.get('year_built')) if request.form.get('year_built') else None,
                'bedrooms': int(request.form.get('bedrooms')) if request.form.get('bedrooms') else None,
                'bathrooms': float(request.form.get('bathrooms')) if request.form.get('bathrooms') else None,
                'living_area': float(request.form.get('living_area')) if request.form.get('living_area') else None,
                'lot_size': float(request.form.get('lot_size')) if request.form.get('lot_size') else None,
                'owner_name': request.form.get('owner_name'),
                'owner_address': request.form.get('owner_address'),
                'owner_city': request.form.get('owner_city'),
                'owner_state': request.form.get('owner_state'),
                'owner_zip': request.form.get('owner_zip'),
                'status': request.form.get('status', 'active')
            }
            
            # Parse sale date if provided
            sale_date = request.form.get('last_sale_date')
            if sale_date:
                try:
                    property_data['last_sale_date'] = datetime.strptime(sale_date, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Parse sale price if provided
            sale_price = request.form.get('last_sale_price')
            if sale_price:
                try:
                    property_data['last_sale_price'] = float(sale_price)
                except ValueError:
                    pass
            
            # Set geometry from lat/long if available
            if property_data['latitude'] is not None and property_data['longitude'] is not None:
                # Using PostGIS to create the geometry
                property_data['geometry'] = f"SRID=4326;POINT({property_data['longitude']} {property_data['latitude']})"
            
            # Create the property
            property_obj = Property(property_data)
            if property_obj.save():
                flash('Property created successfully', 'success')
                return redirect(url_for('property.property_detail', property_id=property_obj.id))
            else:
                flash('Failed to create property', 'danger')
        except Exception as e:
            logger.error(f"Error creating property: {str(e)}")
            flash(f'Error creating property: {str(e)}', 'danger')
    
    return render_template('property/property_form.html', property=None)

@property_bp.route('/<property_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('property:edit')
def property_edit(property_id):
    """Edit a property"""
    property_obj = Property.get_by_id(property_id)
    if not property_obj:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    if request.method == 'POST':
        try:
            # Extract property data from form
            property_data = {
                'parcel_id': request.form.get('parcel_id'),
                'account_number': request.form.get('account_number'),
                'legal_description': request.form.get('legal_description'),
                'address': request.form.get('address'),
                'city': request.form.get('city'),
                'state': request.form.get('state', 'WA'),
                'zip_code': request.form.get('zip_code'),
                'latitude': float(request.form.get('latitude')) if request.form.get('latitude') else None,
                'longitude': float(request.form.get('longitude')) if request.form.get('longitude') else None,
                'property_class': request.form.get('property_class'),
                'zoning': request.form.get('zoning'),
                'land_area': float(request.form.get('land_area')) if request.form.get('land_area') else None,
                'land_value': float(request.form.get('land_value')) if request.form.get('land_value') else None,
                'improvement_value': float(request.form.get('improvement_value')) if request.form.get('improvement_value') else None,
                'total_value': float(request.form.get('total_value')) if request.form.get('total_value') else None,
                'year_built': int(request.form.get('year_built')) if request.form.get('year_built') else None,
                'bedrooms': int(request.form.get('bedrooms')) if request.form.get('bedrooms') else None,
                'bathrooms': float(request.form.get('bathrooms')) if request.form.get('bathrooms') else None,
                'living_area': float(request.form.get('living_area')) if request.form.get('living_area') else None,
                'lot_size': float(request.form.get('lot_size')) if request.form.get('lot_size') else None,
                'owner_name': request.form.get('owner_name'),
                'owner_address': request.form.get('owner_address'),
                'owner_city': request.form.get('owner_city'),
                'owner_state': request.form.get('owner_state'),
                'owner_zip': request.form.get('owner_zip'),
                'status': request.form.get('status', 'active')
            }
            
            # Parse sale date if provided
            sale_date = request.form.get('last_sale_date')
            if sale_date:
                try:
                    property_data['last_sale_date'] = datetime.strptime(sale_date, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Parse sale price if provided
            sale_price = request.form.get('last_sale_price')
            if sale_price:
                try:
                    property_data['last_sale_price'] = float(sale_price)
                except ValueError:
                    pass
            
            # Set geometry from lat/long if available
            if property_data['latitude'] is not None and property_data['longitude'] is not None:
                # Using PostGIS to create the geometry
                property_data['geometry'] = f"SRID=4326;POINT({property_data['longitude']} {property_data['latitude']})"
            
            # Update the property
            property_obj.load_data(property_data)
            if property_obj.save():
                flash('Property updated successfully', 'success')
                return redirect(url_for('property.property_detail', property_id=property_obj.id))
            else:
                flash('Failed to update property', 'danger')
        except Exception as e:
            logger.error(f"Error updating property: {str(e)}")
            flash(f'Error updating property: {str(e)}', 'danger')
    
    return render_template('property/property_form.html', property=property_obj)

@property_bp.route('/<property_id>/delete', methods=['POST'])
@login_required
@permission_required('property:delete')
def property_delete(property_id):
    """Delete a property"""
    property_obj = Property.get_by_id(property_id)
    if not property_obj:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    if property_obj.delete():
        flash('Property deleted successfully', 'success')
    else:
        flash('Failed to delete property', 'danger')
    
    return redirect(url_for('property.property_list'))

@property_bp.route('/<property_id>/assessments')
@login_required
def property_assessments(property_id):
    """Property assessments page"""
    property_obj = Property.get_by_id(property_id)
    if not property_obj:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    assessments = property_obj.get_assessments()
    
    return render_template(
        'property/property_assessments.html', 
        property=property_obj, 
        assessments=assessments
    )

@property_bp.route('/<property_id>/assessments/new', methods=['GET', 'POST'])
@login_required
@permission_required('assessment:create')
def assessment_create(property_id):
    """Create a new assessment for a property"""
    property_obj = Property.get_by_id(property_id)
    if not property_obj:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    if request.method == 'POST':
        try:
            # Extract assessment data from form
            assessment_data = {
                'property_id': property_obj.id,
                'tax_year': int(request.form.get('tax_year')),
                'land_value': float(request.form.get('land_value')) if request.form.get('land_value') else None,
                'improvement_value': float(request.form.get('improvement_value')) if request.form.get('improvement_value') else None,
                'total_value': float(request.form.get('total_value')) if request.form.get('total_value') else None,
                'exemption_value': float(request.form.get('exemption_value', 0)),
                'assessment_type': request.form.get('assessment_type'),
                'assessment_status': request.form.get('assessment_status', 'pending'),
                'notes': request.form.get('notes')
            }
            
            # Parse assessment date if provided
            assessment_date = request.form.get('assessment_date')
            if assessment_date:
                try:
                    assessment_data['assessment_date'] = datetime.strptime(assessment_date, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Create the assessment
            assessment_obj = Assessment(assessment_data)
            if assessment_obj.save():
                flash('Assessment created successfully', 'success')
                return redirect(url_for('property.property_assessments', property_id=property_obj.id))
            else:
                flash('Failed to create assessment', 'danger')
        except Exception as e:
            logger.error(f"Error creating assessment: {str(e)}")
            flash(f'Error creating assessment: {str(e)}', 'danger')
    
    return render_template(
        'property/assessment_form.html', 
        property=property_obj, 
        assessment=None
    )

@property_bp.route('/<property_id>/assessments/<assessment_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('assessment:edit')
def assessment_edit(property_id, assessment_id):
    """Edit an assessment"""
    property_obj = Property.get_by_id(property_id)
    if not property_obj:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    assessment_obj = Assessment.get_by_id(assessment_id)
    if not assessment_obj:
        flash('Assessment not found', 'danger')
        return redirect(url_for('property.property_assessments', property_id=property_id))
    
    if str(assessment_obj.property_id) != str(property_id):
        flash('Assessment does not belong to this property', 'danger')
        return redirect(url_for('property.property_assessments', property_id=property_id))
    
    if request.method == 'POST':
        try:
            # Extract assessment data from form
            assessment_data = {
                'tax_year': int(request.form.get('tax_year')),
                'land_value': float(request.form.get('land_value')) if request.form.get('land_value') else None,
                'improvement_value': float(request.form.get('improvement_value')) if request.form.get('improvement_value') else None,
                'total_value': float(request.form.get('total_value')) if request.form.get('total_value') else None,
                'exemption_value': float(request.form.get('exemption_value', 0)),
                'assessment_type': request.form.get('assessment_type'),
                'assessment_status': request.form.get('assessment_status'),
                'notes': request.form.get('notes')
            }
            
            # Parse assessment date if provided
            assessment_date = request.form.get('assessment_date')
            if assessment_date:
                try:
                    assessment_data['assessment_date'] = datetime.strptime(assessment_date, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Update the assessment
            assessment_obj.load_data(assessment_data)
            if assessment_obj.save():
                flash('Assessment updated successfully', 'success')
                return redirect(url_for('property.property_assessments', property_id=property_id))
            else:
                flash('Failed to update assessment', 'danger')
        except Exception as e:
            logger.error(f"Error updating assessment: {str(e)}")
            flash(f'Error updating assessment: {str(e)}', 'danger')
    
    return render_template(
        'property/assessment_form.html', 
        property=property_obj, 
        assessment=assessment_obj
    )

@property_bp.route('/<property_id>/assessments/<assessment_id>/delete', methods=['POST'])
@login_required
@permission_required('assessment:delete')
def assessment_delete(property_id, assessment_id):
    """Delete an assessment"""
    property_obj = Property.get_by_id(property_id)
    if not property_obj:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    assessment_obj = Assessment.get_by_id(assessment_id)
    if not assessment_obj:
        flash('Assessment not found', 'danger')
        return redirect(url_for('property.property_assessments', property_id=property_id))
    
    if str(assessment_obj.property_id) != str(property_id):
        flash('Assessment does not belong to this property', 'danger')
        return redirect(url_for('property.property_assessments', property_id=property_id))
    
    if assessment_obj.delete():
        flash('Assessment deleted successfully', 'success')
    else:
        flash('Failed to delete assessment', 'danger')
    
    return redirect(url_for('property.property_assessments', property_id=property_id))

@property_bp.route('/<property_id>/files')
@login_required
def property_files(property_id):
    """Property files page"""
    property_obj = Property.get_by_id(property_id)
    if not property_obj:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    files = property_obj.get_files()
    
    return render_template(
        'property/property_files.html', 
        property=property_obj, 
        files=files
    )

@property_bp.route('/<property_id>/files/upload', methods=['POST'])
@login_required
@permission_required('property:edit')
def property_file_upload(property_id):
    """Upload a file for a property"""
    property_obj = Property.get_by_id(property_id)
    if not property_obj:
        flash('Property not found', 'danger')
        return redirect(url_for('property.property_list'))
    
    # Check if the post request has the file part
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('property.property_files', property_id=property_id))
    
    file = request.files['file']
    
    # If the user does not select a file, the browser submits an empty file without a filename
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('property.property_files', property_id=property_id))
    
    try:
        # Get file category from form
        file_category = request.form.get('file_category', 'Other')
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Store the file
        from flask_login import current_user
        file_info = store_file(file, filename, str(property_obj.id), 'property_files')
        
        if not file_info:
            flash('Failed to store file', 'danger')
            return redirect(url_for('property.property_files', property_id=property_id))
        
        # Get the Supabase client for database operation
        from supabase_client import get_supabase_client, insert_record
        
        # Create a record in the property_files table
        file_record = {
            'property_id': str(property_obj.id),
            'file_name': filename,
            'file_type': file.content_type if hasattr(file, 'content_type') else None,
            'file_size': file_info.get('size', 0),
            'storage_path': file_info.get('path'),
            'public_url': file_info.get('url'),
            'file_category': file_category,
            'uploaded_by': str(current_user.id) if hasattr(current_user, 'id') else None,
            'metadata': json.dumps(file_info.get('metadata', {}))
        }
        
        result = insert_record('property_files', file_record)
        
        if result:
            flash('File uploaded successfully', 'success')
        else:
            flash('File uploaded but database record failed', 'warning')
        
        return redirect(url_for('property.property_files', property_id=property_id))
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        flash(f'Error uploading file: {str(e)}', 'danger')
        return redirect(url_for('property.property_files', property_id=property_id))

@property_bp.route('/files/<file_id>/delete', methods=['POST'])
@login_required
@permission_required('property:edit')
def property_file_delete(file_id):
    """Delete a property file"""
    # Get the file from the database
    from supabase_client import execute_query, delete_record
    
    result = execute_query('property_files', '*', {'id': file_id})
    if not result or len(result) == 0:
        flash('File not found', 'danger')
        return redirect(request.referrer or url_for('property.property_list'))
    
    file_info = result[0]
    property_id = file_info.get('property_id')
    
    try:
        # Delete from storage first
        if file_info.get('storage_path'):
            delete_result = delete_stored_file('files', file_info['storage_path'])
            if not delete_result:
                logger.warning(f"Failed to delete file from storage: {file_info['storage_path']}")
        
        # Then delete the database record
        delete_result = delete_record('property_files', file_id)
        
        if delete_result:
            flash('File deleted successfully', 'success')
        else:
            flash('Failed to delete file record', 'danger')
        
        if property_id:
            return redirect(url_for('property.property_files', property_id=property_id))
        else:
            return redirect(request.referrer or url_for('property.property_list'))
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        flash(f'Error deleting file: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('property.property_list'))

# API Routes
@property_bp.route('/api/properties', methods=['GET'])
@login_required
def api_properties():
    """API to get properties"""
    try:
        # Extract query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Limit to 100 items per page
        query = {}
        
        # Add filters from query parameters
        for key, value in request.args.items():
            if key not in ['page', 'per_page']:
                # Handle special filters
                if key.endswith('_like'):
                    base_key = key.replace('_like', '')
                    query[base_key] = {'like': value}
                elif key.endswith('_gt'):
                    base_key = key.replace('_gt', '')
                    query[base_key] = {'gt': value}
                elif key.endswith('_gte'):
                    base_key = key.replace('_gte', '')
                    query[base_key] = {'gte': value}
                elif key.endswith('_lt'):
                    base_key = key.replace('_lt', '')
                    query[base_key] = {'lt': value}
                elif key.endswith('_lte'):
                    base_key = key.replace('_lte', '')
                    query[base_key] = {'lte': value}
                else:
                    query[key] = value
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get properties
        properties = Property.search(query, per_page, offset)
        
        # Format response
        return jsonify({
            'success': True,
            'data': [p.to_dict() for p in properties],
            'page': page,
            'per_page': per_page
        })
    except Exception as e:
        logger.error(f"Error in API properties: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@property_bp.route('/api/properties/<property_id>', methods=['GET'])
@login_required
def api_property_detail(property_id):
    """API to get property details"""
    try:
        property_obj = Property.get_by_id(property_id)
        if not property_obj:
            return jsonify({
                'success': False,
                'error': 'Property not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': property_obj.to_dict()
        })
    except Exception as e:
        logger.error(f"Error in API property detail: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@property_bp.route('/api/properties/<property_id>/assessments', methods=['GET'])
@login_required
def api_property_assessments(property_id):
    """API to get property assessments"""
    try:
        property_obj = Property.get_by_id(property_id)
        if not property_obj:
            return jsonify({
                'success': False,
                'error': 'Property not found'
            }), 404
        
        assessments = property_obj.get_assessments()
        
        return jsonify({
            'success': True,
            'data': assessments
        })
    except Exception as e:
        logger.error(f"Error in API property assessments: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@property_bp.route('/api/properties/<property_id>/files', methods=['GET'])
@login_required
def api_property_files(property_id):
    """API to get property files"""
    try:
        property_obj = Property.get_by_id(property_id)
        if not property_obj:
            return jsonify({
                'success': False,
                'error': 'Property not found'
            }), 404
        
        files = property_obj.get_files()
        
        return jsonify({
            'success': True,
            'data': files
        })
    except Exception as e:
        logger.error(f"Error in API property files: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@property_bp.route('/api/properties/nearby', methods=['GET'])
@login_required
def api_nearby_properties():
    """API to get nearby properties"""
    try:
        # Extract query parameters
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)
        distance = request.args.get('distance', 1000, type=float)  # Default to 1km
        limit = min(request.args.get('limit', 10, type=int), 100)  # Limit to 100 items
        
        if not latitude or not longitude:
            return jsonify({
                'success': False,
                'error': 'Latitude and longitude are required'
            }), 400
        
        # Get nearby properties
        properties = Property.find_nearby(latitude, longitude, distance, limit)
        
        return jsonify({
            'success': True,
            'data': properties
        })
    except Exception as e:
        logger.error(f"Error in API nearby properties: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@property_bp.route('/api/properties/<property_id>/comparables', methods=['GET'])
@login_required
def api_property_comparables(property_id):
    """API to get comparable properties"""
    try:
        limit = min(request.args.get('limit', 10, type=int), 100)  # Limit to 100 items
        
        # Get comparable properties
        comparables = Property.find_comparables(property_id, limit)
        
        return jsonify({
            'success': True,
            'data': comparables
        })
    except Exception as e:
        logger.error(f"Error in API property comparables: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500