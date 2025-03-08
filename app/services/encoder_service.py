import ffmpeg
import logging
from pathlib import Path
from celery import Celery
from app.utils import get_video_path, cleanup_job_files
from app.config import Config

logger = logging.getLogger(__name__)

# Initialize Celery
celery = Celery('encoder_service',
                broker=Config.CELERY_BROKER_URL,
                backend=Config.CELERY_RESULT_BACKEND)

class EncoderService:
    def __init__(self, upload_folder, encoded_folder, presets):
        self.upload_folder = Path(upload_folder)
        self.encoded_folder = Path(encoded_folder)
        self.presets = presets
        self.jobs = {}  # In-memory job status tracking

    def start_encode_job(self, filename, job_id):
        """Start an encoding job for the uploaded video."""
        try:
            # Create output directory for this job
            job_output_dir = self.encoded_folder / job_id
            job_output_dir.mkdir(parents=True, exist_ok=True)

            # Update job status
            self.jobs[job_id] = {
                'status': 'processing',
                'progress': 0,
                'filename': filename,
                'outputs': []
            }

            # Start async encoding task
            encode_video.delay(
                str(self.upload_folder / filename),
                str(job_output_dir),
                self.presets,
                job_id
            )

            return {
                'job_id': job_id,
                'status': 'processing',
                'message': 'Encoding job started'
            }

        except Exception as e:
            logger.error(f"Failed to start encoding job: {str(e)}")
            self.jobs[job_id] = {
                'status': 'failed',
                'error': str(e)
            }
            return {
                'job_id': job_id,
                'status': 'failed',
                'message': f'Failed to start encoding: {str(e)}'
            }

    def get_job_status(self, job_id):
        """Get the current status of an encoding job."""
        if job_id not in self.jobs:
            return {
                'status': 'not_found',
                'message': 'Job not found'
            }
        return self.jobs[job_id]

@celery.task(bind=True)
def encode_video(self, input_path, output_dir, presets, job_id):
    """Celery task to encode video in different qualities."""
    try:
        # Get video information
        probe = ffmpeg.probe(input_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        
        outputs = []
        
        # Encode for each preset
        for quality, settings in presets.items():
            output_path = str(Path(output_dir) / f"{quality}.mp4")
            
            # Prepare FFmpeg command
            stream = ffmpeg.input(input_path)
            
            # Video stream
            stream = ffmpeg.filter(stream, 'scale', settings['resolution'])
            
            # Output with specific encoding settings
            stream = ffmpeg.output(stream, output_path,
                                 vcodec='libx264',
                                 acodec='aac',
                                 video_bitrate=settings['bitrate'],
                                 audio_bitrate=settings['audio_bitrate'],
                                 preset='medium',
                                 movflags='+faststart')
            
            # Run FFmpeg
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            outputs.append({
                'quality': quality,
                'path': output_path
            })
            
            # Update progress (divide 100 by number of presets)
            progress = (len(outputs) / len(presets)) * 100
            self.update_state(state='PROGRESS',
                            meta={'progress': progress,
                                 'current': len(outputs),
                                 'total': len(presets)})
        
        # Update job status on completion
        encoder_service = EncoderService(Config.UPLOAD_FOLDER,
                                       Config.ENCODED_FOLDER,
                                       Config.FFMPEG_PRESETS)
        encoder_service.jobs[job_id] = {
            'status': 'completed',
            'progress': 100,
            'outputs': outputs
        }
        
        # Cleanup input file
        Path(input_path).unlink()
        
        return {'status': 'completed', 'outputs': outputs}
        
    except Exception as e:
        logger.error(f"Encoding failed for job {job_id}: {str(e)}")
        # Update job status on failure
        encoder_service = EncoderService(Config.UPLOAD_FOLDER,
                                       Config.ENCODED_FOLDER,
                                       Config.FFMPEG_PRESETS)
        encoder_service.jobs[job_id] = {
            'status': 'failed',
            'error': str(e)
        }
        
        # Cleanup any partial outputs
        cleanup_job_files(job_id, Config.UPLOAD_FOLDER, Config.ENCODED_FOLDER)
        
        raise e

# Create singleton instance
encoder_service = EncoderService(Config.UPLOAD_FOLDER,
                               Config.ENCODED_FOLDER,
                               Config.FFMPEG_PRESETS)
