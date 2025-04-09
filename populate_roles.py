"""
Role and Permission Population Script

This script sets up the initial roles and permissions for the Benton County
Data Hub application. It creates the following roles:
- administrator: Has all permissions
- assessor: County assessor staff with data modification permissions
- gis_analyst: GIS specialists with data visualization permissions
- it_staff: IT staff with system maintenance permissions
- readonly: Basic users with read-only access

Run this script when setting up a new environment or when roles need to be reset.
"""

import os
import sys
import datetime
from app import db, app
from models import Role, Permission, User

# Define all permissions
PERMISSIONS = [
    # File Management Permissions
    {'name': 'file_upload', 'description': 'Can upload files'},
    {'name': 'file_download', 'description': 'Can download files'},
    {'name': 'file_delete', 'description': 'Can delete files'},
    {'name': 'file_metadata_view', 'description': 'Can view file metadata'},
    {'name': 'file_metadata_edit', 'description': 'Can edit file metadata'},
    
    # Map Permissions
    {'name': 'map_view', 'description': 'Can view maps'},
    {'name': 'map_create', 'description': 'Can create maps'},
    {'name': 'map_export', 'description': 'Can export maps'},
    {'name': 'map_share', 'description': 'Can share maps with others'},
    
    # Search Permissions
    {'name': 'search_basic', 'description': 'Can perform basic searches'},
    {'name': 'search_advanced', 'description': 'Can perform advanced searches'},
    {'name': 'search_export', 'description': 'Can export search results'},
    
    # MCP Permissions
    {'name': 'mcp_task_submit', 'description': 'Can submit tasks to MCP agents'},
    {'name': 'mcp_agent_view', 'description': 'Can view MCP agent details'},
    {'name': 'mcp_agent_manage', 'description': 'Can manage MCP agents'},
    
    # Power Query Permissions
    {'name': 'power_query_run', 'description': 'Can run Power Queries'},
    {'name': 'power_query_create', 'description': 'Can create Power Queries'},
    {'name': 'power_query_save', 'description': 'Can save Power Queries'},
    {'name': 'power_query_export', 'description': 'Can export Power Query results'},
    
    # API Permissions
    {'name': 'api_access', 'description': 'Can access the API'},
    {'name': 'api_token_create', 'description': 'Can create API tokens'},
    {'name': 'api_token_revoke', 'description': 'Can revoke API tokens'},
    {'name': 'api_create_endpoint', 'description': 'Can create new API endpoints'},
    
    # User Management Permissions
    {'name': 'user_view', 'description': 'Can view user details'},
    {'name': 'user_create', 'description': 'Can create users'},
    {'name': 'user_edit', 'description': 'Can edit users'},
    {'name': 'user_delete', 'description': 'Can delete users'},
    {'name': 'role_assign', 'description': 'Can assign roles to users'},
    
    # System Permissions
    {'name': 'system_config', 'description': 'Can configure system settings'},
    {'name': 'system_logs', 'description': 'Can view system logs'},
    {'name': 'system_backup', 'description': 'Can perform system backups'},
    {'name': 'system_restore', 'description': 'Can restore system from backups'},
]

# Define roles and their permissions
ROLES = [
    {
        'name': 'administrator',
        'description': 'System administrator with full access',
        'permissions': [p['name'] for p in PERMISSIONS]  # All permissions
    },
    {
        'name': 'assessor',
        'description': 'County assessor staff with data editing privileges',
        'permissions': [
            'file_upload', 'file_download', 'file_delete', 'file_metadata_view', 'file_metadata_edit',
            'map_view', 'map_create', 'map_export', 'map_share',
            'search_basic', 'search_advanced', 'search_export',
            'power_query_run', 'power_query_create', 'power_query_save', 'power_query_export',
            'mcp_task_submit', 'mcp_agent_view',
            'api_access'
        ]
    },
    {
        'name': 'gis_analyst',
        'description': 'GIS specialist with analysis capabilities',
        'permissions': [
            'file_upload', 'file_download', 'file_metadata_view',
            'map_view', 'map_create', 'map_export',
            'search_basic', 'search_advanced', 'search_export',
            'power_query_run', 'power_query_create', 'power_query_export',
            'mcp_task_submit', 'mcp_agent_view',
            'api_access'
        ]
    },
    {
        'name': 'it_staff',
        'description': 'IT staff with system maintenance access',
        'permissions': [
            'file_download', 'file_metadata_view',
            'map_view',
            'search_basic',
            'mcp_agent_view',
            'system_logs', 'system_backup',
            'api_access'
        ]
    },
    {
        'name': 'readonly',
        'description': 'Basic user with read-only access',
        'permissions': [
            'file_download', 'file_metadata_view',
            'map_view',
            'search_basic',
            'mcp_agent_view',
            'api_access'
        ]
    }
]

def create_permissions():
    """Create all permissions in the database"""
    print("Creating permissions...")
    for perm_data in PERMISSIONS:
        # Check if permission already exists
        perm = Permission.query.filter_by(name=perm_data['name']).first()
        if not perm:
            perm = Permission(name=perm_data['name'], description=perm_data['description'])
            db.session.add(perm)
            print(f"Created permission: {perm_data['name']}")
    
    db.session.commit()
    print(f"Created {len(PERMISSIONS)} permissions")

def create_roles():
    """Create all roles with their permissions"""
    print("Creating roles...")
    for role_data in ROLES:
        # Check if role already exists
        role = Role.query.filter_by(name=role_data['name']).first()
        if not role:
            role = Role(name=role_data['name'], description=role_data['description'])
            db.session.add(role)
            db.session.flush()  # Flush to get the role ID
            
        # Assign permissions to the role
        for perm_name in role_data['permissions']:
            perm = Permission.query.filter_by(name=perm_name).first()
            if perm and perm not in role.permissions:
                role.permissions.append(perm)
        
        print(f"Created/updated role: {role_data['name']} with {len(role_data['permissions'])} permissions")
    
    db.session.commit()
    print(f"Created {len(ROLES)} roles")

def create_admin_user():
    """Create an admin user if none exists"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        print("Creating admin user...")
        admin = User(
            username='admin',
            email='admin@co.benton.wa.us',
            full_name='System Administrator',
            department='IT Department',
            last_login=datetime.datetime.utcnow(),
            active=True
        )
        db.session.add(admin)
        db.session.flush()
        
        # Assign administrator role
        admin_role = Role.query.filter_by(name='administrator').first()
        if admin_role:
            admin.roles.append(admin_role)
            print(f"Assigned administrator role to admin user")
        
        db.session.commit()
        print("Admin user created successfully")
    else:
        print("Admin user already exists")
        
    # Create dev_user for testing
    dev_user = User.query.filter_by(username='dev_user').first()
    if not dev_user:
        print("Creating development test user...")
        dev_user = User(
            username='dev_user',
            email='dev@co.benton.wa.us',
            full_name='Development Test User',
            department='Development',
            last_login=datetime.datetime.utcnow(),
            active=True
        )
        db.session.add(dev_user)
        db.session.flush()
        
        # Assign administrator role
        admin_role = Role.query.filter_by(name='administrator').first()
        if admin_role:
            dev_user.roles.append(admin_role)
            print(f"Assigned administrator role to dev_user")
        
        db.session.commit()
        print("Development test user created successfully")
    else:
        print("Development test user already exists")

def main():
    """Main function to set up roles and permissions"""
    with app.app_context():
        print("Setting up roles and permissions...")
        create_permissions()
        create_roles()
        create_admin_user()
        print("Setup completed successfully")

if __name__ == '__main__':
    main()