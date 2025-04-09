from app import db
from flask_login import UserMixin
import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(128))
    department = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    files = db.relationship('File', backref='owner', lazy='dynamic')
    projects = db.relationship('GISProject', backref='owner', lazy='dynamic')
    queries = db.relationship('QueryLog', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'

class File(db.Model):
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    file_type = db.Column(db.String(64))  # MIME type or file extension
    upload_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    description = db.Column(db.Text)
    file_metadata = db.Column(db.JSON)  # For storing extracted metadata
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('gis_projects.id'))
    
    def __repr__(self):
        return f'<File {self.filename}>'

class GISProject(db.Model):
    __tablename__ = 'gis_projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    files = db.relationship('File', backref='project', lazy='dynamic')
    
    def __repr__(self):
        return f'<GISProject {self.name}>'

class QueryLog(db.Model):
    __tablename__ = 'query_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    response = db.Column(db.Text)
    processing_time = db.Column(db.Float)  # In seconds
    
    def __repr__(self):
        return f'<QueryLog {self.query[:30]}>'

# Association table for tracking which documents have been indexed for RAG
class IndexedDocument(db.Model):
    __tablename__ = 'indexed_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False)
    index_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    chunk_count = db.Column(db.Integer, default=0)  # Number of chunks indexed
    status = db.Column(db.String(32), default='indexed')  # indexed, failed, pending
    
    # Relationship
    file = db.relationship('File', backref=db.backref('index_info', uselist=False))
    
    def __repr__(self):
        return f'<IndexedDocument file_id={self.file_id}>'
