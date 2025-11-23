from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, send_file
from flask_login import login_required, current_user
import os
import pandas as pd
import json
from werkzeug.utils import secure_filename
from datetime import datetime
from app.dashboard.models import AnalysisSession, Visualization
from app.utils.data_utils import validate_csv, get_dataset_stats, get_smart_context, clean_dataframe
from app.utils.viz_utils import generate_visualization
from app.utils.genai_utils import GenAIAnalyzer
from app.extensions import db
import logging
import io
import re
from fpdf import FPDF
import markdown

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates/dashboard')

# --- Helper Functions for PDF Report ---

def clean_markdown(text):
    """
    Simple utility to strip Markdown formatting for the PDF.
    Converts **bold** to plain text and handles lists.
    """
    if not text:
        return ""
    # Remove ** and __ (bold/italics)
    text = re.sub(r'\*\*|__', '', text)
    # Replace markdown list bullets with dots
    text = text.replace('* ', '• ')
    text = text.replace('- ', '• ')
    return text

class PDFReport(FPDF):
    def header(self):
        # Title Header
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(30, 27, 75)  # Deep Indigo
        self.cell(0, 10, 'AI-Powered Data Analysis Report', border=False, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(5)

    def footer(self):
        # Footer with page number
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

# --- Routes ---

@dashboard_bp.route('/')
@login_required
def index():
    """User dashboard showing analysis history."""
    sessions = AnalysisSession.query.filter_by(user_id=current_user.id).order_by(AnalysisSession.created_at.desc()).all()
    
    # Calculate stats for the dashboard
    total_sessions = len(sessions)
    total_visualizations = 0
    recent_activity = []
    
    for session in sessions[:5]:  # Last 5 sessions
        viz_count = Visualization.query.filter_by(session_id=session.id).count()
        total_visualizations += viz_count
        recent_activity.append({
            'session': session,
            'viz_count': viz_count,
            'date': session.created_at.strftime('%Y-%m-%d')
        })
    
    return render_template('dashboard/index.html', 
                         sessions=sessions,
                         total_sessions=total_sessions,
                         total_visualizations=total_visualizations,
                         recent_activity=recent_activity)

@dashboard_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Handle file upload with enhanced AI analysis."""
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
                # Read and process data
                df = pd.read_csv(filepath)
                logger.info(f"Loaded CSV with shape: {df.shape}")
                
                # Get dataset statistics
                dataset_stats = get_dataset_stats(df)
                
                # Generate smart context (limited data exposure for AI)
                smart_context = get_smart_context(df)
                logger.info(f"Generated smart context with {smart_context.get('constraints', {}).get('max_rows_exposed', 0)} exposed rows")
                
                # Clean the data for visualization
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
                
                # Initialize AI analyzer
                analyzer = GenAIAnalyzer()
                
                # Get comprehensive AI analysis
                comprehensive_analysis = analyzer.get_comprehensive_analysis(smart_context)
                logger.info("Generated comprehensive AI analysis")
                
                # Get data quality insights
                quality_insights = analyzer.get_data_quality_insights(smart_context)
                
                # Get visualization suggestions
                suggestions = analyzer.get_visualization_suggestions(smart_context)
                
                # Generate essential visualizations (Heatmap, Boxplot)
                essential_viz = [
                    {"type": "heatmap", "x": "all_numerical", "y": "all_numerical", "reason": "Correlation analysis"},
                    {"type": "box", "x": "all_numerical", "reason": "Outlier detection"}
                ]
                
                generated_viz = []
                
                # Generate Essential visualizations
                for viz_spec in essential_viz:
                    try:
                        graph_data, graph_description = generate_visualization(
                            df_clean, viz_spec['type'], viz_spec['x'], viz_spec.get('y')
                        )
                        
                        # --- FIX: HANDLE TUPLE RETURN (Image, Warning) ---
                        if isinstance(graph_data, tuple):
                            graph_data = graph_data[0]  # Take only the image path
                        # -------------------------------------------------
                        
                        viz = Visualization(
                            session_id=session.id,
                            graph_type=viz_spec['type'],
                            x_column=viz_spec['x'],
                            y_column=viz_spec.get('y'),
                            graph_path=graph_data,
                            insights="Essential visualization",
                            graph_description=graph_description
                        )
                        db.session.add(viz)
                        generated_viz.append(viz_spec['type'])
                    except Exception as e:
                        logger.error(f"Error generating {viz_spec['type']}: {str(e)}")
                        continue
                
                # Generate AI-suggested visualizations
                for suggestion in suggestions[:4]:  # Max 4 suggestions
                    try:
                        graph_data, graph_description = generate_visualization(
                            df_clean, suggestion['type'], suggestion['x'], suggestion.get('y')
                        )
                        
                        # --- FIX: HANDLE TUPLE RETURN ---
                        if isinstance(graph_data, tuple):
                            graph_data = graph_data[0]
                        # --------------------------------
                        
                        viz = Visualization(
                            session_id=session.id,
                            graph_type=suggestion['type'],
                            x_column=suggestion['x'],
                            y_column=suggestion.get('y'),
                            graph_path=graph_data,
                            insights=suggestion.get('reason', 'AI-suggested visualization'),
                            graph_description=graph_description
                        )
                        db.session.add(viz)
                        generated_viz.append(suggestion['type'])
                    except Exception as e:
                        logger.error(f"Error generating {suggestion.get('type')}: {str(e)}")
                        continue
                
                db.session.commit()
                
                # Update session with AI results
                session.dataset_stats = json.dumps({
                    **dataset_stats,
                    'ai_analysis': comprehensive_analysis,
                    'quality_insights': quality_insights,
                    'smart_context': smart_context,
                    'generated_visualizations': generated_viz
                }, default=str)
                db.session.commit()
                
                flash('File uploaded and comprehensively analyzed!', 'success')
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
    """View enhanced analysis session results with Markdown rendering."""
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('Permission denied', 'danger')
        return redirect(url_for('dashboard.index'))
    
    visualizations = Visualization.query.filter_by(session_id=session_id).all()
    
    dataset_stats = {}
    encoding_mappings = {}
    ai_analysis = {}
    quality_insights = {}
    smart_context = {}
    
    try:
        if session.dataset_stats:
            full_stats = json.loads(session.dataset_stats)
            dataset_stats = {
                'basic_info': full_stats.get('basic_info', {}),
                'column_details': full_stats.get('column_details', {}),
                'data_types_summary': full_stats.get('data_types_summary', {})
            }
            ai_analysis = full_stats.get('ai_analysis', {})
            quality_insights = full_stats.get('quality_insights', {})
            smart_context = full_stats.get('smart_context', {})
            
            # Convert Markdown to HTML for display
            if 'sections' in ai_analysis and isinstance(ai_analysis['sections'], list):
                ai_analysis['sections'] = [markdown.markdown(s) for s in ai_analysis['sections']]
            
            if 'analysis' in ai_analysis:
                ai_analysis['analysis'] = markdown.markdown(ai_analysis['analysis'])
                
            if 'quality_report' in quality_insights:
                quality_insights['quality_report'] = markdown.markdown(quality_insights['quality_report'])
        
        if session.encoding_mappings:
            encoding_mappings = json.loads(session.encoding_mappings)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error parsing session data: {str(e)}")
        flash('Error loading session information', 'warning')
    
    return render_template('dashboard/session.html', 
                         session=session, 
                         visualizations=visualizations,
                         dataset_stats=dataset_stats,
                         encoding_mappings=encoding_mappings,
                         ai_analysis=ai_analysis,
                         quality_insights=quality_insights,
                         smart_context=smart_context)

@dashboard_bp.route('/dataset_info/<int:session_id>')
@login_required
def dataset_info(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('Permission denied', 'danger')
        return redirect(url_for('dashboard.index'))
    
    dataset_stats = {}
    encoding_mappings = {}
    smart_context = {}
    
    try:
        if session.dataset_stats:
            full_stats = json.loads(session.dataset_stats)
            dataset_stats = {
                'basic_info': full_stats.get('basic_info', {}),
                'column_details': full_stats.get('column_details', {}),
                'sample_data': full_stats.get('sample_data', []),
                'data_types_summary': full_stats.get('data_types_summary', {})
            }
            smart_context = full_stats.get('smart_context', {})
        
        if session.encoding_mappings:
            encoding_mappings = json.loads(session.encoding_mappings)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error loading dataset info: {str(e)}")
        flash('Error loading dataset information', 'warning')
    
    return render_template('dashboard/dataset_info.html', 
                         session=session,
                         dataset_stats=dataset_stats,
                         encoding_mappings=encoding_mappings,
                         smart_context=smart_context)

@dashboard_bp.route('/delete_session/<int:session_id>')
@login_required
def delete_session(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('Permission denied', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        Visualization.query.filter_by(session_id=session_id).delete()
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], session.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        db.session.delete(session)
        db.session.commit()
        flash('Session deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting session: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/generate_summary/<int:viz_id>')
@login_required
def generate_summary(viz_id):
    viz = Visualization.query.get_or_404(viz_id)
    session = AnalysisSession.query.get_or_404(viz.session_id)
    
    if session.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], session.filename)
        df = pd.read_csv(filepath)
        df_clean, _ = clean_dataframe(df)
        
        data_stats = {}
        if viz.x_column in df_clean.columns:
            if pd.api.types.is_numeric_dtype(df_clean[viz.x_column]):
                data_stats['x_stats'] = f"Range: {df_clean[viz.x_column].min():.2f}-{df_clean[viz.x_column].max():.2f}, Mean: {df_clean[viz.x_column].mean():.2f}"
            else:
                top_values = df_clean[viz.x_column].value_counts().head(3).to_dict()
                data_stats['x_stats'] = f"Top values: {', '.join([f'{k}({v})' for k, v in top_values.items()])}"
        
        if viz.y_column and viz.y_column in df_clean.columns:
            if pd.api.types.is_numeric_dtype(df_clean[viz.y_column]):
                data_stats['y_stats'] = f"Range: {df_clean[viz.y_column].min():.2f}-{df_clean[viz.y_column].max():.2f}, Mean: {df_clean[viz.y_column].mean():.2f}"
            else:
                top_values = df_clean[viz.y_column].value_counts().head(3).to_dict()
                data_stats['y_stats'] = f"Top values: {', '.join([f'{k}({v})' for k, v in top_values.items()])}"
        
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
        
        summary_html = markdown.markdown(summary)
        return jsonify({'success': True, 'insights': summary_html})
    
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return jsonify({'error': f'Failed: {str(e)}'}), 500

@dashboard_bp.route('/ai_analysis/<int:session_id>')
@login_required
def get_ai_analysis(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        if session.dataset_stats:
            full_stats = json.loads(session.dataset_stats)
            return jsonify({
                'success': True,
                'comprehensive_analysis': full_stats.get('ai_analysis', {}),
                'quality_insights': full_stats.get('quality_insights', {}),
                'smart_context': full_stats.get('smart_context', {})
            })
        return jsonify({'error': 'No AI analysis available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/refresh_analysis/<int:session_id>')
@login_required
def refresh_analysis(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('Permission denied', 'danger')
        return redirect(url_for('dashboard.view_session', session_id=session_id))
    
    try:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], session.filename)
        if not os.path.exists(filepath):
            flash('Original data file not found', 'danger')
            return redirect(url_for('dashboard.view_session', session_id=session_id))
        
        df = pd.read_csv(filepath)
        smart_context = get_smart_context(df)
        
        analyzer = GenAIAnalyzer()
        comprehensive_analysis = analyzer.get_comprehensive_analysis(smart_context)
        quality_insights = analyzer.get_data_quality_insights(smart_context)
        
        current_stats = json.loads(session.dataset_stats) if session.dataset_stats else {}
        current_stats.update({
            'ai_analysis': comprehensive_analysis,
            'quality_insights': quality_insights,
            'smart_context': smart_context,
            'refreshed_at': datetime.utcnow().isoformat()
        })
        
        session.dataset_stats = json.dumps(current_stats, default=str)
        db.session.commit()
        flash('AI analysis refreshed successfully!', 'success')
        
    except Exception as e:
        logger.error(f"Error refreshing analysis: {str(e)}")
        flash(f'Error refreshing analysis: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard.view_session', session_id=session_id))

@dashboard_bp.route('/download_report/<int:session_id>')
@login_required
def download_report(session_id):
    """Generate and download a PDF report using FPDF2 with 'Search & Find' image logic."""
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('Permission denied', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        # 1. Setup PDF
        pdf = PDFReport()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # 2. Meta Info
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(50)
        pdf.cell(0, 6, f"Filename: {session.filename}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Date: {session.created_at.strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Analyst: {current_user.username}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)

        # 3. Stats
        stats = {}
        if session.dataset_stats:
            stats = json.loads(session.dataset_stats)
            basic = stats.get('basic_info', {})
            
            pdf.set_fill_color(243, 244, 246)
            pdf.rect(x=pdf.get_x(), y=pdf.get_y(), w=190, h=25, style='F')
            pdf.set_y(pdf.get_y() + 5)
            
            pdf.set_font('Helvetica', 'B', 14)
            pdf.set_text_color(79, 70, 229) 
            pdf.cell(63, 8, str(basic.get('total_rows', 'N/A')), align='C', border=0, new_x="RIGHT", new_y="TOP")
            pdf.cell(63, 8, str(basic.get('total_columns', 'N/A')), align='C', border=0, new_x="RIGHT", new_y="TOP")
            pdf.cell(63, 8, str(basic.get('missing_values', 'N/A')), align='C', border=0, new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(100)
            pdf.cell(63, 6, "Total Rows", align='C', border=0)
            pdf.cell(63, 6, "Total Columns", align='C', border=0)
            pdf.cell(63, 6, "Missing Values", align='C', border=0, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(15)

        # 4. Text Analysis
        if session.dataset_stats:
            pdf.set_font('Helvetica', 'B', 14)
            pdf.set_text_color(30, 27, 75)
            pdf.cell(0, 10, '1. Executive Summary', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            
            ai_text = stats.get('ai_analysis', {}).get('analysis', 'No analysis available.')
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(50)
            pdf.multi_cell(0, 7, clean_markdown(ai_text))
            pdf.ln(10)

            pdf.set_font('Helvetica', 'B', 14)
            pdf.set_text_color(30, 27, 75)
            pdf.cell(0, 10, '2. Data Quality Assessment', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            
            quality_text = stats.get('quality_insights', {}).get('quality_report', 'No quality report available.')
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(50)
            pdf.multi_cell(0, 7, clean_markdown(quality_text))
            pdf.ln(10)

        # 5. Visualizations
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(30, 27, 75)
        pdf.cell(0, 10, '3. Visualizations & Insights', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        visualizations = Visualization.query.filter_by(session_id=session_id).all()
        
        # --- SEARCH & FIND LOGIC ---
        static_root = os.path.join(current_app.root_path, 'static')

        for viz in visualizations:
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_text_color(79, 70, 229)
            title = f"{viz.graph_type.title()} Chart: {viz.x_column}"
            if viz.y_column:
                title += f" vs {viz.y_column}"
            pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
            
            # 1. Extract filename
            if not viz.graph_path:
                continue
            target_filename = os.path.basename(viz.graph_path)
            print(f"DEBUG: Hunting for file: {target_filename}")
            
            final_path = None
            
            # 2. Walk through static dir
            for root, dirs, files in os.walk(static_root):
                if target_filename in files:
                    final_path = os.path.join(root, target_filename)
                    print(f"DEBUG: FOUND IT! {final_path}")
                    break
            
            # 3. Render if found
            if final_path:
                try:
                    # Center image
                    x_pos = (210 - 150) / 2
                    pdf.image(final_path, x=x_pos, w=150)
                    pdf.ln(5)
                except Exception as img_err:
                    print(f"DEBUG: Error adding image: {img_err}")
                    pdf.set_font('Helvetica', 'I', 10)
                    pdf.set_text_color(220, 38, 38)
                    pdf.cell(0, 10, "[Error rendering image file]", new_x="LMARGIN", new_y="NEXT")
            else:
                print(f"DEBUG: Could not find {target_filename} anywhere in {static_root}")
                pdf.set_font('Helvetica', 'I', 10)
                pdf.set_text_color(220, 38, 38)
                pdf.cell(0, 10, f"[Image file '{target_filename}' not found]", new_x="LMARGIN", new_y="NEXT")

            # 4. Insight
            if viz.insights:
                pdf.set_fill_color(248, 250, 252)
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(50)
                pdf.multi_cell(0, 6, "AI Insight: " + clean_markdown(viz.insights), fill=True)
                pdf.ln(10)
            
            if pdf.get_y() > 220:
                pdf.add_page()

        pdf_content = pdf.output()
        return send_file(
            io.BytesIO(pdf_content),
            as_attachment=True,
            download_name=f"Report_{session.filename}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('dashboard.view_session', session_id=session_id))

@dashboard_bp.route('/quick_analyze', methods=['POST'])
@login_required
def quick_analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not validate_csv(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        filename = secure_filename(file.filename)
        temp_path = os.path.join('/tmp', f"quick_{current_user.id}_{filename}")
        file.save(temp_path)
        df = pd.read_csv(temp_path)
        smart_context = get_smart_context(df)
        analyzer = GenAIAnalyzer()
        quick_analysis = analyzer.get_comprehensive_analysis(smart_context)
        os.remove(temp_path)
        return jsonify({
            'success': True,
            'analysis': quick_analysis,
            'dataset_info': {'rows': len(df), 'columns': len(df.columns), 'shape': [len(df), len(df.columns)]}
        })
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/bulk_insights/<int:session_id>')
@login_required
def generate_bulk_insights(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    try:
        visualizations = Visualization.query.filter_by(session_id=session_id).all()
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], session.filename)
        df = pd.read_csv(filepath)
        df_clean, _ = clean_dataframe(df)
        analyzer = GenAIAnalyzer()
        results = []
        for viz in visualizations:
            if viz.insights and viz.insights != "Click 'Generate Insights' for AI analysis":
                results.append({'viz_id': viz.id, 'status': 'already_generated'})
                continue
            try:
                data_stats = {}
                if viz.x_column in df_clean.columns:
                    if pd.api.types.is_numeric_dtype(df_clean[viz.x_column]):
                         data_stats['x_stats'] = f"Range: {df_clean[viz.x_column].min():.1f}-{df_clean[viz.x_column].max():.1f}"
                summary = analyzer.get_graph_summary(viz.graph_type, viz.x_column, viz.y_column, viz.graph_description, data_stats)
                viz.insights = summary
                results.append({'viz_id': viz.id, 'status': 'generated'})
            except Exception as e:
                results.append({'viz_id': viz.id, 'status': 'failed', 'error': str(e)})
        db.session.commit()
        return jsonify({'success': True, 'summary': {'total': len(visualizations), 'generated': len([r for r in results if r['status'] == 'generated'])}})
    except Exception as e:
        logger.error(f"Error generating bulk insights: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/session_stats/<int:session_id>')
@login_required
def session_stats(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    try:
        visualizations = Visualization.query.filter_by(session_id=session_id).all()
        viz_types = {}
        for viz in visualizations:
            viz_types[viz.graph_type] = viz_types.get(viz.graph_type, 0) + 1
        insights_generated = len([v for v in visualizations if v.insights and v.insights != "Click 'Generate Insights' for AI analysis"])
        return jsonify({
            'success': True,
            'stats': {
                'total_visualizations': len(visualizations),
                'insights_generated': insights_generated,
                'visualization_types': viz_types,
                'session_created': session.created_at.isoformat(),
                'filename': session.filename
            }
        })
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/compare_sessions', methods=['GET', 'POST'])
@login_required
def compare_sessions():
    if request.method == 'POST':
        session_ids = request.form.getlist('session_ids')
        if len(session_ids) < 2:
            flash('Please select at least 2 sessions to compare', 'warning')
            return redirect(url_for('dashboard.compare_sessions'))
        sessions = []
        for session_id in session_ids:
            session = AnalysisSession.query.get(session_id)
            if session and session.user_id == current_user.id:
                sessions.append(session)
        return render_template('dashboard/compare.html', sessions=sessions)
    user_sessions = AnalysisSession.query.filter_by(user_id=current_user.id).order_by(AnalysisSession.created_at.desc()).all()
    return render_template('dashboard/compare_sessions.html', sessions=user_sessions)

@dashboard_bp.route('/api/session/<int:session_id>/visualizations')
@login_required
def api_session_visualizations(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    visualizations = Visualization.query.filter_by(session_id=session_id).all()
    viz_data = []
    for viz in visualizations:
        viz_data.append({
            'id': viz.id,
            'graph_type': viz.graph_type,
            'x_column': viz.x_column,
            'y_column': viz.y_column,
            'graph_path': viz.graph_path,
            'insights': viz.insights,
            'graph_description': viz.graph_description,
            'created_at': viz.created_at.isoformat()
        })
    return jsonify({
        'success': True,
        'session_id': session_id,
        'filename': session.filename,
        'visualizations': viz_data,
        'count': len(viz_data)
    })