"""
Configuration settings for AutoScoring application.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///autoscoring.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE_MB', 50)) * 1024 * 1024  # MB to bytes
    MAX_PDF_COUNT = int(os.environ.get('MAX_PDF_COUNT', 50))
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Scoring settings
    DEFAULT_SCORE_MIN = int(os.environ.get('DEFAULT_SCORE_MIN', 40))
    DEFAULT_SCORE_MAX = int(os.environ.get('DEFAULT_SCORE_MAX', 100))
    EVALUATION_MAX_WORDS = int(os.environ.get('EVALUATION_MAX_WORDS', 100))
    
    # OCR settings
    ENABLE_OCR = os.environ.get('ENABLE_OCR', 'true').lower() == 'true'
    
    # Cleanup settings
    ENABLE_CLEANUP = os.environ.get('ENABLE_CLEANUP', 'true').lower() == 'true'
    CLEANUP_ON_STARTUP = os.environ.get('CLEANUP_ON_STARTUP', 'true').lower() == 'true'
    
    # Worker settings
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 4))
    MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    
    # Gemini API keys (up to 15)
    GEMINI_API_KEYS = []
    for i in range(1, 16):
        key = os.environ.get(f'GEMINI_API_KEY_{i}') or os.environ.get(f'gemini_api_key_{i}')
        if key:
            GEMINI_API_KEYS.append(key)
    
    # GPU settings (auto-detected)
    GPU_AVAILABLE = False
    GPU_NAME = None
    
    @staticmethod
    def init_app(app):
        """Initialize application-specific configurations."""
        # Create upload and results directories
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.RESULTS_FOLDER, exist_ok=True)
