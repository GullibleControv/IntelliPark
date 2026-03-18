import os
import secrets
import warnings
from dotenv import load_dotenv

load_dotenv()


def get_secret_key():
    """
    Get SECRET_KEY from environment.
    In production, a secure key MUST be provided via environment variables.
    Uses a build-safe default during container build, but logs warnings at runtime.
    """
    key = os.getenv('SECRET_KEY')
    is_production = (
        os.getenv('FLASK_ENV') == 'production' or
        os.getenv('RAILWAY_ENVIRONMENT') or
        os.getenv('RENDER') or
        os.getenv('HEROKU_APP_NAME')
    )

    if not key:
        if is_production:
            # Use a build-safe default but log a critical warning
            # This allows the container to build but warns at runtime
            key = 'INSECURE-DEFAULT-KEY-SET-SECRET_KEY-ENV-VAR'
            warnings.warn(
                "SECURITY WARNING: SECRET_KEY not set in production! "
                "Set SECRET_KEY environment variable in Railway dashboard. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"",
                UserWarning
            )
        else:
            # Development: generate random key
            key = secrets.token_hex(32)
            warnings.warn(
                "SECRET_KEY not set - using random key. Sessions will not persist across restarts.",
                UserWarning
            )
    elif is_production and (key.startswith('INSECURE') or key == 'your-super-secret-key-change-this'):
        warnings.warn(
            "SECURITY WARNING: Using insecure default SECRET_KEY in production! "
            "Set a proper SECRET_KEY in Railway dashboard.",
            UserWarning
        )

    # Validate key strength
    if key and len(key) < 32 and not key.startswith('INSECURE'):
        warnings.warn(
            "SECRET_KEY is too short (< 32 chars). Use a stronger key for security.",
            UserWarning
        )

    return key


class Config:
    """Application configuration loaded from environment variables."""

    # Security - enforce strong secrets
    SECRET_KEY = get_secret_key()
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))

    # Database - PostgreSQL in production, SQLite for local dev
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///intellipark.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Request size limit (16 MB max) - prevents DoS via large payloads
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

    # CORS - restrict in production
    _cors_env = os.getenv('CORS_ORIGINS', '')
    if _cors_env:
        CORS_ORIGINS = _cors_env.split(',')
    elif os.getenv('FLASK_ENV') == 'production':
        # In production, default to app URL only
        CORS_ORIGINS = [os.getenv('APP_URL', 'https://intellipark.com')]
    else:
        # Development: allow localhost
        CORS_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:5500']

    # App settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    APP_URL = os.getenv('APP_URL', 'http://localhost:5000')

    # Email configuration (Flask-Mail)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@intellipark.com')

    # Stripe configuration
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
