#!/usr/bin/env python3
"""
Production runner for Equipment Inventory Management System
"""

import os
from app import app

if __name__ == '__main__':
    # Get port from environment variable (for deployment platforms)
    port = int(os.environ.get('PORT', 5000))
    
    # Force production mode for deployment
    os.environ['FLASK_ENV'] = 'production'
    
    print(f"Starting Flask application on port {port}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=False)