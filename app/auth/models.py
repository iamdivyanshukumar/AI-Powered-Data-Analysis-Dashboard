from app.extensions import db
from flask_login import UserMixin
from app.utils.security import safe_generate_password_hash, safe_check_password_hash

class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    
    def set_password(self, password):
        """Create hashed password."""
        self.password_hash = safe_generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return safe_check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'