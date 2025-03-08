from app.services.encoder_service import celery

if __name__ == '__main__':
    celery.worker_main(['worker', '--loglevel=info'])
