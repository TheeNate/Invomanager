#!/usr/bin/env python3
"""
Equipment Inventory Management System - Web Application
Flask-based web interface for safety equipment tracking
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import date, datetime
import os
from dotenv import load_dotenv
from database_postgres import DatabaseManager
from auth import MagicLinkAuth
from models import EquipmentStatus, InspectionResult
from utils.helpers import format_date, parse_date
from utils.validators import FormValidator

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
        
        # Get equipment list with filters
        equipment_list = db_manager.get_equipment_list()
        
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
        
        # Add last inspection info to equipment
        for equipment in equipment_list:
            last_inspection = db_manager.get_last_inspection(equipment['equipment_id'])
            equipment['last_inspection'] = last_inspection
        
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
            purchase_date = parse_date(request.form.get('purchase_date', '').strip())
            first_use_date = parse_date(request.form.get('first_use_date', '').strip())
            
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
                        equipment_type, serial_number or '', purchase_date, first_use_date
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
                        equipment_type, name, serial_number, purchase_date, first_use_date
                    )
                    created_equipment.append(equipment_id)
                
                flash(f'Successfully added {len(created_equipment)} pieces of equipment: {", ".join(created_equipment)}', 'success')
                return redirect(url_for('index'))
            
            else:
                # Handle single equipment creation
                serial_number = request.form.get('serial_number', '').strip() or None
                
                # Validate form
                errors = FormValidator.validate_equipment_form(
                    equipment_type, serial_number or '', purchase_date, first_use_date
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
                    equipment_type, name, serial_number, purchase_date, first_use_date
                )
                
                flash(f'Equipment {equipment_id} added successfully!', 'success')
                return redirect(url_for('index'))
        
        except Exception as e:
            flash(f'Error adding equipment: {str(e)}', 'error')
    
    # GET request - show form
    equipment_types = db_manager.get_equipment_types()
    return render_template('add_equipment.html', equipment_types=equipment_types)

@app.route('/equipment/<equipment_id>')
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

@app.route('/equipment/<equipment_id>/update_status', methods=['POST'])
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

@app.route('/equipment/<equipment_id>/delete', methods=['POST'])
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
@app.route('/inspection/add/<equipment_id>', methods=['GET', 'POST'])
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
    active_equipment = db_manager.get_equipment_list(status_filter='ACTIVE')
    return render_template('add_inspection.html', 
                         active_equipment=active_equipment,
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

@app.route('/api/equipment/<equipment_id>')
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
        'session': session
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

if __name__ == '__main__':
    # Use production mode for deployment
    debug_mode = os.environ.get('FLASK_ENV', 'production') == 'development'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)