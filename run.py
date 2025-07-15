#!/usr/bin/env python3
"""
Production runner for Equipment Inventory Management System
"""

import os
import sys

def main():
    """Main entry point for the Flask application"""
    try:
        # Set environment variables for production
        os.environ['FLASK_ENV'] = 'production'
        
        # Get port from environment variable (for deployment platforms)
        port = int(os.environ.get('PORT', 5000))
        
        print(f"Starting Equipment Inventory Management System...")
        print(f"Port: {port}")
        print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
        print(f"Database URL configured: {'DATABASE_URL' in os.environ}")
        print(f"Secret key configured: {'SECRET_KEY' in os.environ}")
        
        # Import app after setting environment variables
        from app import app
        
        if app is None:
            print("Failed to initialize Flask application")
            sys.exit(1)
            
        print("Application initialized successfully, starting server...")
        
        # Run the application
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        print(f"Failed to start application: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()