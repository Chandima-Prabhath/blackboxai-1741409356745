import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Flask configuration
DEBUG = True
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

# File upload configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', BASE_DIR / 'uploads')
ENCODED_FOLDER = os.getenv('ENCODED_FOLDER', BASE_DIR / 'encoded')
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB max file size
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'wmv'}

# Celery configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Redis configuration
REDIS_URL = 'redis://localhost:6379/0'

# Create required directories
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
Path(ENCODED_FOLDER).mkdir(parents=True, exist_ok=True)
