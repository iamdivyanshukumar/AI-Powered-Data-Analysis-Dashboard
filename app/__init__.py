from flask import Flask
import os
from dotenv import load_dotenv
from app.extensions import db, login_manager
from datetime import datetime
import logging

def create_app():
    """Create and configure the Flask application."""
    load_dotenv()
    
    app = Flask(__name__, static_folder='static')
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('autovizai')
    logger.setLevel(logging.INFO)
    
    # Configure application
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///autovizai.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
    app.config['ALLOWED_EXTENSIONS'] = {'csv'}
    app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Import models here to avoid circular imports
    from app.auth.models import User
    
    # User loader function
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints with correct URL prefixes
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    
    # Create upload and static directories if they don't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    static_css_dir = os.path.join(app.root_path, 'static', 'css')
    os.makedirs(static_css_dir, exist_ok=True)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Add timesince template filter
    @app.template_filter('timesince')
    def timesince_filter(dt):
        """Return a friendly timesince format."""
        now = datetime.now()
        diff = now - dt
        
        seconds = diff.total_seconds()
        if seconds < 60:
            return 'just now'
        
        minutes = seconds / 60
        if minutes < 60:
            return f'{int(minutes)} minutes ago'
        
        hours = minutes / 60
        if hours < 24:
            return f'{int(hours)} hours ago'
        
        days = hours / 24
        if days < 30:
            return f'{int(days)} days ago'
        
        months = days / 30
        if months < 12:
            return f'{int(months)} months ago'
        
        years = months / 12
        return f'{int(years)} years ago'
    
    return app