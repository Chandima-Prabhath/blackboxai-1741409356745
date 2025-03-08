import uuid
import os
from pathlib import Path
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

def generate_job_id():
    """Generate a unique job ID."""
    return str(uuid.uuid4())

def allowed_file(filename, allowed_extensions):
    """Check if the file extension is allowed."""
    return Path(filename).suffix.lower() in allowed_extensions

def get_secure_filename(filename):
    """Generate a secure filename while preserving the extension."""
    name, ext = os.path.splitext(filename)
    secure_name = secure_filename(name)
    return f"{secure_name}{ext}"

def ensure_directory(directory):
    """Ensure a directory exists, create if it doesn't."""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {str(e)}")
        return False

def get_video_path(job_id, quality, base_dir):
    """Generate the path for an encoded video file."""
    return Path(base_dir) / job_id / f"{quality}.mp4"

def cleanup_job_files(job_id, upload_dir, encoded_dir):
    """Clean up temporary files after job completion or failure."""
    try:
        # Remove uploaded file
        upload_path = Path(upload_dir) / job_id
        if upload_path.exists():
            upload_path.unlink()
            
        # Remove encoded files directory
        encoded_path = Path(encoded_dir) / job_id
        if encoded_path.exists():
            for file in encoded_path.glob('*'):
                file.unlink()
            encoded_path.rmdir()
            
        logger.info(f"Cleaned up files for job {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to cleanup files for job {job_id}: {str(e)}")
        return False

def get_job_status_message(status_code):
    """Convert status code to human-readable message."""
    status_messages = {
        'pending': 'Job is queued for processing',
        'processing': 'Video encoding is in progress',
        'completed': 'Video encoding completed successfully',
        'failed': 'Video encoding failed',
        'invalid_file': 'Invalid file type uploaded'
    }
    return status_messages.get(status_code, 'Unknown status')
