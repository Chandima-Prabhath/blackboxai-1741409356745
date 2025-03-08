from flask import Blueprint, request, jsonify, current_app, render_template, send_from_directory
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import logging
import json
from datetime import datetime

from app.services.encoder_service import encoder_service

logger = logging.getLogger(__name__)

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

@main_bp.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@main_bp.route('/files')
def files_page():
    """Render the files page"""
    return render_template('files.html')

@api_bp.route('/files')
def list_files():
    """List all encoded files with their details"""
    try:
        encoded_dir = Path(current_app.config['ENCODED_FOLDER'])
        files = []
        
        if encoded_dir.exists():
            for job_dir in encoded_dir.iterdir():
                if job_dir.is_dir():
                    job_id = job_dir.name
                    job_info = encoder_service.get_job_info(job_id)
                    
                    if job_info and job_info.get('status') == 'completed':
                        files.append({
                            'job_id': job_id,
                            'output_name': job_info.get('output_name', ''),
                            'created_at': job_info.get('start_time'),
                            'completed_at': job_info.get('completion_time'),
                            'qualities': {
                                file['quality']: file['size'] 
                                for file in job_info.get('files', [])
                            }
                        })
        
        return jsonify({
            'files': sorted(files, key=lambda x: x['created_at'], reverse=True)
        })
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to list files'
        }), 500

@api_bp.route('/upload', methods=['POST'])
def upload_video():
    """Handle video file upload and start encoding process"""
    try:
        if 'video' not in request.files:
            return jsonify({
                'error': True,
                'message': 'No video file provided'
            }), 400

        file = request.files['video']
        output_name = request.form.get('output_name')
        
        if file.filename == '':
            return jsonify({
                'error': True,
                'message': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'error': True,
                'message': 'Invalid file type'
            }), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file
        file.save(file_path)
        
        # Get custom encoding settings if provided
        settings = request.form.get('settings')
        
        # Generate job ID and start encoding
        job_id = generate_job_id()
        result = encoder_service.start_encode_job(
            filename=filename,
            job_id=job_id,
            output_name=output_name,
            settings=settings
        )
        
        return jsonify({
            'job_id': job_id,
            'message': 'Video upload successful',
            'status': result['status']
        }), 202

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to process upload'
        }), 500

@api_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all encoding jobs"""
    try:
        return jsonify({
            'jobs': encoder_service.jobs
        }), 200
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to list jobs'
        }), 500

@api_bp.route('/jobs/<job_id>/stop', methods=['POST'])
def stop_job(job_id):
    """Stop an encoding job"""
    try:
        if encoder_service.stop_job(job_id):
            return jsonify({
                'message': 'Job stopped successfully'
            }), 200
        else:
            return jsonify({
                'error': True,
                'message': 'Job not found or already completed'
            }), 404
    except Exception as e:
        logger.error(f"Failed to stop job: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to stop job'
        }), 500

@api_bp.route('/jobs/<job_id>/clean', methods=['POST'])
def clean_job(job_id):
    """Clean up all files related to a job"""
    try:
        if encoder_service.clean_job(job_id):
            return jsonify({
                'message': 'Job cleaned successfully'
            }), 200
        else:
            return jsonify({
                'error': True,
                'message': 'Failed to clean job'
            }), 500
    except Exception as e:
        logger.error(f"Failed to clean job: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to clean job'
        }), 500

@api_bp.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get the status of an encoding job"""
    try:
        status = encoder_service.get_job_status(job_id)
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Failed to get status for job {job_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to get job status'
        }), 500

@api_bp.route('/video/<job_id>/<quality>')
def serve_video(job_id, quality):
    """Serve encoded video files"""
    try:
        job_info = encoder_service.get_job_info(job_id)
        if not job_info:
            return jsonify({
                'error': True,
                'message': 'Job not found'
            }), 404

        encoded_dir = current_app.config['ENCODED_FOLDER']
        output_name = job_info.get('output_name', 'video')
        video_filename = f"{output_name}_{quality}.mp4"
        video_path = os.path.join(encoded_dir, job_id, video_filename)

        if os.path.exists(video_path):
            return send_from_directory(
                os.path.join(encoded_dir, job_id),
                video_filename,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=video_filename
            )
        else:
            return jsonify({
                'error': True,
                'message': 'Video not found'
            }), 404
    except Exception as e:
        logger.error(f"Failed to serve video: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to serve video'
        }), 500

def allowed_file(filename):
    """Check if the file extension is allowed"""
    ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'wmv'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_job_id():
    """Generate a unique job ID"""
    import uuid
    return str(uuid.uuid4())
