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
    def __init__(self, tmp_dir="/tmp", port=5000, worker_name=None):
        self.processes = {}
        self.tmp_dir = Path(tmp_dir)
        self.port = port
        self.worker_name = worker_name or f"encoder_worker_{os.getpid()}"
        
        # Ensure required directories exist
        self.uploads_dir = self.tmp_dir / "uploads"
        self.encoded_dir = self.tmp_dir / "encoded"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.encoded_dir.mkdir(parents=True, exist_ok=True)

        # Set environment variables
        os.environ['UPLOAD_FOLDER'] = str(self.uploads_dir)
        os.environ['ENCODED_FOLDER'] = str(self.encoded_dir)

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
        return self.start_flask()

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
    parser.add_argument("--worker-name", help="Custom name for worker instance")
    
    args = parser.parse_args()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create and start service manager
    manager = ServiceManager(
        tmp_dir=args.tmp_dir,
        port=args.port,
        worker_name=args.worker_name
    )

    if manager.start_all():
        logger.info("Service started successfully")
        try:
            # Keep the script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            manager.stop_all()
            manager.cleanup()
    else:
        logger.error("Failed to start service")
        manager.stop_all()
        manager.cleanup()
        sys.exit(1)
