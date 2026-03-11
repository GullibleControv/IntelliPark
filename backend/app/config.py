import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Security - SECRET_KEY must be set in environment
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required")
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///intellipark.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8000').split(',')

    # App settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Detection settings
    YOLO_MODEL_PATH = os.getenv('YOLO_MODEL_PATH', 'detection/models/yolo11s.pt')
    DETECTION_CONFIDENCE = float(os.getenv('DETECTION_CONFIDENCE', 0.5))
