import os
import logging
from flask import Flask, jsonify, g
from flask_cors import CORS

from app.config import Config
from app.models import db, User
from app.utils.auth import hash_password

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

    # Configure CORS
    CORS(app, origins=config_class.CORS_ORIGINS, supports_credentials=True)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.parking import parking_bp
    from app.routes.booking import booking_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(parking_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)

    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'IntelliPark API'
        })

    # Database initialization endpoint (call once after deploy)
    @app.route('/api/init-db', methods=['POST'])
    def init_database():
        try:
            db.create_all()
            seed_admin_user()
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

    logger.info("IntelliPark API initialized successfully")

    return app


def seed_admin_user():
    """Create default admin user if it doesn't exist."""
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@intellipark.com')
    admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@123')
    admin_name = os.getenv('ADMIN_NAME', 'Admin')

    try:
        existing_admin = User.query.filter_by(email=admin_email).first()

        if not existing_admin:
            admin = User(
                email=admin_email,
                password_hash=hash_password(admin_password),
                name=admin_name
            )
            db.session.add(admin)
            db.session.commit()
            logger.info(f"Default admin user created: {admin_email}")
    except Exception as e:
        logger.warning(f"Admin seeding skipped: {e}")
