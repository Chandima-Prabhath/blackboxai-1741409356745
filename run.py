import os
from app import create_app
from app.config import Config

# Create Flask application instance
app = create_app(Config)

if __name__ == '__main__':
    # Create required directories
    Config().UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    Config().ENCODED_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
