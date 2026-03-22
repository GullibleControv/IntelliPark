import os
import logging
from flask import Flask, jsonify, g, request, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import Config
from app.models import db, User
from app.utils.auth import hash_password

# Frontend directory (relative to backend)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'frontend')

# Initialize extensions (without app)
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    headers_enabled=True
)

# SocketIO instance (initialized later)
socketio = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Track if database has been initialized
_db_initialized = False


def create_app(config_class=Config):
    """Application factory for creating Flask app instance."""

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize rate limiter (skip in testing)
    if not app.config.get('TESTING'):
        limiter.init_app(app)

    # Initialize WebSocket support
    global socketio
    from app.services.websocket import init_socketio
    socketio = init_socketio(app)

    # Initialize email service
    from app.services.email import init_mail
    init_mail(app)

    # Configure CORS
    CORS(app, origins=config_class.CORS_ORIGINS, supports_credentials=True)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.parking import parking_bp
    from app.routes.booking import booking_bp
    from app.routes.admin import admin_bp
    from app.routes.payments import payments_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(parking_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(payments_bp)

    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'IntelliPark API'
        })

    # Database initialization endpoint (call once after deploy)
    # SECURITY: Protected by INIT_DB_SECRET environment variable
    @app.route('/api/init-db', methods=['POST'])
    def init_database():
        # Require secret token to prevent unauthorized database resets
        init_secret = os.getenv('INIT_DB_SECRET')
        provided_secret = request.headers.get('X-Init-Secret') or request.json.get('secret')

        if not init_secret:
            # If no secret configured, only allow in development
            if os.getenv('FLASK_ENV') == 'production' or os.getenv('RENDER'):
                logger.warning("SECURITY: init-db called in production without INIT_DB_SECRET configured")
                return jsonify({'error': 'Database initialization disabled in production'}), 403
        elif provided_secret != init_secret:
            logger.warning(f"SECURITY: init-db called with invalid secret from {request.remote_addr}")
            return jsonify({'error': 'Invalid or missing initialization secret'}), 401

        try:
            db.create_all()
            seed_admin_user()
            logger.info("Database initialized via /api/init-db endpoint")
            return jsonify({'status': 'Database initialized successfully'})
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return jsonify({'error': str(e)}), 500

    # Initialize database on first request (lazy initialization)
    @app.before_request
    def initialize_database():
        global _db_initialized
        if not _db_initialized:
            try:
                db.create_all()
                seed_admin_user()
                _db_initialized = True
                logger.info("Database tables created/verified on first request")
            except Exception as e:
                logger.warning(f"Database initialization deferred: {e}")

    # Security headers (OWASP recommendations)
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses."""
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        # XSS filter (legacy but still useful)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # HTTPS enforcement (in production)
        if not app.config.get('DEBUG'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # Content Security Policy (allow fonts and websockets)
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self' wss: ws:"
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Permissions policy
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed'}), 405

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(429)
    def ratelimit_handler(error):
        """Handle rate limit exceeded."""
        return jsonify({
            'error': 'Rate limit exceeded. Please try again later.',
            'retry_after': error.description
        }), 429

    # Serve frontend static files in production
    @app.route('/')
    def serve_index():
        """Serve the main index.html"""
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.route('/<path:filename>')
    def serve_static(filename):
        """Serve static files from frontend directory"""
        # Check if it's an API route (shouldn't reach here, but safety check)
        if filename.startswith('api/'):
            return jsonify({'error': 'Not found'}), 404

        # Try to serve the file
        try:
            return send_from_directory(FRONTEND_DIR, filename)
        except Exception:
            # If file not found, serve index.html for SPA routing
            if '.' not in filename:
                return send_from_directory(FRONTEND_DIR, 'index.html')
            return jsonify({'error': 'File not found'}), 404

    logger.info("IntelliPark API initialized successfully")

    return app


def validate_admin_password(password: str) -> bool:
    """
    Validate admin password strength.
    Must have: 12+ chars, uppercase, lowercase, digit, special char.
    """
    if len(password) < 12:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        return False
    return True


def seed_admin_user():
    """
    Create default admin user if it doesn't exist.

    SECURITY: In production, ADMIN_PASSWORD must be set via environment
    variable and meet strength requirements.
    """
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@intellipark.com')
    admin_password = os.getenv('ADMIN_PASSWORD')
    admin_name = os.getenv('ADMIN_NAME', 'Admin')

    # Check if we're in production
    is_production = (
        os.getenv('FLASK_ENV') == 'production' or
        os.getenv('RAILWAY_ENVIRONMENT') or
        os.getenv('RENDER') or
        os.getenv('HEROKU_APP_NAME')
    )

    if not admin_password:
        if is_production:
            logger.error(
                "SECURITY ERROR: ADMIN_PASSWORD must be set in production! "
                "Admin user will not be created."
            )
            return
        # Development: use weak password with warning
        admin_password = 'DevAdmin@123!'
        logger.warning(
            "Using default admin password for development. "
            "Set ADMIN_PASSWORD in .env for production."
        )

    # Validate password strength in production
    if is_production and not validate_admin_password(admin_password):
        logger.error(
            "SECURITY ERROR: Admin password does not meet strength requirements. "
            "Must have: 12+ chars, uppercase, lowercase, digit, special char."
        )
        return

    try:
        existing_admin = User.query.filter_by(email=admin_email).first()

        if not existing_admin:
            admin = User(
                email=admin_email,
                password_hash=hash_password(admin_password),
                name=admin_name,
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            # Don't log email in production for privacy
            if is_production:
                logger.info("Default admin user created")
            else:
                logger.info(f"Default admin user created: {admin_email}")
    except Exception as e:
        logger.warning(f"Admin seeding skipped: {e}")
