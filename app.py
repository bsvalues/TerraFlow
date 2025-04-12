import os
import sys
import time
import logging
import shutil
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from functools import wraps
import datetime

# Conditionally import ldap
try:
    import ldap
    HAS_LDAP = True
except ImportError:
    HAS_LDAP = False
    logger = logging.getLogger(__name__)
    logger.warning("LDAP module not available, falling back to development mode")

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

# Create a temp directory for file uploads
temp_upload_dir = os.path.join(app.config["UPLOAD_FOLDER"], 'temp')
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1GB max upload size
app.config["ALLOWED_EXTENSIONS"] = {
    'zip', 'shp', 'shx', 'dbf', 'prj', 'xml', 'json', 'geojson', 
    'gpkg', 'kml', 'kmz', 'csv', 'xls', 'xlsx', 'pdf', 'txt',
    'gdb', 'mdb', 'sdf', 'sqlite', 'db', 'geopackage'
}

# Make sure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
# Make sure temp upload directory exists
os.makedirs(temp_upload_dir, exist_ok=True)

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
    from gis_utils import validate_geojson, get_shapefile_info, extract_gis_metadata
    from mcp_api import mcp_api
    
    # Import API blueprints
    try:
        from api.gateway import api_gateway
        from api.auth import auth_api
        from api.spatial import spatial_api
        from api.data_query import data_query_api
        
        # Register API blueprints
        app.register_blueprint(api_gateway, url_prefix='/api')
        app.register_blueprint(auth_api, url_prefix='/api/auth')
        app.register_blueprint(spatial_api, url_prefix='/api/spatial')
        app.register_blueprint(data_query_api, url_prefix='/api/data')
        
        logger.info("API Gateway registered successfully")
    except ImportError as e:
        logger.warning(f"Could not load API Gateway modules: {e}")
    
    # Register MCP API blueprint
    app.register_blueprint(mcp_api, url_prefix='/mcp')
    
    # Register Sync Service blueprint
    try:
        # Import the register_blueprints function from sync_service
        from sync_service import register_blueprints
        
        # Let the sync_service handle all its blueprint registrations
        # This avoids conflicts when registering the same blueprint multiple times
        if register_blueprints(app):
            logger.info("Sync Service and Verification blueprints registered successfully")
    except ImportError as e:
        logger.warning(f"Could not load Sync Service module: {e}")
    
    # Create database tables
    db.create_all()
    
    # Create a development user if it doesn't exist
    try:
        dev_user = User.query.filter_by(username='dev_user').first()
        if not dev_user and os.environ.get('BYPASS_LDAP', 'True').lower() == 'true':
            dev_user = User(id=1, username='dev_user', email='dev_user@example.com', full_name='Development User', department='IT')
            db.session.add(dev_user)
            db.session.commit()
            logger.info("Created development user for testing")
    except Exception as e:
        logger.warning(f"Could not create development user: {str(e)}")
    
    # Initialize MCP system
    from mcp.core import mcp_instance
    
    # Only initialize the core monitoring agent for now
    # The specialized agents with complex dependencies will be loaded on demand
    try:
        from mcp.agents.monitoring_agent import MonitoringAgent
        logger.info("Successfully loaded Monitoring Agent")
    except ImportError as e:
        logger.warning(f"Could not load Monitoring Agent: {e}")
    
    # Try to load the Power Query agent
    try:
        from mcp.agents.power_query_agent import PowerQueryAgent
        mcp_instance.register_agent("power_query", PowerQueryAgent())
        logger.info("Successfully loaded Power Query Agent")
    except ImportError as e:
        logger.warning(f"Could not load Power Query Agent: {e}")
    
    # Try to load the Spatial Analysis agent
    try:
        from mcp.agents.spatial_analysis_agent import SpatialAnalysisAgent
        mcp_instance.register_agent("spatial_analysis", SpatialAnalysisAgent())
        logger.info("Successfully loaded Spatial Analysis Agent")
    except ImportError as e:
        logger.warning(f"Could not load Spatial Analysis Agent: {e}")
        
    # Try to load the Sales Verification agent
    try:
        from mcp.agents.sales_verification_agent import SalesVerificationAgent
        mcp_instance.register_agent("sales_verification", SalesVerificationAgent())
        logger.info("Successfully loaded Sales Verification Agent")
    except ImportError as e:
        logger.warning(f"Could not load Sales Verification Agent: {e}")
        
    # Register a basic dummy agent to ensure the MCP dashboard works
    from mcp.agents.base_agent import BaseAgent
        
    class SystemAgent(BaseAgent):
        """Basic system agent for MCP functionality"""
        def __init__(self):
            super().__init__()
            self.capabilities = ["system_info", "dashboard_support"]
            
    # Register the API Gateway
    try:
        from api.gateway import register_api_endpoint_modules
        if register_api_endpoint_modules(app):
            logger.info("API Gateway registered successfully")
        else:
            logger.warning("API Gateway registration failed")
    except Exception as e:
        logger.warning(f"Could not load API Gateway modules: {str(e)}")
        
    # Initialize agent integrators
    try:
        from mcp.integrators import initialize_integrators
        integrators_count = initialize_integrators()
        if integrators_count > 0:
            logger.info(f"Successfully initialized {integrators_count} agent integrators")
        else:
            logger.warning("No agent integrators were initialized")
    except ImportError as e:
        logger.warning(f"Could not load agent integrators module: {e}")
    except Exception as e:
        logger.error(f"Error initializing agent integrators: {str(e)}")
        
    def process_task(self, task_data):
        """Process a system task"""
        self.last_activity = time.time()
        
        if not task_data or "task_type" not in task_data:
            return {"error": "Invalid task data, missing task_type"}
            
        task_type = task_data["task_type"]
        
        if task_type == "system_info":
            return {
                "status": "success",
                "system_info": {
                    "hostname": os.uname().nodename,
                    "platform": os.uname().sysname,
                    "python_version": sys.version,
                    "flask_version": "unknown",
                    "uptime": time.time()
                }
            }
        else:
            return {"error": f"Unsupported task type: {task_type}"}
    
    # Register the system agent
    mcp_instance.register_agent("system", SystemAgent())

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
        
        auth_result = authenticate_user(username, password)
        
        if auth_result:
            # Unpack user info if returned from LDAP
            if isinstance(auth_result, tuple):
                success, user_info = auth_result
                if not success:
                    flash('Authentication failed. Please check your credentials.', 'danger')
                    return render_template('login.html')
            else:
                # For bypass mode or other authentication methods
                user_info = {}
            
            # After successful authentication
            from models import User, Role
            from auth import map_ad_groups_to_roles
            user = User.query.filter_by(username=username).first()
            
            if not user:
                try:
                    # Create user if not exists
                    user = User(
                        username=username, 
                        email=user_info.get('email', f"{username}@co.benton.wa.us"),
                        full_name=user_info.get('full_name', ''),
                        department=user_info.get('department', ''),
                        ad_object_id=user_info.get('ad_object_id', None),
                        last_login=datetime.datetime.utcnow(),
                        active=True
                    )
                    db.session.add(user)
                    db.session.commit()
                    
                    # Map AD groups to roles if we have group membership info
                    if user_info and 'groups' in user_info:
                        map_ad_groups_to_roles(user, user_info['groups'])
                    else:
                        # For new users, add them to the 'readonly' role by default if no AD groups mapped
                        readonly_role = Role.query.filter_by(name='readonly').first()
                        if readonly_role:
                            user.roles.append(readonly_role)
                            db.session.commit()
                        
                    logger.info(f"Created new user: {username}")
                except Exception as e:
                    # Handle any errors during user creation
                    logger.error(f"Error creating user: {str(e)}")
                    db.session.rollback()
                    
                    # Try to find the user again (maybe it was created in another process)
                    user = User.query.filter_by(username=username).first()
                    if not user:
                        flash('Error creating user account. Please contact an administrator.', 'danger')
                        return render_template('login.html')
            else:
                try:
                    # Update user information from LDAP if available
                    if user_info:
                        if 'full_name' in user_info and user_info['full_name']:
                            user.full_name = user_info['full_name']
                        if 'email' in user_info and user_info['email']:
                            user.email = user_info['email']
                        if 'department' in user_info and user_info['department']:
                            user.department = user_info['department']
                        if 'ad_object_id' in user_info and user_info['ad_object_id']:
                            user.ad_object_id = user_info['ad_object_id']
                        
                        # Update role mapping on each login
                        if 'groups' in user_info:
                            map_ad_groups_to_roles(user, user_info['groups'])
                    
                    # Update last login time
                    user.last_login = datetime.datetime.utcnow()
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Error updating user: {str(e)}")
                    db.session.rollback()
            
            # Get user roles and permissions for the session
            user_roles = [role.name for role in user.roles]
            user_permissions = user.get_permissions()
            
            # Store user in session
            session['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'department': user.department,
                'roles': user_roles,
                'permissions': user_permissions
            }
            
            # Log successful login
            logger.info(f"User {username} logged in successfully")
            next_page = request.args.get('next', url_for('index'))
            return redirect(next_page)
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
            
            # Index the file for RAG if it's a text file, PDF, XML or metadata
            if filename.endswith(('.txt', '.pdf', '.xml', '.dbf', '.shp')):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(file_record.id), filename)
                try:
                    index_document(file_path, file_record.id, description)
                    logger.info(f"Indexed file {filename} for RAG search")
                except Exception as e:
                    logger.error(f"Error indexing file {filename} for RAG search: {str(e)}")
                
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

@app.route('/profile')
@login_required
def user_profile():
    """User profile page showing roles and permissions"""
    from models import User, Role, Permission, AuditLog, ApiToken
    import datetime
    
    user = User.query.get(session['user']['id'])
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('index'))
    
    # Get all available roles and permissions for display
    all_roles = Role.query.all()
    all_permissions = Permission.query.all()
    
    # Get audit logs for the user (limit to the most recent 20)
    audit_logs = AuditLog.query.filter_by(user_id=user.id).order_by(AuditLog.timestamp.desc()).limit(20).all()
    
    # Get API tokens for the user
    api_tokens = ApiToken.query.filter_by(user_id=user.id, revoked=False).all()
    
    # Current time for token status calculation
    now = datetime.datetime.utcnow()
    
    return render_template(
        'profile.html', 
        user=user, 
        all_roles=all_roles,
        all_permissions=all_permissions,
        audit_logs=audit_logs,
        api_tokens=api_tokens,
        now=now
    )

@app.route('/mcp-dashboard')
@login_required
def mcp_dashboard():
    """MCP system dashboard page"""
    return render_template('mcp_dashboard.html')

@app.route('/power-query')
@login_required
def power_query():
    """Power Query page for data integration and transformation"""
    return render_template('power_query.html')

@app.route('/api-tester')
@login_required
def api_tester():
    """API testing interface"""
    return render_template('api_tester.html')

@app.route('/api-test-setup')
@login_required
def api_test_setup():
    """Set up test data for API testing"""
    # Get test files already imported
    test_files = File.query.filter(
        File.user_id == session['user']['id'],
        File.description.like('%API testing%')
    ).all()
    
    return render_template('api_test_setup.html', test_files=test_files)

@app.route('/import-test-data', methods=['POST'])
@login_required
def import_test_data():
    """Import test GeoJSON data for API testing"""
    try:
        project_name = request.form.get('project_name', 'Test Project')
        description = request.form.get('description', 'Sample GeoJSON test data for API testing.')
        
        # Get the test GeoJSON file
        test_file_path = os.path.join(app.root_path, 'static', 'data', 'test_geo.geojson')
        
        if not os.path.exists(test_file_path):
            flash('Test data file not found', 'danger')
            return redirect(url_for('api_test_setup'))
        
        # Create the project
        project = GISProject.query.filter_by(name=project_name, user_id=session['user']['id']).first()
        if not project:
            project = GISProject(name=project_name, description=f"Project for {project_name}", user_id=session['user']['id'])
            db.session.add(project)
            db.session.commit()
            
        # Create uploads directory if it doesn't exist
        if 'UPLOAD_FOLDER' not in app.config:
            app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Create directory for the file
        uploads_dir = os.path.join(app.root_path, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        test_dir = os.path.join(uploads_dir, 'test_data')
        os.makedirs(test_dir, exist_ok=True)
        
        # Copy the file to the uploads directory
        filename = 'test_geo.geojson'
        destination_path = os.path.join(test_dir, filename)
        shutil.copy2(test_file_path, destination_path)
        
        # Create file record with the paths already set
        file_record = File(
            filename=filename,
            original_filename=filename,
            file_path=destination_path,
            file_size=os.path.getsize(destination_path),
            file_type='geojson',
            upload_date=datetime.datetime.now(),
            user_id=session['user']['id'],
            project_id=project.id,
            description=description
        )
        
        # Save the file record
        db.session.add(file_record)
        db.session.commit()
        
        # Extract and save metadata if it's a GIS file
        try:
            metadata = extract_gis_metadata(destination_path, file_record.file_type)
            if metadata:
                file_record.file_metadata = metadata
        except Exception as e:
            app.logger.error(f"Error extracting metadata: {str(e)}")
        
        db.session.commit()
        flash('Test data imported successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error importing test data: {str(e)}")
        flash(f'Error importing test data: {str(e)}', 'danger')
    
    return redirect(url_for('api_test_setup'))

@app.route('/upload-power-query-file', methods=['POST'])
@login_required
def upload_power_query_file():
    """Handle file uploads for Power Query data sources"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    source_name = request.form.get('source_name', '')
    description = request.form.get('description', '')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        # Create directory for Power Query files if it doesn't exist
        power_query_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'power_query')
        os.makedirs(power_query_dir, exist_ok=True)
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Save the file
        file_path = os.path.join(power_query_dir, filename)
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'file_path': file_path,
            'filename': filename
        })
    except Exception as e:
        logger.error(f"Error uploading Power Query file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-power-query-file')
@login_required
def download_power_query_file():
    """Download a Power Query export file"""
    filename = request.args.get('file')
    
    if not filename:
        flash('No file specified', 'danger')
        return redirect(url_for('power_query'))
    
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'power_query')
        return send_from_directory(file_path, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading Power Query file: {str(e)}")
        flash(f'Error downloading file: {str(e)}', 'danger')
        return redirect(url_for('power_query'))

@app.route('/api-direct')
def api_direct():
    """Direct API access (for testing)"""
    return jsonify({
        'name': 'Benton County Data Hub API',
        'version': '1.0.0',
        'status': 'active',
        'auth_required': True,
        'endpoints': {
            'docs': '/api/docs',
            'spatial': '/api/spatial/layers',
            'data': '/api/data/sources'
        }
    })

@app.route('/system/initialize-roles')
@login_required
def initialize_roles():
    """Initialize roles and permissions in the database"""
    try:
        from initialize_roles import main as init_roles
        init_roles()
        flash('Roles and permissions have been initialized successfully', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error initializing roles: {str(e)}")
        flash(f'Error initializing roles: {str(e)}', 'danger')
        return redirect(url_for('index'))

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
        
@app.route('/mcp/task', methods=['POST'])
@login_required
def mcp_task():
    """Handle MCP agent tasks"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400
            
        agent_id = data.get('agent_id')
        task_data = data.get('task_data', {})
        
        if not agent_id:
            return jsonify({'error': 'Missing agent_id parameter'}), 400
            
        # Get the agent
        from mcp.core import mcp_instance
        agent = mcp_instance.get_agent(agent_id)
        
        if not agent:
            return jsonify({'error': f'Agent not found: {agent_id}'}), 404
            
        # Submit the task
        result = agent.process_task(task_data)
        
        return jsonify({'result': result})
    except Exception as e:
        logger.error(f"MCP task error: {str(e)}")
        return jsonify({'error': f'MCP task error: {str(e)}'}), 500

# Register knowledge base blueprint
try:
    from knowledge_routes import knowledge_bp
    app.register_blueprint(knowledge_bp)
    app.logger.info("Knowledge base routes registered")
except Exception as e:
    app.logger.error(f"Error registering knowledge base routes: {str(e)}")

# Register valuation blueprint
try:
    from valuation_routes import valuation_bp
    app.register_blueprint(valuation_bp)
    app.logger.info("Valuation routes registered successfully")
except Exception as e:
    app.logger.error(f"Error registering valuation routes: {str(e)}")

# Register data quality blueprint
try:
    from data_quality_routes import data_quality_bp
    app.register_blueprint(data_quality_bp)
    app.logger.info("Data Quality routes registered successfully")
except Exception as e:
    app.logger.error(f"Error registering data quality routes: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
