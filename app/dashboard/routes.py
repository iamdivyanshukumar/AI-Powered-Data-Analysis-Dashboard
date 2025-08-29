# app/dashboard/routes.py - UPDATED (WITH ERROR HANDLING)
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
import os
import pandas as pd
import json
from werkzeug.utils import secure_filename
from datetime import datetime
from app.dashboard.models import AnalysisSession, Visualization
from app.utils.data_utils import validate_csv, get_column_info, clean_dataframe, get_dataset_stats
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
                # Read the original data
                df = pd.read_csv(filepath)
                
                # Get dataset statistics before cleaning
                dataset_stats = get_dataset_stats(df)
                
                # Clean the data
                df_clean, encoding_mappings = clean_dataframe(df)
                
                # Create analysis session
                session = AnalysisSession(
                    user_id=current_user.id,
                    filename=filename,
                    dataset_stats=json.dumps(dataset_stats, default=str),
                    encoding_mappings=json.dumps(encoding_mappings, default=str)
                )
                db.session.add(session)
                db.session.commit()
                
                # Get column information
                column_info = get_column_info(df_clean)
                
                # Get visualization suggestions from GenAI
                analyzer = GenAIAnalyzer()
                suggestions = analyzer.get_visualization_suggestions(column_info)
                
                # Generate and save visualizations
                for suggestion in suggestions[:3]:  # Limit to top 3 suggestions
                    try:
                        graph_data = generate_visualization(
                            df_clean, 
                            suggestion['type'], 
                            suggestion['x'], 
                            suggestion.get('y')
                        )
                        
                        # Get insights from GenAI
                        data_sample = df_clean[[suggestion['x']] + ([suggestion['y']] if 'y' in suggestion else [])].head().to_string()
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
                            graph_path=graph_data,  # Storing base64 encoded image
                            insights=insights
                        )
                        db.session.add(viz)
                    except Exception as e:
                        flash(f"Error generating visualization for {suggestion['type']}: {str(e)}")
                        continue
                
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
    
    # Parse dataset stats and encoding mappings
    dataset_stats = {}
    encoding_mappings = {}
    
    try:
        if session.dataset_stats:
            dataset_stats = json.loads(session.dataset_stats)
        if session.encoding_mappings:
            encoding_mappings = json.loads(session.encoding_mappings)
    except json.JSONDecodeError:
        flash('Error loading dataset information')
    
    return render_template('dashboard/session.html', 
                         session=session, 
                         visualizations=visualizations,
                         dataset_stats=dataset_stats,
                         encoding_mappings=encoding_mappings)

@dashboard_bp.route('/dataset_info/<int:session_id>')
@login_required
def dataset_info(session_id):
    """View detailed dataset information."""
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('You do not have permission to view this session')
        return redirect(url_for('dashboard.index'))
    
    # Parse dataset stats and encoding mappings
    dataset_stats = {}
    encoding_mappings = {}
    
    try:
        if session.dataset_stats:
            dataset_stats = json.loads(session.dataset_stats)
        if session.encoding_mappings:
            encoding_mappings = json.loads(session.encoding_mappings)
    except json.JSONDecodeError:
        flash('Error loading dataset information')
    
    return render_template('dashboard/dataset_info.html', 
                         session=session,
                         dataset_stats=dataset_stats,
                         encoding_mappings=encoding_mappings)