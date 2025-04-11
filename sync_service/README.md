# CountyDataSync ETL Process

## Overview

CountyDataSync is a comprehensive data synchronization and ETL (Extract, Transform, Load) solution designed for the Benton County GIS and Assessment systems. It provides robust capabilities for extracting data from various sources, transforming it as needed, and loading it into multiple output formats.

## Recent Enhancements

### Multi-Format Export System

The ETL process has been enhanced with a new multi-format export system that allows exporting data to multiple formats simultaneously:

- **SQLite databases**: Relational database files for complex data with query capabilities
- **CSV files**: Simple, universal tabular format compatible with Excel and other tools
- **JSON files**: Web-friendly format for structured data
- **GeoJSON files**: Specialized format for geospatial data

This enhancement provides greater flexibility and interoperability with various systems and applications.

### Key Features

1. **Simultaneous Export to Multiple Formats**:
   - Export datasets to any combination of supported formats in a single ETL run
   - Each format is optimized for its intended use case

2. **Incremental Updates**:
   - All formats support incremental updates for efficient processing
   - Reduces processing time and resource usage for large datasets

3. **Proper Timestamp Handling**:
   - Export files include timestamps in filenames
   - Symlinks to latest versions for easy access

4. **Enhanced Logging**:
   - Detailed logging of export operations
   - Better error reporting and troubleshooting

5. **Structured Results**:
   - Comprehensive results dictionary with paths to all exported files
   - Detailed statistics on processed records

### Architectural Components

1. **MultiFormatExporter**: Core class for handling exports to various formats
2. **SQLiteExporter**: Specialized class for SQLite databases (maintained for backward compatibility)
3. **IncrementalSyncManager**: Manages sync state and incremental updates
4. **CountyDataSyncETL**: Main ETL engine, enhanced with multi-format support

## Usage

### Basic Export

```python
from sync_service.sync import CountyDataSyncETL

etl = CountyDataSyncETL(export_dir='exports')
results = etl.run_etl_workflow(
    source_connection=db_connection,
    stats_query="SELECT * FROM statistics",
    working_query="SELECT * FROM operational_data",
    export_formats=['sqlite', 'csv', 'json']
)
```

### Using Exported Data

The ETL process returns a detailed results dictionary containing paths to all exported files:

```python
# Access SQLite database for complex queries
sqlite_path = results['stats_export_paths']['sqlite']
conn = sqlite3.connect(sqlite_path)
cursor = conn.cursor()
cursor.execute("SELECT * FROM stats_data WHERE stat_value > 100")

# Process CSV data with pandas
csv_path = results['stats_export_paths']['csv']
df = pd.read_csv(csv_path)
avg_value = df['stat_value'].mean()

# Use JSON data in web applications
json_path = results['stats_export_paths']['json']
with open(json_path, 'r') as f:
    data = json.load(f)
```

## Documentation

For detailed information, see the following resources:

- [Multi-Format Export Guide](./docs/multi_format_export_guide.md): Comprehensive guide to the export system
- [Examples](./examples/): Sample code demonstrating various use cases
- [Unit Tests](./tests/): Test cases showing expected behavior

## Getting Started

1. **Installation**: Ensure all required dependencies are installed
2. **Configuration**: Set up export directories and metadata paths
3. **Usage**: Import and use the CountyDataSyncETL class as shown in examples
4. **Testing**: Run unit tests to verify functionality

## Dependencies

- pandas: Data manipulation and analysis
- SQLite: Embedded database for data storage
- geopandas (optional): For working with geospatial data
- shapely (optional): For geometry operations