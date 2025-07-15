#!/usr/bin/env python3
"""
Production server starter using Gunicorn
"""

import os
import subprocess
import sys

def start_gunicorn():
    """Start the application using Gunicorn"""
    port = os.environ.get('PORT', '5000')
    workers = os.environ.get('WEB_CONCURRENCY', '1')
    
    cmd = [
        'gunicorn',
        '--bind', f'0.0.0.0:{port}',
        '--workers', workers,
        '--timeout', '30',
        '--keep-alive', '2',
        '--max-requests', '1000',
        '--max-requests-jitter', '50',
        '--log-level', 'info',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'app:app'
    ]
    
    print(f"Starting Gunicorn server on port {port} with {workers} workers")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to start Gunicorn: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Server stopped by user")
        sys.exit(0)

if __name__ == '__main__':
    start_gunicorn()