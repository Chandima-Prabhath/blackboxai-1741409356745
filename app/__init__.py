from flask import Flask, render_template
from app.routes import main_bp, api_bp
from app.proxy import proxy_bp
import os

def create_app():
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    
    # Load configuration
    app.config.from_object('app.config')
    
    # Ensure upload and encoded directories exist
    upload_dir = os.getenv('UPLOAD_FOLDER', 'uploads')
    encoded_dir = os.getenv('ENCODED_FOLDER', 'encoded')
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(encoded_dir, exist_ok=True)
    
    # Set upload folder in app config
    app.config['UPLOAD_FOLDER'] = upload_dir
    app.config['ENCODED_FOLDER'] = encoded_dir
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB max file size
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(proxy_bp)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('favicon.ico')
    
    return app
