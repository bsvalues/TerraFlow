# Real-time Geospatial Anomaly Visualization Map

A powerful visualization tool that displays data anomalies on an interactive map, providing spatial context and real-time updates for property assessment data anomalies in Benton County.

## Overview

The Geospatial Anomaly Visualization Map provides a real-time visual representation of detected anomalies in property assessment data across Benton County. This tool helps assessors, data quality teams, and administrators quickly identify, analyze, and address data issues with full geographic context.

### Key Features

* **Real-time Anomaly Visualization**: View anomalies as they're detected, with instant map updates
* **Severity-Based Visualization**: Different colors represent severity levels (critical, high, medium, low)
* **Interactive Filtering**: Filter anomalies by type, severity, and time period
* **Detailed Anomaly Information**: Click on anomalies to view comprehensive details
* **Anomaly Statistics**: View summary statistics and trend charts
* **Clustered Markers**: Automatic clustering of nearby anomalies for cleaner visualization

## Setup and Installation

The anomaly visualization is fully integrated with the GeoAssessmentPro system and requires minimal setup:

### 1. Install Dependencies

The visualization uses PostgreSQL with PostGIS extension for geospatial support. These are already included in the main application dependencies.

### 2. Initialize the Visualization

Run the setup script to create necessary database tables and generate sample data:

```bash
python setup_anomaly_visualization.py
```

This script will:
- Create the required database tables (`parcels` and `data_anomaly`)
- Generate sample parcel data with geographic coordinates
- Generate sample anomalies for testing

### 3. Run the Application

Start the main Flask application with the anomaly visualization enabled:

```bash
python main.py
```

The anomaly map will be accessible at:
```
http://localhost:5000/visualizations/anomaly-map
```

### 4. (Optional) Generate Real-time Anomalies

To simulate real-time anomaly detection, run the real-time anomaly generator:

```bash
python generate_realtime_anomalies.py
```

This will continuously generate new anomalies at random intervals. Options:
- `--min-interval`: Minimum seconds between anomalies (default: 10)
- `--max-interval`: Maximum seconds between anomalies (default: 30)
- `--runtime`: Duration to run in seconds (default: continuous)

Example to generate anomalies every 5-15 seconds for 10 minutes:
```bash
python generate_realtime_anomalies.py --min-interval 5 --max-interval 15 --runtime 600
```

## Using the Visualization

### Navigation

- **Pan**: Click and drag the map
- **Zoom**: Use the mouse wheel or the zoom controls in the top-left corner
- **Reset View**: Click the "Home" button to return to the default view

### Filtering Anomalies

Use the control panel on the left to filter anomalies:

1. **Time Period**: Select the time range for anomalies to display
2. **Severity**: Check/uncheck severity levels to show or hide
3. **Anomaly Type**: Filter by specific anomaly types
4. **Update Map**: Click to apply the selected filters

### Viewing Anomaly Details

1. Click on any anomaly marker on the map
2. A popup will show basic information about the anomaly
3. Click "View Details" to see comprehensive information in the details panel

### Real-time Updates

- Toggle the "Enable Real-time Updates" switch to start or stop real-time updates
- New anomalies will automatically appear on the map as they're detected
- A notification will appear when new anomalies are added

## Integration with Data Stability Framework

The anomaly visualization is fully integrated with the Data Stability Framework:

1. **Anomaly Detection**: Visualizes anomalies detected by the framework's AI agents
2. **Data Classification**: Respects data classification levels when displaying information
3. **Security Controls**: Enforces access controls based on user permissions
4. **Audit Logging**: Records all interaction with sensitive data

## Technical Details

- **Frontend**: JavaScript with Leaflet.js for mapping, Chart.js for statistics
- **Backend**: Flask API endpoints that query the PostgreSQL database
- **Database**: PostgreSQL with PostGIS extension for geospatial data
- **Real-time Updates**: AJAX polling with configurable intervals

## Troubleshooting

### Map doesn't load or show anomalies

1. Check that the database tables are created:
   ```
   python -c "from app import db; print(db.session.execute('SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = \\'parcels\\')').scalar())"
   ```

2. Verify that parcel data exists:
   ```
   python -c "from app import db; print(db.session.execute('SELECT COUNT(*) FROM parcels').scalar())"
   ```

3. Verify that anomaly data exists:
   ```
   python -c "from app import db; print(db.session.execute('SELECT COUNT(*) FROM data_anomaly').scalar())"
   ```

4. If any of these return 0 or False, run the setup script again:
   ```
   python setup_anomaly_visualization.py
   ```

### Browser console errors

If you see JavaScript errors in the browser console:

1. Make sure all required JavaScript libraries are loaded
2. Check network requests for any failed API calls
3. Verify that the API endpoints return valid JSON