from app import db
from flask_login import UserMixin
import datetime
import uuid
import json

# Association table for role-permissions relationship
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

class Permission(db.Model):
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Permission {self.name}>'

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
                               backref=db.backref('roles', lazy=True))
    
    def __repr__(self):
        return f'<Role {self.name}>'

# Association table for user-roles relationship
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(128))
    department = db.Column(db.String(128))
    ad_object_id = db.Column(db.String(128))  # Azure AD Object ID
    mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_secret = db.Column(db.String(64))  # For TOTP MFA
    last_login = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    files = db.relationship('File', backref='owner', lazy='dynamic')
    projects = db.relationship('GISProject', backref='owner', lazy='dynamic')
    queries = db.relationship('QueryLog', backref='user', lazy='dynamic')
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                         backref=db.backref('users', lazy=True))
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission_name):
        """Check if user has a specific permission through any of their roles"""
        return any(permission.name == permission_name 
                  for role in self.roles 
                  for permission in role.permissions)
    
    def get_permissions(self):
        """Get all permissions for the user from all roles"""
        # Create a set to avoid duplicates
        permissions = set()
        for role in self.roles:
            for permission in role.permissions:
                permissions.add(permission.name)
        return list(permissions)
    
    def __repr__(self):
        return f'<User {self.username}>'

class ApiToken(db.Model):
    __tablename__ = 'api_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128))  # Optional name/description for the token
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_used_at = db.Column(db.DateTime)
    revoked = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('tokens', lazy='dynamic'))
    
    def is_valid(self):
        """Check if token is valid (not expired or revoked)"""
        now = datetime.datetime.utcnow()
        return not self.revoked and self.expires_at > now
    
    def __repr__(self):
        return f'<ApiToken {self.id}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(64), nullable=False)  # login, logout, api_access, etc.
    resource_type = db.Column(db.String(64))  # file, project, etc.
    resource_id = db.Column(db.Integer)  # ID of the resource being acted upon
    details = db.Column(db.JSON)  # Additional details about the action
    ip_address = db.Column(db.String(45))  # Supports IPv6
    user_agent = db.Column(db.String(256))
    
    # Relationships
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))
    
    def __repr__(self):
        return f'<AuditLog {self.action} by user_id={self.user_id}>'

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

# MFA class to store backup codes and configuration
class MFASetup(db.Model):
    __tablename__ = 'mfa_setup'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    backup_codes = db.Column(db.JSON)  # Store hashed backup codes
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('mfa_setup', uselist=False))
    
    def __repr__(self):
        return f'<MFASetup user_id={self.user_id}>'

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