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
    
    # Gemini API keys (up to 20)
    GEMINI_API_KEYS = []
    for i in range(1, 21):
        key = os.environ.get(f'GEMINI_API_KEY_{i}') or os.environ.get(f'gemini_api_key_{i}')
        if key:
            GEMINI_API_KEYS.append(key)
    
    # LLM provider settings
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'gemini')  # gemini | nvidia | openai | deepseek | openrouter | siliconflow | github
    _LLM_MODEL_DEFAULTS = {
        'gemini': 'gemini-2.5-flash',
        'nvidia': 'moonshotai/kimi-k2.5',
        'openai': 'gpt-4.1',
        'deepseek': 'deepseek-chat',
        'openrouter': 'openai/gpt-4o-mini',
        'siliconflow': 'Qwen/Qwen2.5-72B-Instruct',
        'github': 'openai/gpt-4.1-mini',
    }
    LLM_MODEL = os.environ.get('LLM_MODEL') or _LLM_MODEL_DEFAULTS.get(LLM_PROVIDER, 'gemini-2.5-flash')
    NVIDIA_API_KEY = os.environ.get('NVIDIA_API_KEY') or None
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or None
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY') or None
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY') or None
    SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY') or None
    GITHUB_API_KEY = os.environ.get('GITHUB_API_KEY') or None
    NVIDIA_BASE_URL = os.environ.get('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1')
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
    OPENROUTER_BASE_URL = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    SILICONFLOW_BASE_URL = os.environ.get('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
    GITHUB_BASE_URL = os.environ.get('GITHUB_BASE_URL', 'https://models.github.ai/inference')

    # GPU settings (auto-detected)
    GPU_AVAILABLE = False
    GPU_NAME = None
    
    @staticmethod
    def init_app(app):
        """Initialize application-specific configurations."""
        # Create upload and results directories
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.RESULTS_FOLDER, exist_ok=True)

        # Validate LLM provider API key requirements
        provider = app.config.get('LLM_PROVIDER', 'gemini')
        required_key_by_provider = {
            'nvidia': 'NVIDIA_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'siliconflow': 'SILICONFLOW_API_KEY',
            'github': 'GITHUB_API_KEY',
        }

        required_key = required_key_by_provider.get(provider)
        if required_key and not app.config.get(required_key):
            app.logger.warning(
                f'LLM_PROVIDER is set to "{provider}" but {required_key} is not configured. '
                'Set it in .env or Admin Panel before running scoring jobs.'
            )
