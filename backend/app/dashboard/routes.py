from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, send_file
from flask_login import login_required, current_user
import os
import pandas as pd
import numpy as np
import json
from werkzeug.utils import secure_filename
from datetime import datetime
from app.dashboard.models import AnalysisSession, Visualization
from app.utils.data_utils import validate_csv, get_dataset_stats, get_smart_context, clean_dataframe
from app.utils.viz_utils import generate_visualization
from app.utils.genai_utils import GenAIAnalyzer
from app.utils.analysis_agents import FeatureEngineerAgent, DynamicVisualizerAgent
from app.extensions import db
import logging
import io
import re
from fpdf import FPDF
import markdown

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates/dashboard')

# =========================================
# PDF REPORT GENERATION HELPERS
# =========================================

def clean_markdown(text):
    """
    Sanitizes text to ensure it works with FPDF's standard Helvetica font (Latin-1).
    Replaces special Unicode characters with standard ASCII equivalents.
    """
    if not text:
        return ""
    
    # 1. Remove Markdown bold/italics (**text** -> text)
    text = re.sub(r'\*\*|__', '', text)
    
    # 2. Replace incompatible Unicode characters
    replacements = {
        '•': '-', '–': '-', '—': '-', 
        '“': '"', '”': '"', '‘': "'", '’': "'", 
        '…': '...', '* ': '- '
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
        
    # 3. Final Safety Net: Force Latin-1 encoding
    return text.encode('latin-1', 'replace').decode('latin-1')

class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(30, 27, 75)  # Deep Indigo
        self.cell(0, 10, 'AI-Powered Data Analysis Report', border=False, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

# =========================================
# DATA HELPERS
# =========================================

def get_session_dataframe(session):
    """
    Smart Loader: Tries to load the 'enriched' dataset first (engineered features),
    falls back to the original if not found.
    """
    upload_dir = current_app.config['UPLOAD_FOLDER']
    original_path = os.path.join(upload_dir, session.filename)
    enriched_path = os.path.join(upload_dir, f"enriched_{session.filename}")
    
    if os.path.exists(enriched_path):
        return pd.read_csv(enriched_path)
    return pd.read_csv(original_path)

# =========================================
# ROUTES
# =========================================

@dashboard_bp.route('/')
@login_required
def index():
    """User dashboard showing analysis history."""
    sessions = AnalysisSession.query.filter_by(user_id=current_user.id).order_by(AnalysisSession.created_at.desc()).all()
    
    total_sessions = len(sessions)
    total_visualizations = 0
    recent_activity = []
    
    for session in sessions[:5]:
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
    """
    CORE LOGIC: 
    1. Feature Engineering (AI adds columns)
    2. Dynamic Visualization (AI chooses graphs)
    3. Comprehensive Analysis (AI explains data)
    """
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
                # 1. Load Data
                df = pd.read_csv(filepath)
                logger.info(f"Loaded CSV: {df.shape}")
                
                # 2. AI Feature Engineering (The "Prep" Agent)
                # This creates a NEW dataframe with extra columns derived by AI
                feature_agent = FeatureEngineerAgent()
                df_enriched, new_cols = feature_agent.generate_features(df)
                
                # 3. Save Enriched Data (Preserving Original)
                enriched_filename = f"enriched_{filename}"
                enriched_path = os.path.join(upload_dir, enriched_filename)
                df_enriched.to_csv(enriched_path, index=False)
                
                if new_cols:
                    logger.info(f"AI engineered {len(new_cols)} new features: {new_cols}")

                # 4. Analysis Setup (Using Enriched Data)
                dataset_stats = get_dataset_stats(df_enriched)
                smart_context = get_smart_context(df_enriched)
                df_clean, encoding_mappings = clean_dataframe(df_enriched)
                
                # 5. Create Session
                session = AnalysisSession(
                    user_id=current_user.id,
                    filename=filename, # We reference the original filename
                    dataset_stats=json.dumps(dataset_stats, default=str),
                    encoding_mappings=json.dumps(encoding_mappings, default=str)
                )
                db.session.add(session)
                db.session.commit()
                
                # 6. Dynamic Visualization (The "Artist" Agent)
                viz_agent = DynamicVisualizerAgent()
                plot_configs = viz_agent.generate_plots(df_enriched)
                
                # Fallback if AI fails to generate JSON
                if not plot_configs:
                    plot_configs = [
                        {"type": "heatmap", "x": "all_numerical", "y": "all_numerical", "reason": "Correlation Overview"},
                        {"type": "histogram", "x": df_enriched.select_dtypes(include=np.number).columns[0], "reason": "Distribution check"}
                    ]

                generated_viz = []
                
                # 7. Generate Graphs based on AI instructions
                for config in plot_configs:
                    try:
                        graph_type = config.get('type', 'bar')
                        x_col = config.get('x')
                        y_col = config.get('y')
                        reason = config.get('reason', 'AI Suggested Insight')
                        
                        # Validation: Ensure columns exist
                        if x_col != 'all_numerical' and x_col not in df_clean.columns:
                            continue
                        if y_col and y_col != 'all_numerical' and y_col not in df_clean.columns:
                            continue

                        # Generate Plot
                        graph_data, graph_description = generate_visualization(
                            df_clean, graph_type, x_col, y_col
                        )
                        
                        # BUG FIX: Handle tuple return (Image Path, Warning Message)
                        if isinstance(graph_data, tuple):
                            graph_data = graph_data[0]
                        
                        viz = Visualization(
                            session_id=session.id,
                            graph_type=graph_type,
                            x_column=x_col,
                            y_column=y_col,
                            graph_path=graph_data,
                            insights=reason,
                            graph_description=graph_description
                        )
                        db.session.add(viz)
                        generated_viz.append(graph_type)
                    except Exception as e:
                        logger.error(f"Error generating {config}: {str(e)}")
                        continue
                
                db.session.commit()
                
                # 8. Generate Text Analysis (The "Storyteller")
                analyzer = GenAIAnalyzer()
                comprehensive_analysis = analyzer.get_comprehensive_analysis(smart_context)
                quality_insights = analyzer.get_data_quality_insights(smart_context)
                
                # Update session
                session.dataset_stats = json.dumps({
                    **dataset_stats,
                    'ai_analysis': comprehensive_analysis,
                    'quality_insights': quality_insights,
                    'smart_context': smart_context,
                    'generated_visualizations': generated_viz,
                    'engineered_features': new_cols
                }, default=str)
                db.session.commit()
                
                msg = f'Analysis Complete! AI engineered {len(new_cols)} new features.' if new_cols else 'Analysis Complete!'
                flash(msg, 'success')
                return redirect(url_for('dashboard.view_session', session_id=session.id))
            
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error processing file: {str(e)}", exc_info=True)
                flash(f'Error processing file: {str(e)}', 'danger')
                if os.path.exists(filepath):
                    os.remove(filepath)
                return redirect(request.url)
        else:
            flash('Invalid file type.', 'danger')
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
            # Extract basics
            dataset_stats = {
                'basic_info': full_stats.get('basic_info', {}),
                'column_details': full_stats.get('column_details', {}),
                'data_types_summary': full_stats.get('data_types_summary', {})
            }
            ai_analysis = full_stats.get('ai_analysis', {})
            quality_insights = full_stats.get('quality_insights', {})
            smart_context = full_stats.get('smart_context', {})
            
            # Convert AI Markdown to HTML for display
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
    except Exception as e:
        logger.error(f"Error loading info: {e}")
    
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
        
        # Delete Original and Enriched files
        upload_dir = current_app.config['UPLOAD_FOLDER']
        original_path = os.path.join(upload_dir, session.filename)
        enriched_path = os.path.join(upload_dir, f"enriched_{session.filename}")
        
        if os.path.exists(original_path): os.remove(original_path)
        if os.path.exists(enriched_path): os.remove(enriched_path)
        
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
    """Generate AI summary for a specific visualization."""
    viz = Visualization.query.get_or_404(viz_id)
    session = AnalysisSession.query.get_or_404(viz.session_id)
    
    if session.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        # Load dataframe (prefer enriched)
        df = get_session_dataframe(session)
        df_clean, _ = clean_dataframe(df)
        
        data_stats = {}
        if viz.x_column in df_clean.columns:
            if pd.api.types.is_numeric_dtype(df_clean[viz.x_column]):
                data_stats['x_stats'] = f"Range: {df_clean[viz.x_column].min():.2f}-{df_clean[viz.x_column].max():.2f}, Mean: {df_clean[viz.x_column].mean():.2f}"
            else:
                top = df_clean[viz.x_column].value_counts().head(3).to_dict()
                data_stats['x_stats'] = f"Top: {', '.join([f'{k}({v})' for k,v in top.items()])}"
        
        if viz.y_column and viz.y_column in df_clean.columns:
            if pd.api.types.is_numeric_dtype(df_clean[viz.y_column]):
                data_stats['y_stats'] = f"Range: {df_clean[viz.y_column].min():.2f}-{df_clean[viz.y_column].max():.2f}, Mean: {df_clean[viz.y_column].mean():.2f}"
        
        analyzer = GenAIAnalyzer()
        summary = analyzer.get_graph_summary(
            viz.graph_type, viz.x_column, viz.y_column, 
            viz.graph_description, data_stats
        )
        
        viz.insights = summary
        db.session.commit()
        
        # Return HTML for display
        return jsonify({'success': True, 'insights': markdown.markdown(summary)})
    
    except Exception as e:
        logger.error(f"Error summary: {e}")
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/ai_analysis/<int:session_id>')
@login_required
def get_ai_analysis(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id: return jsonify({'error': 'Denied'}), 403
    try:
        if session.dataset_stats:
            full_stats = json.loads(session.dataset_stats)
            return jsonify({
                'success': True,
                'comprehensive_analysis': full_stats.get('ai_analysis', {}),
                'quality_insights': full_stats.get('quality_insights', {}),
                'smart_context': full_stats.get('smart_context', {})
            })
        return jsonify({'error': 'No analysis'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/refresh_analysis/<int:session_id>')
@login_required
def refresh_analysis(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id: return redirect(url_for('dashboard.index'))
    
    try:
        # Load Enriched Data if available
        df = get_session_dataframe(session)
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
        flash('Refreshed!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    
    return redirect(url_for('dashboard.view_session', session_id=session_id))

@dashboard_bp.route('/download_report/<int:session_id>')
@login_required
def download_report(session_id):
    """
    Robust PDF Generator.
    1. Uses 'fpdf2' (Pure Python) to avoid system dependency crashes.
    2. Uses 'os.walk' to find images regardless of path issues.
    3. Uses 'clean_markdown' to prevent encoding crashes.
    """
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id: return redirect(url_for('dashboard.index'))
    
    try:
        pdf = PDFReport()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Header
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(50)
        pdf.cell(0, 6, f"Filename: {session.filename}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Date: {session.created_at.strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)

        stats = json.loads(session.dataset_stats) if session.dataset_stats else {}
        
        # Executive Summary
        if stats:
            pdf.set_font('Helvetica', 'B', 14)
            pdf.set_text_color(30, 27, 75)
            pdf.cell(0, 10, '1. Executive Summary', new_x="LMARGIN", new_y="NEXT")
            
            ai_text = stats.get('ai_analysis', {}).get('analysis', 'N/A')
            clean_text = clean_markdown(ai_text)
            
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(50)
            pdf.multi_cell(0, 7, clean_text)
            pdf.ln(5)

            # Data Quality
            pdf.set_font('Helvetica', 'B', 14)
            pdf.set_text_color(30, 27, 75)
            pdf.cell(0, 10, '2. Data Quality', new_x="LMARGIN", new_y="NEXT")
            
            q_text = stats.get('quality_insights', {}).get('quality_report', 'N/A')
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(50)
            pdf.multi_cell(0, 7, clean_markdown(q_text))
            pdf.ln(10)

        # Visualizations with Nuclear Image Search
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(30, 27, 75)
        pdf.cell(0, 10, '3. Visualizations', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        visualizations = Visualization.query.filter_by(session_id=session_id).all()
        static_root = os.path.join(current_app.root_path, 'static')

        for viz in visualizations:
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_text_color(79, 70, 229)
            title = f"{viz.graph_type.title()}: {viz.x_column}" + (f" vs {viz.y_column}" if viz.y_column else "")
            pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
            
            # Find Image
            target_filename = os.path.basename(viz.graph_path) if viz.graph_path else ""
            final_path = None
            
            for root, _, files in os.walk(static_root):
                if target_filename in files:
                    final_path = os.path.join(root, target_filename)
                    break
            
            if final_path:
                try:
                    x_pos = (210 - 150) / 2
                    pdf.image(final_path, x=x_pos, w=150)
                    pdf.ln(5)
                except:
                    pdf.cell(0, 10, "[Error rendering image]", new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.set_font('Helvetica', 'I', 10)
                pdf.cell(0, 10, "[Image file not found]", new_x="LMARGIN", new_y="NEXT")

            if viz.insights:
                pdf.set_fill_color(248, 250, 252)
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(50)
                pdf.multi_cell(0, 6, clean_markdown(viz.insights), fill=True)
                pdf.ln(10)
            
            if pdf.get_y() > 220: pdf.add_page()

        return send_file(
            io.BytesIO(pdf.output()),
            as_attachment=True,
            download_name=f"Report_{session.filename}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"PDF Gen Error: {e}")
        flash("Error generating report", "danger")
        return redirect(url_for('dashboard.view_session', session_id=session_id))

@dashboard_bp.route('/bulk_insights/<int:session_id>')
@login_required
def generate_bulk_insights(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id: return jsonify({'error': 'Denied'}), 403
    try:
        vizs = Visualization.query.filter_by(session_id=session_id).all()
        df = get_session_dataframe(session) # Use enriched data
        df_clean, _ = clean_dataframe(df)
        analyzer = GenAIAnalyzer()
        results = []
        
        for viz in vizs:
            if viz.insights and "Click" not in viz.insights:
                results.append({'viz_id': viz.id, 'status': 'done'})
                continue
            try:
                stats = {}
                if viz.x_column in df_clean.columns:
                    if pd.api.types.is_numeric_dtype(df_clean[viz.x_column]):
                        stats['x'] = f"Range: {df_clean[viz.x_column].min():.1f}-{df_clean[viz.x_column].max():.1f}"
                summary = analyzer.get_graph_summary(viz.graph_type, viz.x_column, viz.y_column, viz.graph_description, stats)
                viz.insights = summary
                results.append({'viz_id': viz.id, 'status': 'generated'})
            except Exception as e:
                results.append({'viz_id': viz.id, 'status': 'failed', 'error': str(e)})
        db.session.commit()
        return jsonify({'success': True, 'summary': {'generated': len([r for r in results if r['status']=='generated'])}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/quick_analyze', methods=['POST'])
@login_required
def quick_analyze():
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'No selection'}), 400
    
    try:
        filename = secure_filename(file.filename)
        temp_path = os.path.join('/tmp', f"quick_{current_user.id}_{filename}")
        file.save(temp_path)
        df = pd.read_csv(temp_path)
        # Run Quick Feature Engineering
        feature_agent = FeatureEngineerAgent()
        df_enriched, _ = feature_agent.generate_features(df)
        
        smart_context = get_smart_context(df_enriched)
        analyzer = GenAIAnalyzer()
        quick_analysis = analyzer.get_comprehensive_analysis(smart_context)
        
        os.remove(temp_path)
        return jsonify({'success': True, 'analysis': quick_analysis})
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/session_stats/<int:session_id>')
@login_required
def session_stats(session_id):
    # (Standard stats logic - kept simple for brevity as it's standard)
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id: return jsonify({'error': 'Denied'}), 403
    vizs = Visualization.query.filter_by(session_id=session_id).all()
    return jsonify({'success': True, 'stats': {'total': len(vizs)}})

@dashboard_bp.route('/compare_sessions', methods=['GET', 'POST'])
@login_required
def compare_sessions():
    # (Standard compare logic)
    if request.method == 'POST':
        ids = request.form.getlist('session_ids')
        sessions = [AnalysisSession.query.get(i) for i in ids if AnalysisSession.query.get(i).user_id == current_user.id]
        return render_template('dashboard/compare.html', sessions=sessions)
    all_sessions = AnalysisSession.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard/compare_sessions.html', sessions=all_sessions)

@dashboard_bp.route('/api/session/<int:session_id>/visualizations')
@login_required
def api_session_visualizations(session_id):
    # (Standard API logic)
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id: return jsonify({'error': 'Denied'}), 403
    vizs = Visualization.query.filter_by(session_id=session_id).all()
    return jsonify({
        'success': True, 
        'visualizations': [{
            'id': v.id, 'type': v.graph_type, 'path': v.graph_path, 'insights': v.insights
        } for v in vizs]
    })