"""
Routes for verification and testing of the property export functionality.
"""
import json
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
    
    return render_template('verification/dashboard.html', 
                          sql_server_status=sql_server_status)

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
    """Run automated test suite for property export."""
    # Run a sequence of tests with different parameters
    test_results = []
    
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
        'success': success,
        'message': message,
        'details': details
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
        'success': success,
        'message': message,
        'details': details
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
        'success': success,
        'message': message,
        'details': details
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