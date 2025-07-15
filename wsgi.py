#!/usr/bin/env python3
"""
WSGI entry point for production deployment
"""

import os
import sys

# Ensure production environment
os.environ['FLASK_ENV'] = 'production'

# Import the Flask application
from app import app

# For debugging in production logs
print(f"WSGI application loaded, Environment: {os.environ.get('FLASK_ENV')}")
print(f"Database configured: {'DATABASE_URL' in os.environ}")

# This is what Gunicorn will use
application = app

if __name__ == "__main__":
    # Fallback for direct execution
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)