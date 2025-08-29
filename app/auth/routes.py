# app/auth/routes.py - UPDATED
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.auth.models import User
from app.extensions import db

auth_bp = Blueprint('auth', __name__, template_folder='templates/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username already exists
        user_by_username = User.query.filter_by(username=username).first()
        if user_by_username:
            flash('Username already exists')
            return redirect(url_for('auth.signup'))
        
        # Check if email already exists
        user_by_email = User.query.filter_by(email=email).first()
        if user_by_email:
            flash('Email address already registered')
            return redirect(url_for('auth.signup'))
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))