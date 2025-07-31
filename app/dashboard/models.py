from app import db
from flask_login import current_user
from datetime import datetime

class AnalysisSession(db.Model):
    """Stores user analysis sessions."""
    __tablename__ = 'analysis_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    filename = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    visualizations = db.relationship('Visualization', backref='session', lazy=True)

class Visualization(db.Model):
    """Stores generated visualizations and insights."""
    __tablename__ = 'visualizations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('analysis_sessions.id'))
    graph_type = db.Column(db.String(64))
    x_column = db.Column(db.String(128))
    y_column = db.Column(db.String(128), nullable=True)
    graph_path = db.Column(db.String(256))
    insights = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)