from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
import os
import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime
from app.dashboard.models import AnalysisSession, Visualization
from app.utils.data_utils import validate_csv, get_column_info
from app.utils.viz_utils import generate_visualization
from app.utils.genai_utils import GenAIAnalyzer
from app import db

dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """User dashboard showing analysis history."""
    sessions = AnalysisSession.query.filter_by(user_id=current_user.id).order_by(AnalysisSession.created_at.desc()).all()
    return render_template('dashboard/index.html', sessions=sessions)

@dashboard_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Handle file upload and initial processing."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and validate_csv(file.filename):
            filename = secure_filename(file.filename)
            upload_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            
            try:
                # Create analysis session
                session = AnalysisSession(
                    user_id=current_user.id,
                    filename=filename
                )
                db.session.add(session)
                db.session.commit()
                
                # Process the file
                df = pd.read_csv(filepath)
                column_info = get_column_info(df)
                
                # Get visualization suggestions from GenAI
                analyzer = GenAIAnalyzer()
                suggestions = analyzer.get_visualization_suggestions(column_info)
                
                # Generate and save visualizations
                for suggestion in suggestions[:3]:  # Limit to top 3 suggestions
                    graph_html = generate_visualization(
                        df, 
                        suggestion['type'], 
                        suggestion['x'], 
                        suggestion.get('y')
                    )
                    
                    # Get insights from GenAI
                    data_sample = df[[suggestion['x']] + ([suggestion['y']] if 'y' in suggestion else [])].head().to_string()
                    insights = analyzer.get_graph_summary(
                        suggestion['type'],
                        suggestion['x'],
                        suggestion.get('y'),
                        data_sample
                    )
                    
                    # Save visualization
                    viz = Visualization(
                        session_id=session.id,
                        graph_type=suggestion['type'],
                        x_column=suggestion['x'],
                        y_column=suggestion.get('y'),
                        graph_path=graph_html,  # Storing HTML directly for prototype
                        insights=insights
                    )
                    db.session.add(viz)
                
                db.session.commit()
                return redirect(url_for('dashboard.view_session', session_id=session.id))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing file: {str(e)}')
                return redirect(request.url)
        
        else:
            flash('Invalid file type. Please upload a CSV file.')
            return redirect(request.url)
    
    return render_template('dashboard/upload.html')

@dashboard_bp.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """View analysis session results."""
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('You do not have permission to view this session')
        return redirect(url_for('dashboard.index'))
    
    visualizations = Visualization.query.filter_by(session_id=session_id).all()
    return render_template('dashboard/session.html', session=session, visualizations=visualizations)