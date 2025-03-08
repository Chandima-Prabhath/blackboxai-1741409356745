import subprocess
import os
import shutil
from pathlib import Path
import logging
import json
from datetime import datetime
import re
import threading
import queue
import signal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EncoderService:
    def __init__(self):
        self.jobs = {}
        # Optimized settings for web streaming
        self.default_qualities = {
            '480p': {
                'width': 854,
                'height': 480,
                'bitrate': '1000k',
                'maxrate': '1500k',
                'bufsize': '2000k',
                'audio_bitrate': '128k',
                'keyframe': '48',  # Keyframe every 2 seconds at 24fps
                'preset': 'slow',  # Better compression
                'profile': 'main',
                'level': '3.1',
                'tune': 'fastdecode'
            },
            '720p': {
                'width': 1280,
                'height': 720,
                'bitrate': '2500k',
                'maxrate': '3000k',
                'bufsize': '4000k',
                'audio_bitrate': '128k',
                'keyframe': '48',
                'preset': 'slow',
                'profile': 'main',
                'level': '3.1',
                'tune': 'fastdecode'
            },
            '1080p': {
                'width': 1920,
                'height': 1080,
                'bitrate': '5000k',
                'maxrate': '6000k',
                'bufsize': '8000k',
                'audio_bitrate': '192k',
                'keyframe': '48',
                'preset': 'slow',
                'profile': 'high',
                'level': '4.0',
                'tune': 'fastdecode'
            }
        }
        self.active_processes = {}

    def start_encode_job(self, filename, job_id, output_name=None, settings=None):
        """Start an encoding job with optional custom settings and output name"""
        try:
            qualities = self.default_qualities.copy()
            if settings:
                settings_dict = json.loads(settings)
                for quality, bitrate in settings_dict.items():
                    if quality in qualities and bitrate:
                        qualities[quality]['bitrate'] = bitrate
                        # Adjust maxrate and bufsize based on new bitrate
                        bitrate_value = int(bitrate.replace('k', ''))
                        qualities[quality]['maxrate'] = f"{int(bitrate_value * 1.5)}k"
                        qualities[quality]['bufsize'] = f"{int(bitrate_value * 2)}k"

            self.jobs[job_id] = {
                'status': 'pending',
                'progress': 0,
                'start_time': datetime.now().isoformat(),
                'filename': filename,
                'output_name': output_name or os.path.splitext(filename)[0],
                'current_quality': None,
                'outputs': [],
                'settings': qualities
            }

            # Start encoding in a separate thread
            thread = threading.Thread(
                target=self._encode_video,
                args=(filename, job_id)
            )
            thread.daemon = True
            thread.start()

            return {'status': 'pending', 'job_id': job_id}
        except Exception as e:
            logger.error(f"Failed to start encoding job: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    def _encode_video(self, filename, job_id):
        """Internal method to handle video encoding"""
        try:
            upload_path = Path(os.getenv('UPLOAD_FOLDER', 'uploads'))
            encoded_path = Path(os.getenv('ENCODED_FOLDER', 'encoded'))
            input_file = upload_path / filename
            output_dir = encoded_path / job_id
            output_name = self.jobs[job_id]['output_name']

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            qualities = self.jobs[job_id]['settings']
            total_steps = len(qualities)
            completed_steps = 0
            outputs = []

            # Get video duration
            duration = self._get_video_duration(input_file)
            if not duration:
                raise Exception("Could not determine video duration")

            for quality, settings in qualities.items():
                try:
                    self.jobs[job_id].update({
                        'status': 'processing',
                        'current_quality': quality,
                        'progress': (completed_steps / total_steps) * 100
                    })

                    output_file = output_dir / f"{output_name}_{quality}.mp4"
                    
                    # FFmpeg command with optimized settings for web streaming
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', str(input_file),
                        '-c:v', 'libx264',
                        '-preset', settings['preset'],
                        '-profile:v', settings['profile'],
                        '-level', settings['level'],
                        '-tune', settings['tune'],
                        '-b:v', settings['bitrate'],
                        '-maxrate', settings['maxrate'],
                        '-bufsize', settings['bufsize'],
                        '-vf', f"scale={settings['width']}:{settings['height']}",
                        '-g', settings['keyframe'],
                        '-keyint_min', settings['keyframe'],
                        '-sc_threshold', '0',  # Disable scene cut detection
                        '-c:a', 'aac',
                        '-b:a', settings['audio_bitrate'],
                        '-ar', '48000',  # Audio sample rate
                        '-ac', '2',      # Stereo audio
                        '-movflags', '+faststart',  # Enable fast start for web playback
                        '-progress', 'pipe:1',
                        str(output_file)
                    ]

                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    self.active_processes[job_id] = process

                    # Monitor FFmpeg progress
                    while True:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            progress = self._parse_ffmpeg_progress(output, duration)
                            if progress is not None:
                                quality_progress = (completed_steps + progress/100) / total_steps * 100
                                self.jobs[job_id]['progress'] = quality_progress

                    if process.returncode == 0:
                        outputs.append({
                            'quality': quality,
                            'path': str(output_file),
                            'settings': settings
                        })
                        completed_steps += 1
                    else:
                        error_output = process.stderr.read()
                        logger.error(f"FFmpeg error: {error_output}")
                        raise Exception(f"FFmpeg failed for quality {quality}")

                except Exception as e:
                    logger.error(f"Error encoding {quality}: {str(e)}")
                    self.jobs[job_id].update({
                        'status': 'failed',
                        'error': str(e)
                    })
                    return

                finally:
                    if job_id in self.active_processes:
                        del self.active_processes[job_id]

            self.jobs[job_id].update({
                'status': 'completed',
                'progress': 100,
                'outputs': outputs,
                'completion_time': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Encoding failed: {str(e)}")
            self.jobs[job_id].update({
                'status': 'failed',
                'error': str(e)
            })

    def _get_video_duration(self, input_file):
        """Get video duration using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                str(input_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except Exception as e:
            logger.error(f"Error getting video duration: {str(e)}")
            return None

    def _parse_ffmpeg_progress(self, output, duration):
        """Parse FFmpeg progress output"""
        try:
            if 'out_time_ms=' in output:
                time_ms = int(output.split('out_time_ms=')[1].strip())
                progress = (time_ms / 1000000) / duration * 100
                return min(100, max(0, progress))
            return None
        except Exception:
            return None

    def stop_job(self, job_id):
        """Stop an encoding job"""
        try:
            if job_id in self.active_processes:
                process = self.active_processes[job_id]
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
                del self.active_processes[job_id]
                self.jobs[job_id]['status'] = 'stopped'
                return True
            return False
        except Exception as e:
            logger.error(f"Error stopping job {job_id}: {str(e)}")
            return False

    def clean_job(self, job_id):
        """Clean up all files related to a job"""
        try:
            # Get paths
            upload_path = Path(os.getenv('UPLOAD_FOLDER', 'uploads'))
            encoded_path = Path(os.getenv('ENCODED_FOLDER', 'encoded'))
            
            # Clean up source file if it exists
            if job_id in self.jobs:
                source_file = upload_path / self.jobs[job_id]['filename']
                if source_file.exists():
                    source_file.unlink()

            # Clean up encoded files
            job_output_dir = encoded_path / job_id
            if job_output_dir.exists():
                shutil.rmtree(job_output_dir)

            # Remove job from jobs dict
            if job_id in self.jobs:
                del self.jobs[job_id]

            return True
        except Exception as e:
            logger.error(f"Error cleaning job {job_id}: {str(e)}")
            return False

    def get_job_info(self, job_id):
        """Get detailed information about a job"""
        try:
            if job_id not in self.jobs:
                return None
            
            job = self.jobs[job_id]
            encoded_path = Path(os.getenv('ENCODED_FOLDER', 'encoded'))
            job_path = encoded_path / job_id

            # Get file sizes
            files_info = []
            if job_path.exists():
                for output in job.get('outputs', []):
                    file_path = Path(output['path'])
                    if file_path.exists():
                        files_info.append({
                            'quality': output['quality'],
                            'size': file_path.stat().st_size,
                            'path': str(file_path)
                        })

            return {
                **job,
                'files': files_info
            }
        except Exception as e:
            logger.error(f"Error getting job info: {str(e)}")
            return None

encoder_service = EncoderService()
