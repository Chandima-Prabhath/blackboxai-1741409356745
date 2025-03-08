from flask import Blueprint, send_from_directory, current_app
import os
import logging

logger = logging.getLogger(__name__)
proxy_bp = Blueprint('proxy', __name__)

@proxy_bp.route('/files/<path:filename>')
def serve_file(filename):
    """Serve files from the encoded directory"""
    try:
        encoded_dir = current_app.config['ENCODED_FOLDER']
        # Split the filename to get the job_id and quality
        parts = filename.split('/')
        if len(parts) >= 2:
            job_id = parts[0]
            quality_file = parts[1]
            # Construct the full path
            job_dir = os.path.join(encoded_dir, job_id)
            return send_from_directory(job_dir, quality_file)
        else:
            return {"error": "Invalid file path"}, 400
    except Exception as e:
        logger.error(f"Error serving file {filename}: {str(e)}")
        return {"error": "File not found"}, 404

@proxy_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve files from the uploads directory"""
    try:
        upload_dir = current_app.config['UPLOAD_FOLDER']
        return send_from_directory(upload_dir, filename)
    except Exception as e:
        logger.error(f"Error serving upload {filename}: {str(e)}")
        return {"error": "File not found"}, 404

@proxy_bp.route('/video/<job_id>/<quality>')
def serve_video(job_id, quality):
    """Serve encoded video files"""
    try:
        encoded_dir = current_app.config['ENCODED_FOLDER']
        video_path = os.path.join(encoded_dir, job_id, f"{quality}.mp4")
        if os.path.exists(video_path):
            return send_from_directory(
                os.path.join(encoded_dir, job_id),
                f"{quality}.mp4",
                mimetype='video/mp4'
            )
        else:
            return {"error": "Video not found"}, 404
    except Exception as e:
        logger.error(f"Error serving video {job_id}/{quality}: {str(e)}")
        return {"error": "Video not found"}, 404
