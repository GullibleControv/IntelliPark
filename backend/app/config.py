import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Security - use default for build, real key required in production
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))

    # Database - PostgreSQL in production, SQLite for local dev
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///intellipark.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CORS - allow all origins by default, restrict in production
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # App settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
