#!/usr/bin/env python3
import subprocess
import sys
import os
import time
import signal
import argparse
from pathlib import Path
import logging
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self, tmp_dir="/tmp", port=5000, worker_name=None, worker_only=False):
        self.processes = {}
        self.tmp_dir = Path(tmp_dir)
        self.port = port
        self.worker_name = worker_name or f"encoder_worker_{os.getpid()}"
        self.worker_only = worker_only
        
        # Ensure required directories exist
        self.uploads_dir = self.tmp_dir / "uploads"
        self.encoded_dir = self.tmp_dir / "encoded"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.encoded_dir.mkdir(parents=True, exist_ok=True)

        # Set environment variables
        os.environ['UPLOAD_FOLDER'] = str(self.uploads_dir)
        os.environ['ENCODED_FOLDER'] = str(self.encoded_dir)

    def start_redis(self):
        """Start Redis server"""
        try:
            # Create Redis configuration
            redis_conf = self.tmp_dir / "redis.conf"
            redis_conf.write_text(f"""
                port 6379
                dir {self.tmp_dir}
                dbfilename redis.rdb
                logfile {self.tmp_dir}/redis.log
            """)

            cmd = f"redis-server {redis_conf}"
            process = subprocess.Popen(
                cmd.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes['redis'] = process
            logger.info("Redis server started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Redis: {e}")
            return False

    def start_celery_worker(self):
        """Start Celery worker"""
        try:
            env = os.environ.copy()
            cmd = f"celery -A app.services.encoder_service.celery worker --loglevel=info -n {self.worker_name}@%h -Q encoder_queue"
            process = subprocess.Popen(
                cmd.split(),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes['celery'] = process
            logger.info(f"Celery worker started: {self.worker_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start Celery worker: {e}")
            return False

    def start_flask(self):
        """Start Flask application"""
        try:
            app = create_app()
            from werkzeug.serving import run_simple
            run_simple('0.0.0.0', self.port, app, use_reloader=False)
            return True
        except Exception as e:
            logger.error(f"Failed to start Flask: {e}")
            return False

    def start_all(self):
        """Start all services"""
        if not self.worker_only:
            if not self.start_redis():
                return False
            time.sleep(2)  # Wait for Redis to start

        if not self.start_celery_worker():
            self.stop_all()
            return False

        if not self.worker_only:
            if not self.start_flask():
                self.stop_all()
                return False

        return True

    def stop_all(self):
        """Stop all services"""
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Stopped {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
                process.kill()

    def cleanup(self):
        """Clean up temporary files"""
        try:
            if not self.worker_only:
                redis_conf = self.tmp_dir / "redis.conf"
                redis_rdb = self.tmp_dir / "redis.rdb"
                redis_log = self.tmp_dir / "redis.log"
                
                for file in [redis_conf, redis_rdb, redis_log]:
                    if file.exists():
                        file.unlink()
            
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info("Received termination signal")
    manager.stop_all()
    manager.cleanup()
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Media Encoder Service Manager")
    parser.add_argument("--tmp-dir", default="/tmp/encoder", help="Temporary directory path")
    parser.add_argument("--port", type=int, default=5000, help="Port for the service")
    parser.add_argument("--worker-name", help="Custom name for Celery worker")
    parser.add_argument("--worker-only", action="store_true", help="Start only the worker component")
    
    args = parser.parse_args()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create and start service manager
    manager = ServiceManager(
        tmp_dir=args.tmp_dir,
        port=args.port,
        worker_name=args.worker_name,
        worker_only=args.worker_only
    )

    if manager.start_all():
        logger.info(f"{'Worker' if args.worker_only else 'All services'} started successfully")
        try:
            # Keep the script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            manager.stop_all()
            manager.cleanup()
    else:
        logger.error("Failed to start services")
        manager.stop_all()
        manager.cleanup()
        sys.exit(1)
