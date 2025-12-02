import os
import logging.config
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///autovizai.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'csv', 'txt'}
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # AI/ML Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    
    # LangChain Configuration
    LANGCHAIN_TRACING_V2 = os.getenv('LANGCHAIN_TRACING_V2', 'false').lower() == 'true'
    LANGCHAIN_ENDPOINT = os.getenv('LANGCHAIN_ENDPOINT', 'https://api.smith.langchain.com')
    LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY', '')
    LANGCHAIN_PROJECT = os.getenv('LANGCHAIN_PROJECT', 'autovizai-2.0')
    
    # Agent Configuration
    DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'gpt-4')
    FALLBACK_MODEL = os.getenv('FALLBACK_MODEL', 'gpt-3.5-turbo')
    MAX_ITERATIONS = int(os.getenv('MAX_ITERATIONS', '10'))
    DEFAULT_TEMPERATURE = float(os.getenv('DEFAULT_TEMPERATURE', '0.1'))
    
    # Execution Configuration
    MAX_EXECUTION_TIME = int(os.getenv('MAX_EXECUTION_TIME', '30'))  # seconds
    SAFE_EXECUTION_MODE = os.getenv('SAFE_EXECUTION_MODE', 'strict').lower()
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/autovizai.log')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

def setup_logging():
    """Configure application logging"""
    
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': Config.LOG_FORMAT,
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': Config.LOG_FILE,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'detailed',
                'level': Config.LOG_LEVEL,
            },
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                'level': 'INFO',
                'stream': 'ext://sys.stdout',
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': Config.LOG_FILE.replace('.log', '_error.log'),
                'maxBytes': 10485760,
                'backupCount': 5,
                'formatter': 'detailed',
                'level': 'ERROR',
            },
        },
        'loggers': {
            'app': {
                'handlers': ['file', 'console'],
                'level': Config.LOG_LEVEL,
                'propagate': False,
            },
            'agents': {
                'handlers': ['file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
            'core': {
                'handlers': ['file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
            'werkzeug': {
                'handlers': ['file'],
                'level': 'ERROR',
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    }
    
    logging.config.dictConfig(logging_config)
    
    # Log startup information
    startup_logger = logging.getLogger('app')
    startup_logger.info(f"Logging configured. Level: {Config.LOG_LEVEL}")
    startup_logger.info(f"Log file: {Config.LOG_FILE}")