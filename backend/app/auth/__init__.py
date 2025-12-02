from .models import User
from .routes import auth_bp

# Add the user loader function
from flask_login import LoginManager
login_manager = LoginManager()

from flask import Flask
from app.extensions import db
from app.auth.routes import auth_bp
# other imports...

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register auth blueprint with URL prefix
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    # Example: other API blueprints
    # from app.api.notebook_routes import notebook_bp
    # app.register_blueprint(notebook_bp, url_prefix='/api/notebook')

    return app

