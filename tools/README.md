# GeoAssessmentPro Data Synchronization Tools

This directory contains tools for synchronizing data from a SQL Server database to the Supabase PostgreSQL database used by GeoAssessmentPro.

## Overview

The synchronization system provides:

- Full and incremental data migration from SQL Server to Supabase
- Automated change detection and synchronization
- Transaction tracking for rollback capability
- Comprehensive logging and notification system
- Dry-run mode for testing changes without applying them

## Installation

Before using these tools, ensure you have the required Python packages installed:

```bash
pip install supabase pyodbc colorama requests
```

## Configuration

### Create a Configuration File

Use the `configure_sync.py` tool to create a configuration file:

```bash
python configure_sync.py --create-config sync_config.json
```

This interactive tool will prompt you for:
- SQL Server connection details
- Supabase credentials
- Synchronization options
- Table mappings (using template as a starting point)

### Test Your Configuration

After creating a configuration file, test the connections:

```bash
python configure_sync.py --test-connection sync_config.json
```

This will verify:
- SQL Server connection and table access
- Supabase connection and table access
- Configuration structure validity

## Data Migration

### One-time Migration

To perform a one-time migration:

```bash
# For a full migration
python run_sync.py --config sync_config.json --full

# For an incremental migration
python run_sync.py --config sync_config.json --incremental

# To test without making changes (dry run)
python run_sync.py --config sync_config.json --dry-run
```

### Continuous Synchronization Service

To run a continuous synchronization service:

```bash
python run_sync_service.py --config sync_config.json
```

This will:
- Monitor the SQL Server database for changes
- Synchronize changes to Supabase according to your configuration
- Send notifications on successful or failed synchronization
- Run as a daemon process

## Data Migrator Tool

For more advanced migration needs, use the `data_migrator.py` tool directly:

```bash
# Generate a template configuration
python data_migrator.py --create-template migration_config.json

# Run a migration with a configuration file
python data_migrator.py --config migration_config.json
```

The data migrator supports various source types:
- SQL Server (with incremental sync)
- PostgreSQL
- SQLite
- CSV files
- JSON files

## Deployment Agent Integration

The `sync_agent.py` module is designed to be integrated with the GeoAssessmentPro Deployment Agent. When deployed, the synchronization service can be:

- Started automatically after application deployment
- Monitored for health and status
- Controlled via RESTful API endpoints
- Integrated with other service agents

## Troubleshooting

### Common Issues

1. **Connection Failures**:
   - Verify network connectivity
   - Check credentials and permissions
   - Ensure firewall rules allow the connection

2. **Missing Tables**:
   - Verify table names and case sensitivity
   - Check if the user has permissions to access the tables
   - For SQL Server, check if schema is needed (e.g., `dbo.TableName`)

3. **Synchronization Errors**:
   - Check the logs for detailed error messages
   - Try running with `--dry-run` to preview changes
   - Verify field mappings match actual database fields

### Logs

Logs are stored in:
- `sync_agent.log` - For sync agent logs
- `sync_service.log` - For sync service logs
- `data_migration.log` - For detailed migration logs

## Advanced Configuration

### Schema Management

For database schema versions and migrations:

1. Create a baseline migration first
2. Use incremental sync for ongoing changes
3. Consider using the rollback capability for failed migrations

### Notification Setup

The sync agent supports multiple notification channels:

- Email (via SMTP)
- Webhooks (HTTP callbacks)
- Logging (file and console)

To configure notifications, update the `notifications` section in your configuration file.

### Security Considerations

- Store SQL Server and Supabase credentials securely
- Use service accounts with minimal permissions
- Consider encrypting sensitive configuration values
- Use SSL for database connections where possible