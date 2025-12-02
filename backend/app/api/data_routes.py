from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import os
import uuid
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
from app.agents.notebook_agent import NotebookAgent
from app.core.logger import AgentLogger

# Define the blueprint
data_bp = Blueprint('data', __name__)
logger = AgentLogger('DataRoutes')

ALLOWED_EXTENSIONS = {'csv', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_dataset_stats(df):
    """Generate stats format compatible with Frontend DataDeck"""
    return {
        'shape': df.shape,
        'columns': df.columns.tolist(),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'missing_values': int(df.isnull().sum().sum()),
        'sample_data': df.head(5).astype(object).where(pd.notnull(df), None).to_dict('records')
    }

# --- 1. UPLOAD ENDPOINT ---
@data_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
            
        if file and allowed_file(file.filename):
            # Secure save
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
            upload_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), unique_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            
            # Read and Analyze
            try:
                df = pd.read_csv(upload_path)
                stats = get_dataset_stats(df)
                
                # Create session in StateManager
                from app.core.state_manager import SessionState
                session_id = SessionState.create_session(
                    user_id=current_user.id,
                    df=df,
                    filename=original_filename
                )
                
                session_data = {
                    'session_id': session_id,
                    'filename': original_filename,
                    'filepath': upload_path,
                    'dataframe': stats,
                    'created_at': datetime.now().isoformat()
                }
                
                logger.log_info('file_uploaded', f"Uploaded {original_filename}", {'session_id': session_id})
                
                return jsonify({
                    'success': True,
                    'session': session_data,
                    'message': 'File uploaded successfully'
                })
                
            except Exception as e:
                logger.log_error('csv_processing_error', str(e))
                return jsonify({'success': False, 'error': f'Corrupt CSV: {str(e)}'}), 400
                
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
    except Exception as e:
        logger.log_error('upload_failed', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

# --- 2. CREATE NOTEBOOK ENDPOINT ---
@data_bp.route('/create', methods=['POST'])
@login_required
def create_notebook():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400

        # Initialize Agent
        agent = NotebookAgent(session_id=session_id)
        
        # We need to reconstruct the dataframe stats context if possible
        # For this fix, we will assume the filename is passed or stored
        # In a real app, you'd fetch session from DB. Here we mock using input or defaults.
        
        result = agent.generate_initial_notebook(
            filename="uploaded_data.csv", # Placeholder name since we don't have DB persistence in this snippet
            analysis_type=data.get('analysis_type', 'comprehensive_eda')
        )
        
        if result['success']:
            notebook = result['data']['notebook']
            # Add ID
            notebook['notebook_id'] = str(uuid.uuid4())
            notebook['title'] = "Exploratory Data Analysis"
            
            # Save notebook to session state
            from app.core.state_manager import SessionState
            SessionState.add_notebook(session_id, notebook)
            
            return jsonify({
                'success': True,
                'notebook': notebook
            })
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.log_error('notebook_creation_failed', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500