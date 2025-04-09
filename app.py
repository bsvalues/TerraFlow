import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
import ldap
from functools import wraps
import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///benton_gis.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure file uploads
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1GB max upload size
app.config["ALLOWED_EXTENSIONS"] = {
    'zip', 'shp', 'shx', 'dbf', 'prj', 'xml', 'json', 'geojson', 
    'gpkg', 'kml', 'kmz', 'csv', 'xls', 'xlsx', 'pdf', 'txt'
}

# Make sure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize the database
db.init_app(app)

# Add template context processors
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now()}

# Import views and models after app is created to avoid circular imports
with app.app_context():
    from models import User, File, GISProject, QueryLog
    from auth import login_required, is_authenticated, authenticate_user, logout_user
    from file_handlers import allowed_file, process_file_upload, get_user_files, delete_file
    from rag import process_query, index_document
    from gis_utils import validate_geojson, get_shapefile_info
    from mcp_api import mcp_api
    
    # Register blueprints
    app.register_blueprint(mcp_api, url_prefix='/mcp')
    
    # Create database tables
    db.create_all()
    
    # Initialize MCP system
    from mcp.core import mcp_instance
    mcp_instance.discover_agents()

# Define route handlers
@app.route('/')
def index():
    if is_authenticated():
        return render_template('index.html', user=session.get('user'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if authenticate_user(username, password):
            # After successful authentication
            user = User.query.filter_by(username=username).first()
            if not user:
                # Create user if not exists
                user = User(username=username, email=f"{username}@co.benton.wa.us")
                db.session.add(user)
                db.session.commit()
            
            session['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
            
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/file-manager')
@login_required
def file_manager():
    files = get_user_files(session['user']['id'])
    return render_template('file_manager.html', files=files)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('file_manager'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('file_manager'))
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            project_name = request.form.get('project_name', 'Default Project')
            description = request.form.get('description', '')
            
            file_record = process_file_upload(file, filename, session['user']['id'], project_name, description)
            
            # Index the file for RAG if it's a text file or metadata
            if filename.endswith(('.txt', '.pdf', '.xml')):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(file_record.id), filename)
                index_document(file_path, file_record.id, description)
                
            flash('File uploaded successfully', 'success')
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            flash(f'Error uploading file: {str(e)}', 'danger')
    else:
        flash(f'File type not allowed. Allowed types: {", ".join(app.config["ALLOWED_EXTENSIONS"])}', 'danger')
    
    return redirect(url_for('file_manager'))

@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file_record = File.query.get_or_404(file_id)
    
    # Check if user has access to this file
    if file_record.user_id != session['user']['id']:
        flash('You do not have permission to access this file', 'danger')
        return redirect(url_for('file_manager'))
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(file_id))
    return send_from_directory(file_path, file_record.filename, as_attachment=True)

@app.route('/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file_route(file_id):
    try:
        delete_file(file_id, session['user']['id'])
        flash('File deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting file: {str(e)}', 'danger')
    
    return redirect(url_for('file_manager'))

@app.route('/map-viewer')
@login_required
def map_viewer():
    # Get GeoJSON files for the user
    geojson_files = File.query.filter(
        File.user_id == session['user']['id'], 
        File.filename.like('%.geojson')
    ).all()
    
    return render_template('map_viewer.html', geojson_files=geojson_files)

@app.route('/map-data/<int:file_id>')
@login_required
def map_data(file_id):
    file_record = File.query.get_or_404(file_id)
    
    # Check if user has access to this file
    if file_record.user_id != session['user']['id']:
        return jsonify({'error': 'Access denied'}), 403
    
    # Only serve GeoJSON files
    if not file_record.filename.endswith('.geojson'):
        return jsonify({'error': 'File is not GeoJSON'}), 400
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(file_id), file_record.filename)
    
    try:
        with open(file_path, 'r') as f:
            geojson_data = f.read()
        return geojson_data, 200, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error(f"Error reading GeoJSON file: {str(e)}")
        return jsonify({'error': f'Error reading file: {str(e)}'}), 500

@app.route('/search')
@login_required
def search_page():
    return render_template('search.html')

@app.route('/mcp-dashboard')
@login_required
def mcp_dashboard():
    """MCP system dashboard page"""
    return render_template('mcp_dashboard.html')

@app.route('/api/search', methods=['POST'])
@login_required
def search_api():
    query = request.json.get('query', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        # Log the query
        query_log = QueryLog(
            user_id=session['user']['id'],
            query=query,
            timestamp=datetime.datetime.now()
        )
        db.session.add(query_log)
        db.session.commit()
        
        # Process the query using RAG
        results = process_query(query, user_id=session['user']['id'])
        return jsonify(results)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': f'Search error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
