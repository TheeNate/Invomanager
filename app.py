#!/usr/bin/env python3
"""
Equipment Inventory Management System - Web Application
Flask-based web interface for safety equipment tracking
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file, Response
from datetime import date, datetime
import os
from dotenv import load_dotenv
from database_postgres import DatabaseManager
from auth import MagicLinkAuth
from models import EquipmentStatus, InspectionResult, JobStatus, PaymentStatus
from utils.helpers import format_date, parse_date
from utils.validators import FormValidator
from pdf_export import EquipmentPDFExporter

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')




# Initialize database manager
db_manager = None
auth = None

def initialize_app():
    """Initialize database and authentication with proper error handling"""
    global db_manager, auth

    try:
        print("Initializing database connection...")
        db_manager = DatabaseManager()

        print("Setting up database tables...")
        db_manager.initialize_database()

        print("Initializing authentication system...")
        auth = MagicLinkAuth(db_manager)

        print("Application initialization completed successfully!")
        return True

    except Exception as e:
        print(f"Failed to initialize application: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Initialize the application
if not initialize_app():
    print("Application failed to start. Check database connection and environment variables.")
    import sys
    sys.exit(1)

@app.route('/')
@auth.require_auth
def index():
    """Main dashboard page"""
    try:
        # Get filters from query parameters
        status_filter = request.args.get('status', 'All')
        type_filter = request.args.get('type', 'All')
        search_term = request.args.get('search', '')

        # Get equipment list with inspection data in a single optimized query
        equipment_list = db_manager.get_equipment_list_with_inspections()

        # Apply filters
        if status_filter != 'All':
            equipment_list = [eq for eq in equipment_list if eq['status'] == status_filter]

        if type_filter != 'All':
            equipment_list = [eq for eq in equipment_list if eq['equipment_type'] == type_filter]

        if search_term:
            search_term = search_term.lower()
            equipment_list = [
                eq for eq in equipment_list
                if search_term in eq['equipment_id'].lower() or
                   search_term in (eq['name'] or '').lower() or
                   search_term in (eq['serial_number'] or '').lower() or
                   search_term in (eq['type_description'] or '').lower()
            ]

        # Get equipment types for filter dropdown
        equipment_types = db_manager.get_equipment_types()

        return render_template('index.html', 
                             equipment_list=equipment_list,
                             equipment_types=equipment_types,
                             current_filters={
                                 'status': status_filter,
                                 'type': type_filter,
                                 'search': search_term
                             })

    except Exception as e:
        flash(f'Error loading equipment list: {str(e)}', 'error')
        return render_template('index.html', 
                             equipment_list=[], 
                             equipment_types=[],
                             current_filters={
                                 'status': 'All',
                                 'type': 'All',
                                 'search': ''
                             })

@app.route('/auth/login', methods=['GET', 'POST'])
def auth_login():
    """Magic link login page"""
    print(f"Login route accessed: {request.method}")

    if auth.is_authenticated():
        print("User already authenticated, redirecting to index")
        return redirect(url_for('index'))

    if request.method == 'POST':
        print("POST request received")
        print(f"Form data: {request.form}")
        print(f"Content-Type: {request.content_type}")

        email = request.form.get('email', '').strip().lower()
        print(f"Email extracted: '{email}'")

        if not email:
            print("No email provided")
            flash('Please enter your email address.', 'error')
            return render_template('auth/login.html')

        try:
            # Generate magic link
            print(f"Generating magic link for {email}")
            magic_link = auth.generate_magic_link(email)
            print(f"Magic link generated: {magic_link}")

            # Send email
            print(f"Attempting to send email to {email}")
            email_result = auth.send_magic_link(email, magic_link)
            print(f"Email send result: {email_result}")

            if email_result:
                print(f"Email sent successfully to {email}")
                return render_template('auth/check_email.html', email=email)
            else:
                print(f"Failed to send email to {email}")
                flash('Failed to send email. Please try a real email address (test domains like example.com are not allowed).', 'error')

        except ValueError as ve:
            # Handle unauthorized email
            print(f"Unauthorized email attempt: {email}")
            flash('Access denied. This email is not authorized to use this system.', 'error')
        except Exception as e:
            print(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            flash('An error occurred. Please try again.', 'error')

    print("Rendering login template")
    return render_template('auth/login.html')

@app.route('/auth/verify')
def auth_verify():
    """Verify magic link token"""
    token = request.args.get('token')

    if not token:
        flash('Invalid or missing login token.', 'error')
        return redirect(url_for('auth_login'))

    # Verify token
    email = auth.verify_magic_link(token)

    if email:
        # Log in user
        auth.login_user(email)

        # Redirect to originally requested page or home
        next_url = session.pop('next_url', None)
        flash(f'Welcome! You are now logged in as {email}', 'success')
        return redirect(next_url or url_for('index'))
    else:
        flash('Invalid or expired login link. Please request a new one.', 'error')
        return redirect(url_for('auth_login'))

@app.route('/auth/logout')
def auth_logout():
    """Logout user"""
    auth.logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth_login'))

@app.route('/equipment/add', methods=['GET', 'POST'])
@auth.require_auth
def add_equipment():
    """Add new equipment"""
    if request.method == 'POST':
        try:
            # Check if this is batch mode
            batch_mode = request.form.get('batch_mode') == 'true'

            # Get common form data
            equipment_type = request.form.get('equipment_type')
            name = request.form.get('name', '').strip() or None
            date_added_to_inventory = parse_date(request.form.get('date_added_to_inventory', '').strip()) or date.today()
            date_put_in_service = parse_date(request.form.get('date_put_in_service', '').strip())

            if batch_mode:
                # Handle batch equipment creation
                batch_quantity = int(request.form.get('batch_quantity', 0))

                if batch_quantity < 2 or batch_quantity > 50:
                    flash('Batch quantity must be between 2 and 50.', 'error')
                    equipment_types = db_manager.get_equipment_types()
                    return render_template('add_equipment.html', 
                                         equipment_types=equipment_types,
                                         form_data=request.form)

                # Validate common fields
                if not equipment_type:
                    flash('Equipment type is required.', 'error')
                    equipment_types = db_manager.get_equipment_types()
                    return render_template('add_equipment.html', 
                                         equipment_types=equipment_types,
                                         form_data=request.form)

                # Create equipment for each serial number
                created_equipment = []
                for i in range(1, batch_quantity + 1):
                    serial_number = request.form.get(f'batch_serial_{i}', '').strip() or None

                    # Validate each item
                    errors = FormValidator.validate_equipment_form(
                        equipment_type, serial_number or '', date_added_to_inventory, date_put_in_service
                    )

                    if errors:
                        for error in errors:
                            flash(f'Item #{i}: {error}', 'error')
                        equipment_types = db_manager.get_equipment_types()
                        return render_template('add_equipment.html', 
                                             equipment_types=equipment_types,
                                             form_data=request.form)

                    # Add individual equipment
                    equipment_id = db_manager.add_equipment(
                        equipment_type, name, serial_number, date_added_to_inventory, date_put_in_service
                    )
                    created_equipment.append(equipment_id)

                flash(f'Successfully added {len(created_equipment)} pieces of equipment: {", ".join(created_equipment)}', 'success')
                return redirect(url_for('index'))

            else:
                # Handle single equipment creation
                serial_number = request.form.get('serial_number', '').strip() or None

                # Validate form
                errors = FormValidator.validate_equipment_form(
                    equipment_type, serial_number or '', date_added_to_inventory, date_put_in_service
                )

                if errors:
                    for error in errors:
                        flash(error, 'error')
                    equipment_types = db_manager.get_equipment_types()
                    return render_template('add_equipment.html', 
                                         equipment_types=equipment_types,
                                         form_data=request.form)

                # Add equipment
                equipment_id = db_manager.add_equipment(
                    equipment_type, name, serial_number, date_added_to_inventory, date_put_in_service
                )

                flash(f'Equipment {equipment_id} added successfully!', 'success')
                return redirect(url_for('index'))

        except Exception as e:
            flash(f'Error adding equipment: {str(e)}', 'error')

    # GET request - show form
    equipment_types = db_manager.get_equipment_types()
    return render_template('add_equipment.html', equipment_types=equipment_types)

@app.route('/equipment/<path:equipment_id>')
@auth.require_auth
def equipment_details(equipment_id):
    """Show equipment details"""
    try:
        equipment = db_manager.get_equipment_by_id(equipment_id)
        if not equipment:
            flash('Equipment not found', 'error')
            return redirect(url_for('index'))

        inspections = db_manager.get_equipment_inspections(equipment_id)

        return render_template('equipment_details.html', 
                             equipment=equipment,
                             inspections=inspections)

    except Exception as e:
        flash(f'Error loading equipment details: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/equipment/<path:equipment_id>/update_status', methods=['POST'])
@auth.require_auth
def update_equipment_status(equipment_id):
    """Update equipment status"""
    try:
        new_status = request.form.get('status')

        if new_status not in ['ACTIVE', 'RED_TAGGED', 'DESTROYED']:
            flash('Invalid status', 'error')
            return redirect(url_for('equipment_details', equipment_id=equipment_id))

        success = db_manager.update_equipment_status(equipment_id, new_status)

        if success:
            flash(f'Equipment status updated to {new_status}', 'success')
        else:
            flash('Failed to update equipment status', 'error')

        return redirect(url_for('equipment_details', equipment_id=equipment_id))

    except Exception as e:
        flash(f'Error updating equipment status: {str(e)}', 'error')
        return redirect(url_for('equipment_details', equipment_id=equipment_id))

@app.route('/equipment/<path:equipment_id>/update_service_date', methods=['POST'])
@auth.require_auth
def update_equipment_service_date(equipment_id):
    """Update equipment service date"""
    try:
        service_date_str = request.form.get('date_put_in_service')

        if not service_date_str:
            flash('Service date is required', 'error')
            return redirect(url_for('equipment_details', equipment_id=equipment_id))

        service_date = parse_date(service_date_str)
        if not service_date:
            flash('Invalid date format', 'error')
            return redirect(url_for('equipment_details', equipment_id=equipment_id))

        if db_manager.update_equipment_service_date(equipment_id, service_date):
            flash(f'Service date updated successfully for {equipment_id}', 'success')
        else:
            flash('Failed to update service date', 'error')

        return redirect(url_for('equipment_details', equipment_id=equipment_id))

    except Exception as e:
        flash(f'Error updating service date: {str(e)}', 'error')
        return redirect(url_for('equipment_details', equipment_id=equipment_id))

@app.route('/equipment/<path:equipment_id>/update_info', methods=['POST'])
@auth.require_auth
def update_equipment_info(equipment_id):
    """Update equipment information (name and serial number)"""
    try:
        name = request.form.get('name', '').strip() or None
        serial_number = request.form.get('serial_number', '').strip() or None

        if db_manager.update_equipment_info(equipment_id, name, serial_number):
            flash(f'Equipment information updated successfully for {equipment_id}', 'success')
        else:
            flash('Failed to update equipment information', 'error')

        return redirect(url_for('equipment_details', equipment_id=equipment_id))

    except Exception as e:
        flash(f'Error updating equipment information: {str(e)}', 'error')
        return redirect(url_for('equipment_details', equipment_id=equipment_id))

@app.route('/equipment/<path:equipment_id>/delete', methods=['POST'])
@auth.require_auth
def delete_equipment(equipment_id):
    """Delete equipment entry"""
    try:
        # Check if equipment exists
        equipment = db_manager.get_equipment_by_id(equipment_id)
        if not equipment:
            flash('Equipment not found', 'error')
            return redirect(url_for('index'))

        # Safety check - only allow deletion of equipment without inspections
        inspections = db_manager.get_equipment_inspections(equipment_id)
        if inspections:
            flash('Cannot delete equipment with inspection history. Set status to DESTROYED instead.', 'warning')
            return redirect(url_for('equipment_details', equipment_id=equipment_id))

        # Delete the equipment
        success = db_manager.delete_equipment(equipment_id)

        if success:
            flash(f'Equipment {equipment_id} has been permanently deleted', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to delete equipment', 'error')
            return redirect(url_for('equipment_details', equipment_id=equipment_id))

    except Exception as e:
        flash(f'Error deleting equipment: {str(e)}', 'error')
        return redirect(url_for('equipment_details', equipment_id=equipment_id))

@app.route('/inspection/add', methods=['GET', 'POST'])
@app.route('/inspection/add/<path:equipment_id>', methods=['GET', 'POST'])
@auth.require_auth
def add_inspection(equipment_id=None):
    """Add inspection record"""
    if request.method == 'POST':
        try:
            # Get form data
            selected_equipment_id = request.form.get('equipment_id') or equipment_id
            inspection_date = parse_date(request.form.get('inspection_date', '').strip())
            result = request.form.get('result')
            inspector_name = request.form.get('inspector_name', '').strip()
            notes = request.form.get('notes', '').strip() or None

            # Validate form
            errors = FormValidator.validate_inspection_form(
                selected_equipment_id, inspection_date, result, inspector_name, notes or ''
            )

            if errors:
                for error in errors:
                    flash(error, 'error')
                active_equipment = db_manager.get_equipment_list(status_filter='ACTIVE')
                return render_template('add_inspection.html', 
                                     active_equipment=active_equipment,
                                     selected_equipment_id=equipment_id,
                                     form_data=request.form)

            # Add inspection
            inspection_id = db_manager.add_inspection(
                selected_equipment_id, inspection_date, result, inspector_name, notes
            )

            if result == 'FAIL':
                flash(f'Inspection recorded. Equipment {selected_equipment_id} has been RED TAGGED due to failed inspection.', 'warning')
            else:
                flash(f'Inspection recorded successfully for equipment {selected_equipment_id}', 'success')

            return redirect(url_for('equipment_details', equipment_id=selected_equipment_id))

        except Exception as e:
            flash(f'Error adding inspection: {str(e)}', 'error')

    # GET request - show form
    try:
        # Get equipment that can be inspected (ACTIVE, IN_FIELD, WAREHOUSE)
        all_equipment = db_manager.get_equipment_list()
        inspectable_equipment = [eq for eq in all_equipment if eq.get('status') in ['ACTIVE', 'IN_FIELD', 'WAREHOUSE']]
        
        print(f"Debug: Found {len(inspectable_equipment)} inspectable equipment items")
        
        # Check specifically for /001 items
        type_001_items = [eq for eq in inspectable_equipment if eq.get('equipment_id', '').endswith('/001')]
        print(f"Debug: Found {len(type_001_items)} items ending with /001")
        for eq in type_001_items:
            print(f"Debug: /001 Item - ID: {eq.get('equipment_id')}, Status: {eq.get('status')}, Type: {eq.get('equipment_type')}")
        
        # Show first 10 items for debugging
        for i, eq in enumerate(inspectable_equipment[:10]):
            print(f"Debug: Equipment {i+1}: ID: {eq.get('equipment_id')}, Type: {eq.get('equipment_type')}, Status: {eq.get('status')}")
            
    except Exception as e:
        print(f"Error loading inspectable equipment: {e}")
        inspectable_equipment = []
    
    return render_template('add_inspection.html', 
                         active_equipment=inspectable_equipment,
                         selected_equipment_id=equipment_id,
                         today=date.today().strftime('%Y-%m-%d'))

@app.route('/equipment-types')
@auth.require_auth
def equipment_types():
    """Manage equipment types"""
    try:
        types = db_manager.get_equipment_types(active_only=False)
        return render_template('equipment_types.html', equipment_types=types)

    except Exception as e:
        flash(f'Error loading equipment types: {str(e)}', 'error')
        return render_template('equipment_types.html', equipment_types=[])

@app.route('/equipment-types/add', methods=['POST'])
@auth.require_auth
def add_equipment_type():
    """Add new equipment type"""
    try:
        type_code = request.form.get('type_code', '').strip().upper()
        description = request.form.get('description', '').strip()
        is_soft_goods = request.form.get('is_soft_goods') == 'on'
        lifespan_years = request.form.get('lifespan_years', '').strip()
        inspection_interval = int(request.form.get('inspection_interval', 6))

        # Convert lifespan to int if provided
        lifespan_years = int(lifespan_years) if lifespan_years else None

        # Validate
        errors = FormValidator.validate_equipment_type_form(
            type_code, description, is_soft_goods, lifespan_years, inspection_interval
        )

        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            success = db_manager.add_equipment_type(
                type_code, description, is_soft_goods, lifespan_years, inspection_interval
            )

            if success:
                flash(f'Equipment type {type_code} added successfully!', 'success')
            else:
                flash('Equipment type code already exists', 'error')

        return redirect(url_for('equipment_types'))

    except Exception as e:
        flash(f'Error adding equipment type: {str(e)}', 'error')
        return redirect(url_for('equipment_types'))

@app.route('/reports')
@auth.require_auth
def reports():
    """Reports dashboard"""
    try:
        # Get report data
        overdue_inspections = db_manager.get_overdue_inspections()
        red_tagged_equipment = db_manager.get_red_tagged_equipment()
        expiring_equipment = db_manager.get_expiring_soft_goods()

        # Get equipment statistics
        all_equipment = db_manager.get_equipment_list()
        stats = {
            'total': len(all_equipment),
            'active': len([eq for eq in all_equipment if eq['status'] == 'ACTIVE']),
            'red_tagged': len([eq for eq in all_equipment if eq['status'] == 'RED_TAGGED']),
            'destroyed': len([eq for eq in all_equipment if eq['status'] == 'DESTROYED'])
        }

        return render_template('reports.html',
                             overdue_inspections=overdue_inspections,
                             red_tagged_equipment=red_tagged_equipment,
                             expiring_equipment=expiring_equipment,
                             stats=stats)

    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'error')
        return render_template('reports.html',
                             overdue_inspections=[],
                             red_tagged_equipment=[],
                             expiring_equipment=[],
                             stats={'total': 0, 'active': 0, 'red_tagged': 0, 'destroyed': 0})

@app.route('/api/equipment/<path:equipment_id>')
@auth.require_auth
def api_equipment_details(equipment_id):
    """API endpoint for equipment details"""
    try:
        equipment = db_manager.get_equipment_by_id(equipment_id)
        if not equipment:
            return jsonify({'error': 'Equipment not found'}), 404

        # Convert dates to strings for JSON serialization
        for key, value in equipment.items():
            if isinstance(value, date):
                equipment[key] = value.strftime('%Y-%m-%d')

        return jsonify(equipment)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for deployment monitoring"""
    try:
        # Test database connection
        db_manager.get_equipment_types()
        return jsonify({
            'status': 'healthy',
            'service': 'Equipment Inventory Management System',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

# Template context processor to make auth available in templates
@app.context_processor
def inject_auth():
    return {
        'auth': auth,
        'session': session,
        'date': date
    }

# Template filters
@app.template_filter('date_format')
def date_format_filter(date_obj, format='%Y-%m-%d'):
    """Format date for templates"""
    if date_obj is None:
        return ''
    if isinstance(date_obj, str):
        return date_obj
    return date_obj.strftime(format)

@app.template_filter('status_color')
def status_color_filter(status):
    """Get Bootstrap color class for status"""
    colors = {
        'ACTIVE': 'success',
        'RED_TAGGED': 'danger', 
        'DESTROYED': 'secondary'
    }
    return colors.get(status, 'dark')

@app.template_filter('result_color')
def result_color_filter(result):
    """Get Bootstrap color class for inspection result"""
    colors = {
        'PASS': 'success',
        'FAIL': 'danger'
    }
    return colors.get(result, 'dark')

@app.template_filter('strptime')
def strptime_filter(date_string, format='%Y-%m-%d'):
    """Parse date string into datetime object for template use"""
    if not date_string:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(date_string, format)
    except:
        return None

@app.template_filter('add_years')
def add_years_filter(date_obj, years):
    """Add years to a date object"""
    if not date_obj or not years:
        return date_obj
    try:
        if isinstance(date_obj, str):
            from datetime import datetime
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        return date_obj.replace(year=date_obj.year + int(years))
    except:
        return date_obj

@app.template_filter('strftime')
def strftime_filter(date_obj, format='%Y-%m-%d'):
    """Format datetime object to string"""
    if not date_obj:
        return None
    try:
        return date_obj.strftime(format)
    except:
        return str(date_obj)

@app.route('/export/pdf/complete')
@auth.require_auth
def export_complete_inventory_pdf():
    """Export complete inventory as PDF"""
    try:
        # Get all equipment with inspection data optimized
        equipment_list = db_manager.get_equipment_list_with_inspections()

        # Generate PDF
        pdf_exporter = EquipmentPDFExporter()
        pdf_bytes = pdf_exporter.create_complete_inventory_pdf(equipment_list)

        # Create response
        response = Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=equipment_inventory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            }
        )
        return response

    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/export/pdf/selected', methods=['POST'])
@auth.require_auth
def export_selected_equipment_pdf():
    """Export selected equipment as PDF"""
    try:
        # Get selected equipment IDs from form
        selected_ids = request.form.getlist('selected_equipment')

        if not selected_ids:
            flash('No equipment selected for export', 'error')
            return redirect(url_for('index'))

        # Get all equipment with inspection data optimized
        equipment_list = db_manager.get_equipment_list_with_inspections()

        # Generate PDF
        pdf_exporter = EquipmentPDFExporter()
        pdf_bytes = pdf_exporter.create_selected_equipment_pdf(
            equipment_list, 
            selected_ids,
            f"Selected Equipment Report ({len(selected_ids)} items)"
        )

        # Create response
        response = Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=selected_equipment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            }
        )
        return response

    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/equipment/bulk_put_in_service', methods=['POST'])
@auth.require_auth
def bulk_put_in_service():
    """Put multiple equipment items in service"""
    try:
        # Get selected equipment IDs and service date from form
        selected_ids = request.form.getlist('selected_equipment')
        service_date_str = request.form.get('service_date')

        if not selected_ids:
            flash('No equipment selected', 'error')
            return redirect(url_for('index'))

        if not service_date_str:
            flash('Service date is required', 'error')
            return redirect(url_for('index'))

        service_date = parse_date(service_date_str)
        if not service_date:
            flash('Invalid date format', 'error')
            return redirect(url_for('index'))

        # Update service date for each selected equipment
        success_count = 0
        error_count = 0

        for equipment_id in selected_ids:
            if db_manager.update_equipment_service_date(equipment_id, service_date):
                success_count += 1
            else:
                error_count += 1

        # Show results
        if success_count > 0:
            flash(f'Successfully put {success_count} equipment item(s) in service', 'success')

        if error_count > 0:
            flash(f'Failed to update {error_count} equipment item(s)', 'error')

        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error updating service dates: {str(e)}', 'error')
        return redirect(url_for('index'))

# Jobs & Billing Routes
@app.route('/jobs')
@auth.require_auth
def jobs_dashboard():
    """Jobs & Billing Dashboard"""
    try:
        # Get filter from query params
        status_filter = request.args.get('status', 'All')
        
        # Get job statistics
        job_stats = db_manager.get_job_stats()
        
        # Get jobs list with filter
        jobs_list = db_manager.get_jobs_list(status_filter if status_filter != 'All' else None)
        
        return render_template('jobs_dashboard.html', 
                             jobs_list=jobs_list,
                             job_stats=job_stats,
                             current_filter=status_filter)
    
    except Exception as e:
        flash(f'Error loading jobs dashboard: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/jobs/add', methods=['GET', 'POST'])
@auth.require_auth
def add_job():
    """Add new job"""
    if request.method == 'POST':
        try:
            # Get form data
            customer_name = request.form.get('customer_name', '').strip()
            description = request.form.get('description', '').strip() or None
            projected_start_date = parse_date(request.form.get('projected_start_date', '').strip())
            projected_end_date = parse_date(request.form.get('projected_end_date', '').strip())
            location_city = request.form.get('location_city', '').strip() or None
            location_state = request.form.get('location_state', '').strip() or None
            job_title = request.form.get('job_title', '').strip() or None
            
            # Validate required fields
            if not customer_name:
                flash('Customer name is required', 'error')
                return render_template('add_job.html', form_data=request.form)
            
            # Validate dates
            if projected_start_date and projected_start_date < date.today():
                flash('Start date cannot be in the past', 'error')
                return render_template('add_job.html', form_data=request.form)
            
            if projected_end_date and projected_start_date and projected_end_date < projected_start_date:
                flash('End date must be after start date', 'error')
                return render_template('add_job.html', form_data=request.form)
            
            # Add job
            job_id = db_manager.add_job(
                customer_name=customer_name,
                description=description,
                projected_start_date=projected_start_date,
                projected_end_date=projected_end_date,
                location_city=location_city,
                location_state=location_state,
                job_title=job_title
            )
            
            flash(f'Job {job_id} created successfully', 'success')
            return redirect(url_for('job_details', job_id=job_id))
            
        except Exception as e:
            flash(f'Error creating job: {str(e)}', 'error')
            return render_template('add_job.html', form_data=request.form)
    
    # GET request - show form
    return render_template('add_job.html')

@app.route('/jobs/<job_id>')
@auth.require_auth
def job_details(job_id):
    """Job details page"""
    try:
        job = db_manager.get_job_by_id(job_id)
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('jobs_dashboard'))
        
        # Get equipment assigned to this job
        job_equipment = db_manager.get_job_equipment(job_id)
        
        return render_template('job_details.html', 
                             job=job,
                             job_equipment=job_equipment)
    
    except Exception as e:
        flash(f'Error loading job details: {str(e)}', 'error')
        return redirect(url_for('jobs_dashboard'))

@app.route('/jobs/<job_id>/edit', methods=['GET', 'POST'])
@auth.require_auth
def edit_job(job_id):
    """Edit job details"""
    if request.method == 'POST':
        try:
            # Get form data
            customer_name = request.form.get('customer_name', '').strip()
            description = request.form.get('description', '').strip() or None
            projected_start_date = parse_date(request.form.get('projected_start_date', '').strip())
            projected_end_date = parse_date(request.form.get('projected_end_date', '').strip())
            location_city = request.form.get('location_city', '').strip() or None
            location_state = request.form.get('location_state', '').strip() or None
            job_title = request.form.get('job_title', '').strip() or None
            status = request.form.get('status')
            
            # Billing data
            bid_amount = request.form.get('bid_amount', '').strip()
            actual_cost = request.form.get('actual_cost', '').strip()
            payment_status = request.form.get('payment_status')
            invoice_date = parse_date(request.form.get('invoice_date', '').strip())
            billing_notes = request.form.get('billing_notes', '').strip() or None
            
            # Validate required fields
            if not customer_name:
                flash('Customer name is required', 'error')
                job = db_manager.get_job_by_id(job_id)
                return render_template('edit_job.html', job=job, form_data=request.form)
            
            # Validate dates
            if projected_start_date and projected_start_date < date.today():
                flash('Start date cannot be in the past', 'error')
                job = db_manager.get_job_by_id(job_id)
                return render_template('edit_job.html', job=job, form_data=request.form)
            
            if projected_end_date and projected_start_date and projected_end_date < projected_start_date:
                flash('End date must be after start date', 'error')
                job = db_manager.get_job_by_id(job_id)
                return render_template('edit_job.html', job=job, form_data=request.form)
            
            # Update job
            success = db_manager.update_job(
                job_id=job_id,
                customer_name=customer_name,
                description=description,
                projected_start_date=projected_start_date,
                projected_end_date=projected_end_date,
                location_city=location_city,
                location_state=location_state,
                job_title=job_title,
                status=status
            )
            
            if success:
                # Process billing amounts
                from decimal import Decimal, InvalidOperation
                bid_decimal = None
                actual_decimal = None
                
                if bid_amount:
                    try:
                        bid_decimal = Decimal(bid_amount.replace('$', '').replace(',', ''))
                    except InvalidOperation:
                        pass
                
                if actual_cost:
                    try:
                        actual_decimal = Decimal(actual_cost.replace('$', '').replace(',', ''))
                    except InvalidOperation:
                        pass
                
                # Update billing
                db_manager.update_job_billing(
                    job_id=job_id,
                    bid_amount=bid_decimal,
                    actual_cost=actual_decimal,
                    payment_status=payment_status,
                    invoice_date=invoice_date,
                    notes=billing_notes
                )
                
                flash('Job updated successfully', 'success')
            else:
                flash('Failed to update job', 'error')
            
            return redirect(url_for('job_details', job_id=job_id))
            
        except Exception as e:
            flash(f'Error updating job: {str(e)}', 'error')
            job = db_manager.get_job_by_id(job_id)
            return render_template('edit_job.html', job=job, form_data=request.form)
    
    # GET request - show form
    try:
        job = db_manager.get_job_by_id(job_id)
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('jobs_dashboard'))
        
        return render_template('edit_job.html', job=job)
    
    except Exception as e:
        flash(f'Error loading job for editing: {str(e)}', 'error')
        return redirect(url_for('jobs_dashboard'))

@app.route('/equipment/assign_to_job', methods=['POST'])
@auth.require_auth
def assign_equipment_to_job():
    """Assign selected equipment to a job"""
    try:
        # Get selected equipment IDs and job ID from form
        selected_ids = request.form.getlist('selected_equipment')
        job_id = request.form.get('job_id')
        
        if not selected_ids:
            flash('No equipment selected', 'error')
            return redirect(url_for('index'))
        
        if not job_id:
            flash('No job selected', 'error')
            return redirect(url_for('index'))
        
        # Assign equipment to job
        success_count = db_manager.assign_equipment_to_job(selected_ids, job_id)
        
        if success_count > 0:
            flash(f'Successfully assigned {success_count} equipment item(s) to job {job_id}', 'success')
        
        if success_count < len(selected_ids):
            failed_count = len(selected_ids) - success_count
            flash(f'Failed to assign {failed_count} equipment item(s) (may already be assigned or have invalid status)', 'warning')
        
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error assigning equipment to job: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/jobs/<job_id>/equipment_pdf')
@auth.require_auth
def export_job_equipment_pdf(job_id):
    """Export job equipment to PDF"""
    try:
        # Get job details
        job = db_manager.get_job_by_id(job_id)
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('jobs_dashboard'))
        
        # Get job equipment
        job_equipment = db_manager.get_job_equipment(job_id)
        
        if not job_equipment:
            flash('No equipment assigned to this job', 'warning')
            return redirect(url_for('job_details', job_id=job_id))
        
        # Create PDF
        from pdf_export import EquipmentPDFExporter
        exporter = EquipmentPDFExporter()
        
        title = f"Equipment Report - Job {job['job_id']}"
        if job.get('customer_name'):
            title += f" - {job['customer_name']}"
        if job.get('job_title'):
            title += f" ({job['job_title']})"
        
        pdf_bytes = exporter.create_job_equipment_pdf(job, job_equipment, title)
        
        # Create response
        from flask import make_response
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="job_{job_id}_equipment_report.pdf"'
        
        return response
        
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('job_details', job_id=job_id))

@app.route('/jobs/<job_id>/return_equipment', methods=['POST'])
@auth.require_auth
def return_equipment_from_job(job_id):
    """Return selected equipment from a job"""
    try:
        # Get selected equipment IDs from form
        selected_ids = request.form.getlist('selected_equipment')
        
        if not selected_ids:
            flash('No equipment selected for return', 'error')
            return redirect(url_for('job_details', job_id=job_id))
        
        # Return equipment from job
        success_count = db_manager.return_equipment_from_job(selected_ids)
        
        if success_count > 0:
            flash(f'Successfully returned {success_count} equipment item(s) from job', 'success')
        
        if success_count < len(selected_ids):
            failed_count = len(selected_ids) - success_count
            flash(f'Failed to return {failed_count} equipment item(s)', 'warning')
        
        return redirect(url_for('job_details', job_id=job_id))
        
    except Exception as e:
        flash(f'Error returning equipment from job: {str(e)}', 'error')
        return redirect(url_for('job_details', job_id=job_id))

@app.route('/api/active_jobs')
@auth.require_auth
def api_active_jobs():
    """API endpoint to get active jobs for equipment assignment dropdown"""
    try:
        active_jobs = db_manager.get_active_jobs()
        return jsonify(active_jobs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Invoice Management Routes

@app.route('/invoice/create/<path:equipment_id>')
@auth.require_auth
def create_invoice(equipment_id):
    """Create new invoice form"""
    try:
        # Get equipment details
        equipment = db_manager.get_equipment_by_id(equipment_id)
        if not equipment:
            flash('Equipment not found', 'error')
            return redirect(url_for('index'))

        # Get job details if equipment is assigned to a job
        job = None
        if equipment.get('job_id'):
            job = db_manager.get_job_by_id(equipment['job_id'])

        return render_template('create_invoice.html', 
                             equipment=equipment,
                             job=job,
                             today=date.today().strftime('%Y-%m-%d'))

    except Exception as e:
        flash(f'Error loading invoice form: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/invoice/save', methods=['POST'])
@auth.require_auth
def save_invoice():
    """Save invoice with line items"""
    try:
        # Get form data
        equipment_id = request.form.get('equipment_id')
        job_number = request.form.get('job_number')
        invoice_date = request.form.get('invoice_date')
        tax_rate = float(request.form.get('tax_rate', 0))
        
        # Issued to data
        issued_to_data = {
            'name': request.form.get('issued_to_name'),
            'company': request.form.get('issued_to_company'),
            'address': request.form.get('issued_to_address')
        }
        
        # Pay to data
        pay_to_data = {
            'name': request.form.get('pay_to_name'),
            'company': request.form.get('pay_to_company'),
            'address': request.form.get('pay_to_address')
        }
        
        # Create invoice
        invoice_id = db_manager.create_invoice(
            equipment_id, job_number, issued_to_data, pay_to_data, 
            invoice_date
        )
        
        # Add line items
        line_descriptions = request.form.getlist('line_description[]')
        line_prices = request.form.getlist('line_price[]')
        line_quantities = request.form.getlist('line_quantity[]')
        
        for i, description in enumerate(line_descriptions):
            if description.strip():  # Only add non-empty line items
                unit_price = float(line_prices[i])
                quantity = int(line_quantities[i])
                db_manager.add_invoice_line_item(invoice_id, description, unit_price, quantity)
        
        # Update totals with tax (convert float to prevent decimal/float errors)
        db_manager.update_invoice_totals(invoice_id, float(tax_rate))
        
        # Update status if specified
        if request.form.get('action') == 'finalize':
            db_manager.update_invoice_status(invoice_id, 'SENT')
        
        flash('Invoice created successfully', 'success')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))
        
    except Exception as e:
        flash(f'Error saving invoice: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/invoice/<int:invoice_id>')
@auth.require_auth
def view_invoice(invoice_id):
    """View/print invoice"""
    try:
        invoice = db_manager.get_invoice_by_id(invoice_id)
        if not invoice:
            flash('Invoice not found', 'error')
            return redirect(url_for('invoices_list'))
        
        return render_template('view_invoice.html', invoice=invoice)
        
    except Exception as e:
        flash(f'Error loading invoice: {str(e)}', 'error')
        return redirect(url_for('invoices_list'))

@app.route('/invoice/<int:invoice_id>/pdf')
@auth.require_auth
def download_invoice_pdf(invoice_id):
    """Download invoice as PDF"""
    try:
        invoice = db_manager.get_invoice_by_id(invoice_id)
        if not invoice:
            flash('Invoice not found', 'error')
            return redirect(url_for('invoices_list'))
        
        from pdf_export import generate_invoice_pdf
        pdf_buffer = generate_invoice_pdf(invoice)
        
        filename = f"Invoice_{invoice['invoice_number']}.pdf"
        
        return Response(
            pdf_buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))

@app.route('/invoices')
@auth.require_auth
def invoices_list():
    """List all invoices"""
    try:
        status_filter = request.args.get('status')
        invoices = db_manager.get_invoices_list(status_filter)
        
        return render_template('invoices_list.html', 
                             invoices=invoices,
                             current_filter=status_filter,
                             today=date.today())
        
    except Exception as e:
        flash(f'Error loading invoices: {str(e)}', 'error')
        return render_template('invoices_list.html', 
                             invoices=[], 
                             current_filter=None,
                             today=date.today())

@app.route('/invoice/<int:invoice_id>/status', methods=['POST'])
@auth.require_auth
def update_invoice_status_route(invoice_id):
    """Update invoice status"""
    try:
        status = request.form.get('status')
        if db_manager.update_invoice_status(invoice_id, status):
            flash(f'Invoice status updated to {status}', 'success')
        else:
            flash('Error updating invoice status', 'error')
        
        return redirect(url_for('view_invoice', invoice_id=invoice_id))
        
    except Exception as e:
        flash(f'Error updating invoice status: {str(e)}', 'error')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))

@app.route('/invoice/<int:invoice_id>/delete', methods=['POST'])
@auth.require_auth
def delete_invoice_route(invoice_id):
    """Delete invoice"""
    try:
        if db_manager.delete_invoice(invoice_id):
            flash('Invoice deleted successfully', 'success')
        else:
            flash('Error deleting invoice', 'error')
        
        return redirect(url_for('invoices_list'))
        
    except Exception as e:
        flash(f'Error deleting invoice: {str(e)}', 'error')
        return redirect(url_for('invoices_list'))

if __name__ == '__main__':
    # Use production mode for deployment
    debug_mode = os.environ.get('FLASK_ENV', 'production') == 'development'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)