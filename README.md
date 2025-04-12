# Benton County GIS System

A comprehensive Geographic Information System (GIS) for the Benton County Assessor's Office, featuring data quality management, validation capabilities, and integration with Supabase.

## Overview

This system provides a sophisticated platform for managing Geographic Information System (GIS) data with enhanced data quality management and validation capabilities. The application supports both local database storage and Supabase integration, providing flexibility for different deployment scenarios.

## Features

- Python-based backend with Flask
- PostgreSQL GIS database integration
- Advanced data quality monitoring
- Machine learning property assessment
- Interactive data visualization
- Comprehensive regional property knowledge base
- Secure authentication (LDAP and Supabase)
- API for third-party applications and microservices

## Setting Up Supabase Integration

### Prerequisites

1. Create a Supabase account at [https://supabase.io](https://supabase.io)
2. Create a new Supabase project
3. Get your Supabase URL and API key from the project settings

### Configuration

Set the following environment variables:

```bash
# Supabase configuration
export SUPABASE_URL=https://your-project-id.supabase.co
export SUPABASE_KEY=your-supabase-api-key

# Enable Supabase integration
export USE_SUPABASE=true
```

### Database Setup

The system will automatically create tables in Supabase based on the SQLAlchemy models. Additionally, ensure your Supabase project has the PostgreSQL extensions enabled for spatial data:

1. Go to your Supabase project dashboard
2. Select "Database" from the sidebar
3. Click on "Extensions"
4. Enable the following extensions:
   - `postgis`
   - `uuid-ossp`
   - `pg_stat_statements`

### Authentication Setup

To use Supabase for authentication:

1. Go to your Supabase project dashboard
2. Select "Authentication" from the sidebar
3. Configure the desired sign-in methods (email, OAuth providers, etc.)
4. Set the proper redirect URLs in the Authentication settings

For local development, set the redirect URL to `http://localhost:5000/auth/callback`.

## API Integration

The system provides a comprehensive API for third-party applications and microservices to interact with the Benton County GIS system. See the [API Documentation](api/README.md) for details.

## Connection Management

For microservices and third-party applications that need database access, the system provides a connection management facility to ensure proper connection pooling, load balancing, and security. See the [API Documentation](api/README.md) for details on integrating with this system.

## Storage Integration

The system supports both local file storage and Supabase Storage. When Supabase integration is enabled, all files will be stored in Supabase Storage buckets, providing:

- Automatic backup
- Enhanced security
- CDN delivery
- Easy access control

## Development

### Prerequisites

- Python 3.9+
- Flask
- PostgreSQL with PostGIS extensions
- SQLAlchemy
- Supabase Python client (for Supabase integration)

### Installation

```bash
# Clone the repository
git clone https://github.com/benton-county/gis-system.git
cd gis-system

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
flask db upgrade

# Start the development server
flask run
```

### Running Tests

```bash
# Run the test suite
pytest

# Run tests with coverage report
pytest --cov=app tests/
```

## Deployment

For production deployment, we recommend using Gunicorn with Nginx as a reverse proxy:

```bash
gunicorn --bind 0.0.0.0:5000 --worker-class gthread --workers 3 main:app
```

## License

Copyright © 2025 Benton County. All rights reserved.