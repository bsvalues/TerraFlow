import os
import shutil
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
from models import File, GISProject, db
import datetime
import json
from gis_utils import extract_gis_metadata

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def process_file_upload(file, filename, user_id, project_name, description):
    """Process an uploaded file and save it to the system"""
    import logging
    logger = logging.getLogger(__name__)
    # Get or create the project
    project = GISProject.query.filter_by(name=project_name, user_id=user_id).first()
    if not project:
        project = GISProject(name=project_name, description=f"Project for {project_name}", user_id=user_id)
        db.session.add(project)
        db.session.commit()
    
    # Create a new file record
    file_record = File(
        filename=filename,
        original_filename=file.filename,
        file_path=os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', filename),  # Temporary path
        file_size=0,  # Will be updated after saving
        file_type=filename.rsplit('.', 1)[1].lower() if '.' in filename else '',
        user_id=user_id,
        project_id=project.id,
        description=description,
        file_metadata={}  # Fixed field name to match models.py
    )
    
    # Save the file record to get an ID
    db.session.add(file_record)
    db.session.commit()
    
    # Create directory for the file using its ID
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(file_record.id))
    os.makedirs(file_dir, exist_ok=True)
    
    # Save the file to disk
    file_path = os.path.join(file_dir, filename)
    file.save(file_path)
    
    # Update the file record with the actual path and size
    file_record.file_path = file_path
    file_record.file_size = os.path.getsize(file_path)
    
    # Extract and save metadata if it's a GIS file
    try:
        metadata = extract_gis_metadata(file_path, file_record.file_type)
        if metadata:
            file_record.file_metadata = metadata
    except Exception as e:
        current_app.logger.error(f"Error extracting metadata: {str(e)}")
    
    db.session.commit()
    return file_record

def get_user_files(user_id):
    """Get all files belonging to a user"""
    return File.query.filter_by(user_id=user_id).order_by(File.upload_date.desc()).all()

def delete_file(file_id, user_id):
    """Delete a file from the system"""
    file_record = File.query.filter_by(id=file_id, user_id=user_id).first()
    
    if not file_record:
        raise Exception("File not found or you don't have permission to delete it")
    
    # Delete the file directory
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(file_id))
    if os.path.exists(file_dir):
        shutil.rmtree(file_dir)
    
    # Delete the database record
    db.session.delete(file_record)
    db.session.commit()
