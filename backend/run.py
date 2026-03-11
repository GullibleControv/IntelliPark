#!/usr/bin/env python3
"""
IntelliPark API Server

Run this file to start the Flask development server.
For production, use gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'

    print(f"""
    ========================================================
    |          IntelliPark API Server                      |
    ========================================================
    |  Running on: http://127.0.0.1:{port}                   |
    |  Debug mode: {str(debug):<5}                              |
    |                                                      |
    |  Endpoints:                                          |
    |    GET  /api/health         - Health check           |
    |    POST /api/auth/register  - Register user          |
    |    POST /api/auth/login     - Login                  |
    |    GET  /api/auth/me        - Get profile            |
    |    GET  /api/parking/spaces - List spaces            |
    |    GET  /api/parking/status - Overall status         |
    |    POST /api/bookings       - Create booking         |
    |    GET  /api/bookings       - List user bookings     |
    ========================================================
    """)

    app.run(host='0.0.0.0', port=port, debug=debug)
