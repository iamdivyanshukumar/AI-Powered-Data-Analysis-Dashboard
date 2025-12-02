from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from flask_migrate import Migrate

# Initialize extensions
# We create the objects here, but we don't bind them to the app yet.
db = SQLAlchemy()
login_manager = LoginManager()
cors = CORS()
migrate = Migrate()

@login_manager.user_loader
def load_user(user_id):
    """Load user from database"""
    # Local import to avoid circular dependency
    from app.auth.models import User
    return User.query.get(int(user_id))