import logging
from flask import Flask, jsonify
from flask_cors import CORS

from app.config import Config
from app.models import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


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
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    # Create database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified")

    logger.info("IntelliPark API initialized successfully")

    return app
