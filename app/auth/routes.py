from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth.models import User
from app.extensions import db
from app.utils.security import safe_check_password_hash

auth_bp = Blueprint('auth', __name__, template_folder='templates/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not safe_check_password_hash(user.password_hash, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard.index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate input
        if not username or not email or not password:
            flash('Please fill all fields', 'danger')
            return redirect(url_for('auth.signup'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('auth.signup'))
        
        # Check if username already exists
        user_by_username = User.query.filter_by(username=username).first()
        if user_by_username:
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.signup'))
        
        # Check if email already exists
        user_by_email = User.query.filter_by(email=email).first()
        if user_by_email:
            flash('Email address already registered', 'danger')
            return redirect(url_for('auth.signup'))
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    from app.dashboard.models import AnalysisSession, Visualization
    user_sessions = AnalysisSession.query.filter_by(user_id=current_user.id).count()
    total_visualizations = db.session.query(Visualization).join(AnalysisSession).filter(AnalysisSession.user_id == current_user.id).count()
    
    return render_template('auth/profile.html', 
                         user=current_user,
                         total_sessions=user_sessions,
                         total_visualizations=total_visualizations)