# Supabase Migration Guide

This document provides guidance for migrating from a traditional database setup to Supabase.

## Overview

The migration process involves:

1. Setting up Supabase project
2. Configuring database schema
3. Migrating authentication
4. Migrating file storage
5. Testing and validation
6. Production deployment

## Setting Up Supabase Project

### Create a New Project

1. Sign up for Supabase at [https://supabase.io](https://supabase.io)
2. Create a new project with a suitable name (e.g., `benton-county-gis`)
3. Choose a region closest to your primary user base
4. Set a secure password for the PostgreSQL database

### Get API Credentials

From your project dashboard:

1. Go to Project Settings > API
2. Note the Project URL and API Key (anon public)
3. Also save the Service Role key for administrative operations

## Database Migration

### Schema Setup

The database schema should match the SQLAlchemy models defined in our application. You can generate SQL scripts from our existing models:

```python
from app import app, db
from models import *  # Import all models

def generate_create_tables_sql():
    """Generate SQL to create all tables."""
    with app.app_context():
        return str(db.metadata.create_all(bind=db.engine, checkfirst=False))

if __name__ == "__main__":
    print(generate_create_tables_sql())
```

Execute this script to generate SQL, then run it in the Supabase SQL Editor.

### Enable PostGIS Extension

For GIS functionality, you need to enable the PostGIS extension:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

### Data Migration

For data migration, you can use a simple Python script:

```python
import json
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from app import app, db
from models import *  # Import all models

load_dotenv()

# Source database (SQLite or existing PostgreSQL)
SOURCE_DB_URI = os.getenv("SOURCE_DATABASE_URL")
source_engine = create_engine(SOURCE_DB_URI)

# Target Supabase database
SUPABASE_DB_URI = os.getenv("SUPABASE_DB_URL")
target_engine = create_engine(SUPABASE_DB_URI)

# Get all models
model_classes = [cls for cls in locals().values() 
                if isinstance(cls, type) and 
                   issubclass(cls, db.Model) and 
                   cls != db.Model]

def migrate_model(model_class):
    """Migrate a single model."""
    print(f"Migrating {model_class.__name__}...")
    
    with source_engine.connect() as source_conn:
        # Get all records
        query = f"SELECT * FROM {model_class.__tablename__}"
        results = source_conn.execute(text(query))
        
        # Convert to list of dicts
        records = []
        columns = results.keys()
        for row in results:
            record = dict(zip(columns, row))
            records.append(record)
        
        print(f"  Found {len(records)} records")
        
        # Insert into target
        if records:
            with target_engine.connect() as target_conn:
                for record in records:
                    # Handle special data types
                    for key, value in record.items():
                        if isinstance(value, dict) or isinstance(value, list):
                            record[key] = json.dumps(value)
                    
                    # Create INSERT statement
                    columns_str = ', '.join(record.keys())
                    placeholders = ', '.join([f':{col}' for col in record.keys()])
                    
                    insert_query = f"""
                    INSERT INTO {model_class.__tablename__} ({columns_str})
                    VALUES ({placeholders})
                    """
                    
                    target_conn.execute(text(insert_query), record)
                
                target_conn.commit()
        
        print(f"  Migration of {model_class.__name__} completed.")

# Run migration for each model
for model_class in model_classes:
    migrate_model(model_class)

print("Migration completed.")
```

## Authentication Migration

### User Migration

You will need to migrate existing users to Supabase Auth. This requires special handling for passwords and authentication methods.

1. Export users from your current system
2. Import users to Supabase using the Admin API

Example for migrating users:

```python
import os
import supabase
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
from models import User

load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service role key
client = supabase.create_client(supabase_url, supabase_key)

# Get all users from your database
users = User.query.all()

for user in users:
    # Create user in Supabase Auth
    # Note: This requires using the service role key
    response = client.auth.admin.create_user({
        'email': user.email,
        'email_confirm': True,
        'password': 'temporary_password',  # Set a temporary password
        'user_metadata': {
            'full_name': user.full_name,
            'department': user.department,
            'migrated_from_legacy': True
        }
    })
    
    print(f"Migrated user: {user.email}")
    
    # Note: Passwords can't be migrated directly due to hashing incompatibility
    # Users will need to reset their passwords
```

### Authentication Flow Adjustment

Update the authentication flow in `auth.py` to work with Supabase Auth:

```python
def authenticate_user(username, password):
    """Authenticate user using various methods."""
    if is_supabase_enabled():
        return _authenticate_supabase(username, password)
    else:
        # Try LDAP or other authentication methods
        return _authenticate_ldap(username, password)
```

## File Storage Migration

### Create Storage Buckets

In your Supabase project, create storage buckets for your file categories:

1. Go to the Storage section in your Supabase dashboard
2. Create buckets for each file category (e.g., `documents`, `maps`, `images`)
3. Set the appropriate access policies

### File Migration

Create a script to migrate files from local storage to Supabase Storage:

```python
import os
import supabase
from dotenv import load_dotenv
from models import File

load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
client = supabase.create_client(supabase_url, supabase_key)

# Get all files from your database
files = File.query.all()

for file in files:
    # Determine appropriate bucket
    bucket_name = "documents"  # Default
    if file.file_type:
        if file.file_type.startswith("image/"):
            bucket_name = "images"
        elif file.file_type.endswith("geojson") or file.file_type.endswith("shapefile"):
            bucket_name = "maps"
    
    # Read the file from local storage
    file_path = os.path.join("local_storage", file.file_path)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            file_content = f.read()
            
            # Upload to Supabase
            supabase_path = f"{file.user_id}/{file.filename}"
            response = client.storage.from_(bucket_name).upload(
                supabase_path, 
                file_content
            )
            
            # Update the file record with new path
            file.file_path = f"supabase://{bucket_name}/{supabase_path}"
            db.session.commit()
            
            print(f"Migrated file: {file.filename}")
    else:
        print(f"Warning: File not found: {file_path}")
```

## Testing and Validation

### Test Authentication

Test the authentication flow with both existing and new users:

1. Ensure existing users can reset their passwords and log in
2. Verify new user registration works
3. Test LDAP authentication if configured as fallback

### Test File Access

Verify file storage and retrieval:

1. Test uploading new files
2. Test downloading existing files
3. Check file permissions

### Test API Integration

Verify API access with Supabase:

1. Test API endpoints
2. Verify connection management
3. Check performance and rate limits

## Production Deployment

### Update Configuration

For production, set the environment variables:

```bash
# Supabase configuration
export SUPABASE_URL=https://your-project-id.supabase.co
export SUPABASE_KEY=your-supabase-api-key
export SUPABASE_SERVICE_KEY=your-supabase-service-key

# Enable Supabase integration
export USE_SUPABASE=true
```

### Verify Backups

Ensure Supabase backups are configured:

1. Go to Project Settings > Database
2. Verify daily backups are enabled
3. Consider enabling Point-in-Time Recovery for production

### Monitor Performance

Set up monitoring for your Supabase project:

1. Go to Project Settings > API
2. Review API usage statistics
3. Set up alerts for unusual activity

## Rollback Plan

In case of issues, prepare a rollback plan:

1. Keep the original database running during the migration period
2. Create dual-write functionality for critical operations
3. Maintain the ability to switch back to the original database

## Post-Migration

After successful migration:

1. Update documentation
2. Train administrators on the new system
3. Set up proper access controls
4. Consider optimization for improved performance