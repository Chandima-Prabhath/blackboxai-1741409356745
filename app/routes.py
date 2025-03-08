from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import logging

from app.services.encoder_service import encoder_service
from app.utils import (
    generate_job_id,
    allowed_file,
    get_secure_filename,
    ensure_directory,
    get_video_path
)

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/upload', methods=['POST'])
def upload_video():
    """Handle video file upload and start encoding process."""
    try:
        # Check if file was uploaded
        if 'video' not in request.files:
            return jsonify({
                'error': True,
                'message': 'No video file provided'
            }), 400

        file = request.files['video']
        
        # Check if a file was selected
        if file.filename == '':
            return jsonify({
                'error': True,
                'message': 'No file selected'
            }), 400

        # Validate file type
        if not allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
            return jsonify({
                'error': True,
                'message': 'Invalid file type. Allowed types: ' + 
                          ', '.join(current_app.config['ALLOWED_EXTENSIONS'])
            }), 400

        # Generate job ID and secure filename
        job_id = generate_job_id()
        filename = get_secure_filename(file.filename)
        
        # Ensure upload directory exists
        upload_dir = Path(current_app.config['UPLOAD_FOLDER'])
        ensure_directory(upload_dir)
        
        # Save uploaded file
        file_path = upload_dir / filename
        file.save(str(file_path))
        
        # Start encoding process
        result = encoder_service.start_encode_job(filename, job_id)
        
        return jsonify({
            'job_id': job_id,
            'message': 'Video upload successful, encoding started',
            'status': result['status']
        }), 202

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to process upload'
        }), 500

@api_bp.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get the status of an encoding job."""
    try:
        status = encoder_service.get_job_status(job_id)
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Failed to get status for job {job_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to get job status'
        }), 500

@api_bp.route('/video/<job_id>/<quality>', methods=['GET'])
def stream_video(job_id, quality):
    """Stream an encoded video file."""
    try:
        # Get video file path
        video_path = get_video_path(job_id, quality, current_app.config['ENCODED_FOLDER'])
        
        if not video_path.exists():
            return jsonify({
                'error': True,
                'message': 'Video not found'
            }), 404

        # Stream the video file
        return send_file(
            str(video_path),
            mimetype='video/mp4',
            as_attachment=False,
            download_name=f"{job_id}_{quality}.mp4"
        )

    except Exception as e:
        logger.error(f"Failed to stream video {job_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to stream video'
        }), 500

@api_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all encoding jobs and their status."""
    try:
        jobs = encoder_service.jobs
        return jsonify({
            'jobs': jobs,
            'total': len(jobs)
        }), 200
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to list jobs'
        }), 500
