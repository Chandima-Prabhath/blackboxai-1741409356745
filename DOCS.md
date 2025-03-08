# Distributed Media Encoder Service

A distributed video encoding service with a modern dark-themed UI, supporting multiple encoding instances for high-performance video processing.

## Features

- Modern dark-themed web interface with drag-and-drop
- Distributed video encoding across multiple workers
- Multiple quality outputs (480p, 720p, 1080p)
- Real-time encoding progress tracking
- Single-port access through Python proxy
- Temporary directory support for restricted environments

## System Architecture

- **Web Interface**: Modern dark theme UI for video upload and monitoring
- **Task Queue**: Redis-based distributed task queue
- **Workers**: Multiple Celery workers for distributed encoding
- **Storage**: Temporary directory based file storage
- **Proxy**: Python-based reverse proxy for single-port access

## Prerequisites

- Python 3.8+
- FFmpeg
- Redis

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the service:
```bash
python3 start_service.py --port 5000 --tmp-dir /tmp/encoder
```

The service will be available at `http://localhost:5000`

## Distributed Setup

### Main Instance
```bash
python3 start_service.py --port 5000 --tmp-dir /tmp/encoder
```

### Additional Worker Instances
```bash
# Worker 1
python3 start_service.py --worker-name encoder_worker_1 --tmp-dir /tmp/encoder_1

# Worker 2
python3 start_service.py --worker-name encoder_worker_2 --tmp-dir /tmp/encoder_2

# Add more workers as needed
```

## Command Line Options

- `--port`: Port number for the web interface (default: 5000)
- `--tmp-dir`: Temporary directory for storage (default: /tmp/encoder)
- `--worker-name`: Custom name for worker instance

## Directory Structure

```
/tmp/encoder/
├── uploads/           # Uploaded video files
├── encoded/          # Encoded video files
├── redis.conf        # Redis configuration
├── redis.rdb         # Redis database
└── redis.log         # Redis logs
```

## Monitoring

### View Service Logs
```bash
tail -f /tmp/encoder/redis.log  # Redis logs
```

### Check Worker Status
```python
from app.services.encoder_service import celery
celery.control.inspect().active()  # View active tasks
celery.control.inspect().registered()  # View registered workers
```

## Scaling

The service can be scaled by adding more worker instances. Each worker should:
1. Have FFmpeg installed
2. Connect to the same Redis instance
3. Have access to the shared storage directory

### Example Scaling Setup

```bash
# Main instance (handles web UI and coordination)
python3 start_service.py --port 5000 --tmp-dir /shared/tmp/encoder

# Worker instances (handle encoding tasks)
python3 start_service.py --worker-name encoder_worker_1 --tmp-dir /shared/tmp/encoder
python3 start_service.py --worker-name encoder_worker_2 --tmp-dir /shared/tmp/encoder
```

## Performance Considerations

1. **Storage Performance**:
   - Use fast storage for /tmp directory
   - Consider local SSD for better I/O performance

2. **Network Bandwidth**:
   - Ensure sufficient bandwidth between workers
   - Consider network topology when distributing workers

3. **Resource Allocation**:
   - Monitor CPU usage across workers
   - Balance memory usage for concurrent encoding

## Troubleshooting

1. **Service Won't Start**:
   ```bash
   # Check if Redis is already running
   ps aux | grep redis
   # Check port availability
   netstat -tulpn | grep 5000
   ```

2. **Encoding Fails**:
   - Verify FFmpeg installation
   - Check temporary directory permissions
   - Verify Redis connectivity

3. **Worker Connection Issues**:
   - Check Redis connection string
   - Verify network connectivity
   - Check firewall settings

## Security Notes

1. **Temporary Directory**:
   - Regularly clean up old files
   - Set appropriate permissions
   ```bash
   chmod 700 /tmp/encoder
   ```

2. **Redis Security**:
   - Use strong passwords in production
   - Configure proper network restrictions

3. **File Validation**:
   - Service validates video file types
   - Implements size restrictions
   - Sanitizes filenames

## API Endpoints

- `POST /api/upload`: Upload video file
- `GET /api/status/<job_id>`: Get encoding status
- `GET /api/video/<job_id>/<quality>`: Stream encoded video
- `GET /api/jobs`: List all encoding jobs

## Contributing

[Contribution Guidelines]

## License

[Your License Here]
