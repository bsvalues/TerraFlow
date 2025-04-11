# CountyDataSync ETL Process

## Overview

The CountyDataSync ETL process has been enhanced with two major improvements:

1. **SQLite Database Export**: Instead of exporting data to CSV files, the system now exports data to SQLite databases for better performance and query capabilities.
2. **Incremental Updates**: The ETL process now supports incremental updates by only processing records that have changed since the last successful sync.

## Components

### SQLite Exporter

The `SQLiteExporter` class in `sqlite_export.py` provides functions for exporting data to SQLite databases:

- `create_and_load_stats_db(df_stats)`: Creates a SQLite database for statistics data
- `create_and_load_working_db(df_working)`: Creates a SQLite database for working data
- `append_to_working_db(df_working)`: Appends new records to an existing working database
- `append_to_stats_db(df_stats)`: Appends new records to an existing stats database
- `merge_with_working_db(df_working, key_columns)`: Merges records with an existing working database
- `merge_with_stats_db(df_stats, key_columns)`: Merges records with an existing stats database

### Incremental Sync Manager

The `IncrementalSyncManager` class in `incremental_sync.py` tracks the last sync timestamp and provides functions for incremental updates:

- `get_last_sync_time(table_name)`: Gets the timestamp of the last successful sync
- `update_sync_time(table_name, job_id)`: Updates the last sync timestamp
- `filter_changed_records(df, timestamp_column, table_name)`: Filters a DataFrame to include only records that changed since the last sync
- `get_changed_record_ids(df, timestamp_column, id_column, table_name)`: Gets a list of IDs for records that changed since the last sync
- `update_record_counts(inserted, updated, table_name)`: Updates record counts in the metadata
- `get_sync_statistics()`: Gets statistics about sync operations

### ETL Workflow

The `CountyDataSyncETL` class in `sync.py` implements the complete ETL workflow:

- `extract_data(source_connection, query, timestamp_column, table_name)`: Extracts data from the source database
- `transform_data(df, transformations)`: Applies transformations to the extracted data
- `load_stats_data(df, incremental, key_columns)`: Loads statistics data into a SQLite database
- `load_working_data(df, incremental, key_columns)`: Loads working data into a SQLite database
- `run_etl_workflow(...)`: Runs the complete ETL workflow

## Usage Example

```python
from sync_service.sync import CountyDataSyncETL

# Initialize the ETL workflow
etl = CountyDataSyncETL(export_dir='exports', sync_metadata_path='sync_metadata.json')
etl.set_job_id('my_job_id')

# Define queries
stats_query = "SELECT id, use_code, acres, assessed_value, updated_at FROM property_stats"
working_query = "SELECT id, owner, use_code, parcel_id, updated_at FROM property_working"

# Run the ETL workflow (incremental mode)
results = etl.run_etl_workflow(
    source_connection="postgresql://user:password@host/database",
    stats_query=stats_query,
    working_query=working_query,
    stats_timestamp_column='updated_at',
    working_timestamp_column='updated_at',
    stats_table_name='property_stats',
    working_table_name='property_working',
    stats_key_columns=['id'],
    working_key_columns=['id'],
    incremental=True
)

# Check results
if results['success']:
    print(f"ETL completed successfully. Processed {results['stats']['records_processed']} records.")
    print(f"Stats database: {results['stats_db_path']}")
    print(f"Working database: {results['working_db_path']}")
else:
    print(f"ETL failed with errors: {results['errors']}")
```

## Testing

The ETL process includes comprehensive unit and integration tests:

- `test_sqlite_export.py`: Tests the SQLite export functionality
- `test_incremental_sync.py`: Tests the incremental sync functionality
- `test_etl_workflow.py`: Tests the complete ETL workflow

To run all tests:

```
python -m unittest discover -s sync_service/tests
```

To run a specific test:

```
python -m unittest sync_service.tests.test_etl_workflow
```