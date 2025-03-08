from flask import jsonify
from werkzeug.exceptions import HTTPException
import logging

def register_error_handlers(app):
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle all HTTP exceptions."""
        response = {
            'error': True,
            'message': error.description,
            'status_code': error.code
        }
        logger.error(f'HTTP error occurred: {error.code} - {error.description}')
        return jsonify(response), error.code

    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """Handle all unhandled exceptions."""
        response = {
            'error': True,
            'message': 'An unexpected error occurred',
            'status_code': 500
        }
        logger.error(f'Unhandled error: {str(error)}', exc_info=True)
        return jsonify(response), 500

    @app.errorhandler(413)
    def handle_file_too_large(error):
        """Handle file size exceeding MAX_CONTENT_LENGTH."""
        response = {
            'error': True,
            'message': 'File is too large. Maximum size allowed is 1GB.',
            'status_code': 413
        }
        logger.error('File upload exceeded size limit')
        return jsonify(response), 413
