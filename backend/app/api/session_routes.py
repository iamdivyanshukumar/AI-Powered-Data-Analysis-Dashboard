from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import uuid
from datetime import datetime

session_bp = Blueprint('session', __name__)

# In-memory session storage (for demo)
sessions = {}

@session_bp.route('/create', methods=['POST'])
@login_required
def create_session():
    """
    Create a new analysis session
    """
    try:
        data = request.json
        dataset_info = data.get('dataset_info', {})
        
        session_id = str(uuid.uuid4())
        
        session = {
            'session_id': session_id,
            'user_id': current_user.id,
            'dataset_info': dataset_info,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'status': 'active',
            'notebooks': []
        }
        
        # Store session
        sessions[session_id] = session
        
        return jsonify({
            'success': True,
            'session': session,
            'message': 'Session created successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create session: {str(e)}'
        }), 500

@session_bp.route('/<session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """
    Get session details
    """
    try:
        session = sessions.get(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        if session['user_id'] != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        return jsonify({
            'success': True,
            'session': session
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get session: {str(e)}'
        }), 500

@session_bp.route('/<session_id>/notebooks', methods=['GET'])
@login_required
def get_session_notebooks(session_id):
    """
    Get all notebooks in a session
    """
    try:
        session = sessions.get(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        if session['user_id'] != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        return jsonify({
            'success': True,
            'notebooks': session.get('notebooks', []),
            'total': len(session.get('notebooks', []))
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get notebooks: {str(e)}'
        }), 500