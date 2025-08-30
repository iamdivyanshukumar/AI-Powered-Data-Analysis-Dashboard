# app/dashboard/models.py - UPDATED
from app.extensions import db
from flask_login import current_user
from datetime import datetime

class AnalysisSession(db.Model):
    """Stores user analysis sessions."""
    __tablename__ = 'analysis_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    filename = db.Column(db.String(256))
    dataset_stats = db.Column(db.Text)  # Store dataset statistics as JSON
    encoding_mappings = db.Column(db.Text)  # Store encoding mappings as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    visualizations = db.relationship('Visualization', backref='session', lazy=True, cascade='all, delete-orphan')

class Visualization(db.Model):
    """Stores generated visualizations and insights."""
    __tablename__ = 'visualizations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('analysis_sessions.id', ondelete='CASCADE'))
    graph_type = db.Column(db.String(64))
    x_column = db.Column(db.String(128))
    y_column = db.Column(db.String(128), nullable=True)
    graph_path = db.Column(db.String(256))
    insights = db.Column(db.Text)
    graph_description = db.Column(db.Text)  # Store textual description for on-demand summaries
    created_at = db.Column(db.DateTime, default=datetime.utcnow)