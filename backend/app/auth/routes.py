from flask import Blueprint, request, jsonify, current_app, make_response
from flask_login import login_user, logout_user, login_required, current_user
import jwt
from datetime import datetime, timedelta

from app.auth.models import User
# CRITICAL: Must import db from extensions where it is defined
from app.extensions import db

auth_bp = Blueprint('auth', __name__)

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'success': False, 'error': 'Missing fields'}), 400
        
        # Check existing user
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': 'Username taken'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'error': 'Email taken'}), 400
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        token = generate_token(user.id)
        
        return jsonify({
            'success': True, 
            'message': 'User registered successfully',
            'token': token,
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        login_user(user, remember=True)
        token = generate_token(user.id)
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Login failed: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True, 'message': 'Logout successful'})