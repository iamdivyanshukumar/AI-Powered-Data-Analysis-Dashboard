from flask import Blueprint

# Create main API blueprint
api_bp = Blueprint('api', __name__)

# Import sub-blueprints directly (NO try/except)
# This ensures we see errors immediately
from .analysis_routes import analysis_bp
from .data_routes import data_bp
from .notebook_routes import notebook_bp
from .session_routes import session_bp

# Register sub-blueprints with their specific prefixes
# Since Vite strips '/api', these combine to form:
# /analysis, /data, /notebook, /session
api_bp.register_blueprint(analysis_bp, url_prefix='/analysis')
api_bp.register_blueprint(data_bp, url_prefix='/data')
api_bp.register_blueprint(notebook_bp, url_prefix='/notebook')
api_bp.register_blueprint(session_bp, url_prefix='/session')

@api_bp.route('/')
def api_index():
    return {
        'success': True,
        'message': 'AutoVizAI 2.0 API',
        'version': '2.0.0'
    }