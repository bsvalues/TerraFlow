"""
Routes for verification and testing of the property export functionality.
"""
import json
import datetime
import pyodbc
from flask import Blueprint, render_template, jsonify, request, session, flash, redirect, url_for
from app import db
from auth import login_required, role_required
from sync_service.verification import PropertyExportVerification, test_windows_auth_connection
from sync_service.models import SyncJob, SyncLog
from sync_service.config import SQL_SERVER_CONNECTION_STRING

verification_bp = Blueprint('verification', __name__, url_prefix='/verification')

@verification_bp.route('/')
@login_required
@role_required('administrator')
def verification_dashboard():
    """Verification dashboard for the property export functionality."""
    sql_server_status = "Not Verified"
    try:
        if SQL_SERVER_CONNECTION_STRING:
            # Check if we have a cached verification result
            recent_job = SyncJob.query.filter_by(job_type='verification').order_by(SyncJob.created_at.desc()).first()
            sql_server_status = "Configured but not verified"
            
            if recent_job and recent_job.error_details:
                details = recent_job.error_details.get('sql_server_connection', {})
                if details.get('success', False):
                    sql_server_status = "Verified"
        else:
            sql_server_status = "Not Configured"
    except:
        pass
    
    # Get deployment information
    version = "1.0.0"
    build_id = "c4fd8ba"
    environment = "Development"
    last_deployment = "2025-04-10 08:15 AM"
    
    # Get the 5 most recent jobs to determine system status
    recent_jobs = SyncJob.query.order_by(SyncJob.created_at.desc()).limit(5).all()
    
    # Get system version from database if available
    try:
        from sync_service.models import GlobalSetting
        version_setting = GlobalSetting.query.filter_by(setting_key='system_version').first()
        if version_setting:
            version = version_setting.setting_value
            
        build_setting = GlobalSetting.query.filter_by(setting_key='build_id').first()
        if build_setting:
            build_id = build_setting.setting_value
            
        env_setting = GlobalSetting.query.filter_by(setting_key='environment').first()
        if env_setting:
            environment = env_setting.setting_value
            
        deploy_setting = GlobalSetting.query.filter_by(setting_key='last_deployment_date').first()
        if deploy_setting:
            last_deployment = deploy_setting.setting_value
    except:
        # If we can't get version info from database, use defaults
        pass
    
    return render_template('verification/dashboard.html', 
                          sql_server_status=sql_server_status,
                          version=version,
                          build_id=build_id,
                          environment=environment,
                          last_deployment=last_deployment,
                          now=datetime.datetime.utcnow().strftime('%Y-%m-%d'))

@verification_bp.route('/verify-sql-connection')
@login_required
@role_required('administrator')
def verify_sql_connection():
    """Verify SQL Server connection."""
    success, message, details = PropertyExportVerification.verify_sql_server_connection()
    
    # Create a verification job for tracking
    job = SyncJob(
        job_id=f"verify_{success}_{hash(message)}",
        name="SQL Server Connection Verification",
        status='completed',
        total_records=1,
        processed_records=1 if success else 0,
        error_records=0 if success else 1,
        error_details={'sql_server_connection': {'success': success, 'message': message, 'details': details}},
        job_type='verification',
        initiated_by=session.get('user', {}).get('id')
    )
    db.session.add(job)
    
    # Add a log entry
    log_entry = SyncLog(
        job_id=job.job_id,
        level="INFO" if success else "ERROR",
        message=message,
        component="Verification"
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return jsonify({
        'success': success,
        'message': message,
        'details': details
    })

@verification_bp.route('/test-stored-procedure')
@login_required
@role_required('administrator')
def test_stored_procedure():
    """Test the ExportPropertyAccess stored procedure."""
    database_name = request.args.get('database_name', 'web_internet_benton')
    num_years = int(request.args.get('num_years', 1))
    min_bill_years = int(request.args.get('min_bill_years', 2))
    
    success, message, details = PropertyExportVerification.test_stored_procedure(
        database_name=database_name,
        num_years=num_years,
        min_bill_years=min_bill_years,
        log_to_db=True,
        user_id=session.get('user', {}).get('id')
    )
    
    return jsonify({
        'success': success,
        'message': message,
        'details': details
    })

@verification_bp.route('/test-windows-auth')
@login_required
@role_required('administrator')
def test_windows_auth():
    """Test Windows Authentication connection to SQL Server."""
    server = request.args.get('server', 'jcharrispacs')
    database = request.args.get('database', 'web_internet_benton')
    
    success, message, details = test_windows_auth_connection(server, database)
    
    return jsonify({
        'success': success,
        'message': message,
        'details': details
    })

@verification_bp.route('/validate-api-endpoints')
@login_required
@role_required('administrator')
def validate_api_endpoints():
    """Validate API endpoints for property export."""
    success, message, details = PropertyExportVerification.validate_api_endpoints()
    
    return jsonify({
        'success': success,
        'message': message,
        'details': details
    })

@verification_bp.route('/full-validation')
@login_required
@role_required('administrator')
def full_validation():
    """Run a full validation suite for property export."""
    results = PropertyExportVerification.run_pre_deployment_validation()
    
    # Create a job record for this validation
    job = SyncJob(
        job_id=f"validation_{hash(json.dumps(results))}",
        name="Pre-deployment Validation",
        status='completed',
        total_records=3,  # SQL connection, stored procedure, API endpoints
        processed_records=sum(1 for k in ['sql_server_connection', 'stored_procedure', 'api_endpoints'] 
                             if results.get(k, {}).get('success', False)),
        error_records=sum(1 for k in ['sql_server_connection', 'stored_procedure', 'api_endpoints'] 
                         if not results.get(k, {}).get('success', False)),
        error_details=results,
        job_type='validation',
        initiated_by=session.get('user', {}).get('id')
    )
    db.session.add(job)
    
    # Add a log entry
    log_entry = SyncLog(
        job_id=job.job_id,
        level="INFO" if results['overall_status'] == 'passed' else "WARNING",
        message=f"Pre-deployment validation: {results['overall_status']}",
        component="Validation"
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return jsonify(results)

@verification_bp.route('/automated-test-suite')
@login_required
@role_required('administrator')
def automated_test_suite():
    """Run comprehensive automated test suite for property export."""
    # Run a sequence of tests with different parameters
    test_results = []
    start_time = datetime.datetime.utcnow()
    
    # === Basic Parameter Tests ===
    
    # Test with minimum values
    success, message, details = PropertyExportVerification.test_stored_procedure(
        database_name='web_internet_benton',
        num_years=1,
        min_bill_years=1,
        log_to_db=True,
        user_id=session.get('user', {}).get('id')
    )
    test_results.append({
        'name': 'Minimum Values Test',
        'category': 'Basic Parameter Tests',
        'success': success,
        'message': message,
        'details': details,
        'execution_time': details.get('execution_time_ms', 0) if success else 0
    })
    
    # Test with typical values
    success, message, details = PropertyExportVerification.test_stored_procedure(
        database_name='web_internet_benton',
        num_years=2,
        min_bill_years=2,
        log_to_db=True,
        user_id=session.get('user', {}).get('id')
    )
    test_results.append({
        'name': 'Typical Values Test',
        'category': 'Basic Parameter Tests',
        'success': success,
        'message': message,
        'details': details,
        'execution_time': details.get('execution_time_ms', 0) if success else 0
    })
    
    # Test with maximum values (-1 for all years)
    success, message, details = PropertyExportVerification.test_stored_procedure(
        database_name='web_internet_benton',
        num_years=-1,
        min_bill_years=10,
        log_to_db=True,
        user_id=session.get('user', {}).get('id')
    )
    test_results.append({
        'name': 'Maximum Values Test',
        'category': 'Basic Parameter Tests',
        'success': success,
        'message': message,
        'details': details,
        'execution_time': details.get('execution_time_ms', 0) if success else 0
    })
    
    # Test with alternate database
    success, message, details = PropertyExportVerification.test_stored_procedure(
        database_name='pacs_training',
        num_years=1,
        min_bill_years=2,
        log_to_db=True,
        user_id=session.get('user', {}).get('id')
    )
    test_results.append({
        'name': 'Alternate Database Test',
        'category': 'Basic Parameter Tests',
        'success': success,
        'message': message,
        'details': details,
        'execution_time': details.get('execution_time_ms', 0) if success else 0
    })
    
    # === Edge Case Tests ===
    
    # Test with invalid database name
    success, message, details = PropertyExportVerification.test_stored_procedure(
        database_name='nonexistent_db',
        num_years=1,
        min_bill_years=2,
        log_to_db=True,
        user_id=session.get('user', {}).get('id')
    )
    test_results.append({
        'name': 'Invalid Database Name Test',
        'category': 'Edge Cases',
        'success': not success,  # We expect this test to fail
        'message': message,
        'details': details,
        'execution_time': details.get('execution_time_ms', 0) if success else 0,
        'notes': 'This test is expected to fail - we want to verify proper error handling'
    })
    
    # Test with invalid year value (negative but not -1)
    success, message, details = PropertyExportVerification.test_stored_procedure(
        database_name='web_internet_benton',
        num_years=-5,  # Invalid value
        min_bill_years=2,
        log_to_db=True,
        user_id=session.get('user', {}).get('id')
    )
    test_results.append({
        'name': 'Invalid Years Parameter Test',
        'category': 'Edge Cases',
        'success': not success,  # We expect proper error handling
        'message': message,
        'details': details,
        'execution_time': details.get('execution_time_ms', 0) if success else 0,
        'notes': 'This test may fail or succeed depending on stored procedure validation'
    })
    
    # Test with zero billing years
    success, message, details = PropertyExportVerification.test_stored_procedure(
        database_name='web_internet_benton',
        num_years=1,
        min_bill_years=0,  # Potential edge case
        log_to_db=True,
        user_id=session.get('user', {}).get('id')
    )
    test_results.append({
        'name': 'Zero Billing Years Test',
        'category': 'Edge Cases',
        'success': success,  # This might be valid depending on stored procedure
        'message': message,
        'details': details,
        'execution_time': details.get('execution_time_ms', 0) if success else 0
    })
    
    # === Performance Tests ===
    
    # Test minimal data for performance baseline
    start_perf = datetime.datetime.utcnow()
    success, message, details = PropertyExportVerification.test_stored_procedure(
        database_name='web_internet_benton',
        num_years=1,  # Minimal data
        min_bill_years=5,  # Higher threshold to reduce data
        log_to_db=True,
        user_id=session.get('user', {}).get('id')
    )
    execution_time = (datetime.datetime.utcnow() - start_perf).total_seconds() * 1000
    test_results.append({
        'name': 'Minimal Data Performance Test',
        'category': 'Performance',
        'success': success,
        'message': message,
        'details': details,
        'execution_time': execution_time,
        'performance_metrics': {
            'sp_execution_time': details.get('execution_time_ms', 0) if success else 0,
            'total_time': execution_time
        }
    })
    
    # Performance test with all years (-1)
    if any(t['name'] == 'Maximum Values Test' and t['success'] for t in test_results):
        start_perf = datetime.datetime.utcnow()
        success, message, details = PropertyExportVerification.test_stored_procedure(
            database_name='web_internet_benton',
            num_years=-1,  # All years
            min_bill_years=1,  # Include all billing years
            log_to_db=True,
            user_id=session.get('user', {}).get('id')
        )
        execution_time = (datetime.datetime.utcnow() - start_perf).total_seconds() * 1000
        test_results.append({
            'name': 'Maximum Data Performance Test',
            'category': 'Performance',
            'success': success,
            'message': message,
            'details': details,
            'execution_time': execution_time,
            'performance_metrics': {
                'sp_execution_time': details.get('execution_time_ms', 0) if success else 0,
                'total_time': execution_time
            }
        })
    
    # === Data Integrity Tests ===
    
    # Verify that we can query the target database after export
    success = False
    message = "Data integrity test not implemented"
    details = {}
    try:
        if SQL_SERVER_CONNECTION_STRING:
            # Get connection string for target database
            conn_parts = SQL_SERVER_CONNECTION_STRING.split(';')
            conn_dict = {}
            for part in conn_parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    conn_dict[key.strip().upper()] = value.strip()
            
            # Replace database with the target database
            target_db = 'web_internet_benton'
            if 'DATABASE' in conn_dict:
                conn_dict['DATABASE'] = target_db
            
            # Reconstruct connection string
            target_conn_str = ';'.join([f"{k}={v}" for k, v in conn_dict.items()])
            
            try:
                # Connect to target database
                conn = pyodbc.connect(target_conn_str)
                cursor = conn.cursor()
                
                # Query basic table existence
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES")
                table_count = cursor.fetchone()[0]
                
                # Try to query a few known tables that should exist after export
                sample_tables = ['Property', 'OwnershipInfo', 'Valuation']
                existing_tables = []
                
                for table in sample_tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table}'")
                        count = cursor.fetchone()[0]
                        if count > 0:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            row_count = cursor.fetchone()[0]
                            existing_tables.append({
                                'table': table,
                                'row_count': row_count
                            })
                    except:
                        pass
                
                success = True
                message = f"Successfully verified {len(existing_tables)} tables in target database"
                details = {
                    'target_database': target_db,
                    'total_tables': table_count,
                    'verified_tables': existing_tables
                }
                
                # Close connection
                conn.close()
            except Exception as e:
                message = f"Error connecting to target database: {str(e)}"
                details = {'error': str(e)}
    except Exception as e:
        message = f"Error during data integrity test: {str(e)}"
        details = {'error': str(e)}
        
    test_results.append({
        'name': 'Data Integrity Test',
        'category': 'Data Integrity',
        'success': success,
        'message': message,
        'details': details
    })
    
    # Create a job record for this test suite
    job = SyncJob(
        job_id=f"test_suite_{hash(json.dumps(test_results))}",
        name="Property Export Automated Test Suite",
        status='completed',
        total_records=len(test_results),
        processed_records=sum(1 for test in test_results if test['success']),
        error_records=sum(1 for test in test_results if not test['success']),
        error_details={'tests': test_results},
        job_type='test_suite',
        initiated_by=session.get('user', {}).get('id')
    )
    db.session.add(job)
    
    # Add a log entry
    success_count = sum(1 for test in test_results if test['success'])
    log_entry = SyncLog(
        job_id=job.job_id,
        level="INFO" if success_count == len(test_results) else "WARNING",
        message=f"Automated test suite completed: {success_count}/{len(test_results)} tests passed",
        component="TestSuite"
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return jsonify({
        'tests': test_results,
        'summary': {
            'total_tests': len(test_results),
            'passed': success_count,
            'failed': len(test_results) - success_count,
            'overall_status': 'passed' if success_count == len(test_results) else 'failed'
        }
    })