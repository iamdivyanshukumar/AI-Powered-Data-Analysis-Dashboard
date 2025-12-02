import os
import logging
import jwt
from flask import Flask, jsonify, current_app, request
from app.config import Config, setup_logging
from app.extensions import db, login_manager, cors, migrate

def create_app(config_class=Config):
    """Application factory"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Configure Login Manager
    login_manager.login_view = 'auth.login'
    
    # --- JWT Token Loader ---
    # This allows the backend to accept the token sent by the frontend
    @login_manager.request_loader
    def load_user_from_request(req):
        auth_header = req.headers.get('Authorization')
        if auth_header:
            try:
                # Remove 'Bearer ' prefix
                token = auth_header.replace('Bearer ', '')
                # Decode token
                data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
                from app.auth.models import User
                return User.query.get(int(data.get('user_id')))
            except Exception:
                return None
        return None
    
    # Configure CORS
    cors.init_app(app, resources={
        r"/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
            "supports_credentials": True
        }
    })
    
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.api import api_bp
    
    # Register Auth at /auth
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Register API at /api (frontend sends requests to /api/notebook, /api/data, etc.)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Import models
    from app.auth.models import User
    
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'success': False, 'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    logger.info("AutoVizAI 2.0 application initialized")
    return app