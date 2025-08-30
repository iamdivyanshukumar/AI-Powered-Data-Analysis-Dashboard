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
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

# Define the blueprint first
dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """User dashboard showing analysis history."""
    sessions = AnalysisSession.query.filter_by(user_id=current_user.id).order_by(AnalysisSession.created_at.desc()).all()
    return render_template('dashboard/index.html', sessions=sessions)

@dashboard_bp.route('/generate_summary/<int:viz_id>')
@login_required
def generate_summary(viz_id):
    """Generate AI summary on-demand for a specific visualization."""
    viz = Visualization.query.get_or_404(viz_id)
    session = AnalysisSession.query.get_or_404(viz.session_id)
    
    if session.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        # Load the original data to get statistics
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], session.filename)
        df = pd.read_csv(filepath)
        
        # Get basic statistics for the relevant columns
        data_stats = {}
        if viz.x_column in df.columns:
            x_stats = f"Range: {df[viz.x_column].min():.1f}-{df[viz.x_column].max():.1f}, Mean: {df[viz.x_column].mean():.1f}"
            data_stats['x_stats'] = x_stats
        
        if viz.y_column and viz.y_column in df.columns:
            y_stats = f"Range: {df[viz.y_column].min():.1f}-{df[viz.y_column].max():.1f}, Mean: {df[viz.y_column].mean():.1f}"
            data_stats['y_stats'] = y_stats
        
        analyzer = GenAIAnalyzer()
        summary = analyzer.get_graph_summary(
            viz.graph_type,
            viz.x_column,
            viz.y_column,
            viz.graph_description,
            data_stats
        )
        
        viz.insights = summary
        db.session.commit()
        
        return jsonify({'success': True, 'insights': summary})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Handle file upload and initial processing."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'warning')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'warning')
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
                logger.info(f"Loaded CSV with shape: {df.shape}")
                
                # Get dataset statistics before cleaning
                dataset_stats = get_dataset_stats(df)
                logger.info(f"Dataset stats type: {type(dataset_stats)}, keys: {list(dataset_stats.keys()) if isinstance(dataset_stats, dict) else 'N/A'}")
                
                # Validate dataset_stats is a dictionary
                if not isinstance(dataset_stats, dict):
                    logger.error(f"dataset_stats is not a dict: {type(dataset_stats)}")
                    flash('Error processing dataset statistics', 'danger')
                    return redirect(request.url)
                
                # Clean the data
                df_clean, encoding_mappings = clean_dataframe(df)
                logger.info(f"Cleaned data shape: {df_clean.shape}")
                
                # Create analysis session
                session = AnalysisSession(
                    user_id=current_user.id,
                    filename=filename,
                    dataset_stats=json.dumps(dataset_stats, default=str),
                    encoding_mappings=json.dumps(encoding_mappings, default=str)
                )
                db.session.add(session)
                db.session.commit()
                logger.info(f"Created session ID: {session.id}")
                
                # Get column information
                column_info = get_column_info(df_clean)
                logger.info(f"Column info: {[f'{col['name']}({col['type']})' for col in column_info]}")
                
                # Get visualization suggestions from GenAI
                analyzer = GenAIAnalyzer()
                logger.info("Getting visualization suggestions...")
                suggestions = analyzer.get_visualization_suggestions(column_info, dataset_stats)
                logger.info(f"Got {len(suggestions)} suggestions: {suggestions}")
                
                # Always generate heatmap and box plots (essential visualizations)
                essential_visualizations = [
                    {"type": "heatmap", "x": "all_numerical", "y": "all_numerical", "reason": "Correlation analysis"},
                    {"type": "box", "x": "all_numerical", "reason": "Outlier detection"}
                ]
                
                # Generate essential visualizations first
                for suggestion in essential_visualizations:
                    try:
                        logger.info(f"Generating essential visualization: {suggestion['type']}")
                        graph_data, graph_description = generate_visualization(
                            df_clean, 
                            suggestion['type'], 
                            suggestion['x'], 
                            suggestion.get('y')
                        )
                        
                        viz = Visualization(
                            session_id=session.id,
                            graph_type=suggestion['type'],
                            x_column=suggestion['x'],
                            y_column=suggestion.get('y'),
                            graph_path=graph_data,
                            insights="Essential visualization - correlation and outlier analysis",
                            graph_description=graph_description
                        )
                        db.session.add(viz)
                        logger.info(f"Created {suggestion['type']} visualization")
                    except Exception as e:
                        logger.error(f"Error generating {suggestion['type']}: {str(e)}")
                        flash(f"Error generating {suggestion['type']}: {str(e)}", 'warning')
                        continue
                
                # Generate suggested visualizations (3-5 graphs)
                for suggestion in suggestions[:5]:
                    try:
                        # Validate suggestion structure
                        if not isinstance(suggestion, dict) or 'type' not in suggestion or 'x' not in suggestion:
                            logger.warning(f"Invalid suggestion format: {suggestion}")
                            continue
                            
                        logger.info(f"Generating suggested visualization: {suggestion['type']} for {suggestion['x']}")
                        graph_data, graph_description = generate_visualization(
                            df_clean, 
                            suggestion['type'], 
                            suggestion['x'], 
                            suggestion.get('y')
                        )
                        
                        viz = Visualization(
                            session_id=session.id,
                            graph_type=suggestion['type'],
                            x_column=suggestion['x'],
                            y_column=suggestion.get('y'),
                            graph_path=graph_data,
                            insights="Click 'Generate Insights' for AI analysis",
                            graph_description=graph_description
                        )
                        db.session.add(viz)
                        logger.info(f"Created {suggestion['type']} visualization for {suggestion['x']}")
                    except Exception as e:
                        logger.error(f"Error generating visualization {suggestion.get('type', 'unknown')}: {str(e)}")
                        flash(f"Error generating visualization: {str(e)}", 'warning')
                        continue
                
                db.session.commit()
                flash('File uploaded and analyzed successfully!', 'success')
                logger.info("File processing completed successfully")
                return redirect(url_for('dashboard.view_session', session_id=session.id))
            
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error processing file: {str(e)}", exc_info=True)
                flash(f'Error processing file: {str(e)}', 'danger')
                if os.path.exists(filepath):
                    os.remove(filepath)
                return redirect(request.url)
        
        else:
            flash('Invalid file type. Please upload a CSV file.', 'danger')
            return redirect(request.url)
    
    return render_template('dashboard/upload.html')

@dashboard_bp.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """View analysis session results."""
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('You do not have permission to view this session', 'danger')
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
        flash('Error loading dataset information', 'warning')
    
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
        flash('You do not have permission to view this session', 'danger')
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
        flash('Error loading dataset information', 'warning')
    
    return render_template('dashboard/dataset_info.html', 
                         session=session,
                         dataset_stats=dataset_stats,
                         encoding_mappings=encoding_mappings)

@dashboard_bp.route('/delete_session/<int:session_id>')
@login_required
def delete_session(session_id):
    """Delete an analysis session."""
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('You do not have permission to delete this session', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        # Delete associated visualizations first (due to foreign key constraints)
        Visualization.query.filter_by(session_id=session_id).delete()
        db.session.delete(session)
        db.session.commit()
        flash('Session deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting session: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard.index'))