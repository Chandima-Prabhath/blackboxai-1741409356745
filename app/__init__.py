from flask import Flask
from app.config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    from app.routes import api_bp
    app.register_blueprint(api_bp)

    # Register error handlers
    from app.error_handlers import register_error_handlers
    register_error_handlers(app)

    return app
