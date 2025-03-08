import os
from pathlib import Path

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # File upload settings
    BASE_DIR = Path(__file__).resolve().parent.parent
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    ENCODED_FOLDER = BASE_DIR / 'encoded'
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB max file size
    ALLOWED_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}

    # FFmpeg settings
    FFMPEG_PRESETS = {
        '480p': {
            'resolution': '854x480',
            'bitrate': '1000k',
            'audio_bitrate': '128k'
        },
        '720p': {
            'resolution': '1280x720',
            'bitrate': '2500k',
            'audio_bitrate': '192k'
        },
        '1080p': {
            'resolution': '1920x1080',
            'bitrate': '5000k',
            'audio_bitrate': '256k'
        }
    }

    # Celery Configuration
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

    def __init__(self):
        # Create upload and encoded directories if they don't exist
        self.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        self.ENCODED_FOLDER.mkdir(parents=True, exist_ok=True)
