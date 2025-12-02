from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import os
import uuid
import json
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
from app.agents.notebook_agent import NotebookAgent
from app.core.logger import AgentLogger

notebook_bp = Blueprint('notebook', __name__)
logger = AgentLogger('NotebookRoutes')

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
@notebook_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
            
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
            upload_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), unique_filename)
            
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            
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
                
                # Calls the new log_info method in your logger
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
@notebook_bp.route('/create', methods=['POST'])
@login_required
async def create_notebook():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400

        # Get dataframe to generate stats
        from app.core.state_manager import SessionState
        df = SessionState.get_dataframe(session_id)
        stats = get_dataset_stats(df) if df is not None else None

        agent = NotebookAgent(session_id=session_id)
        
        # Generate notebook using AI
        result = await agent.generate_initial_notebook(
            filename="uploaded_data.csv",
            analysis_type=data.get('analysis_type', 'comprehensive_eda'),
            dataframe_stats=stats
        )
        
        if result['success']:
            notebook = result['data']['notebook']
            notebook['notebook_id'] = str(uuid.uuid4())
            notebook['title'] = "Exploratory Data Analysis"
            
            # Save notebook to session state
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

# --- 3. EXECUTE CELL ENDPOINT ---
@notebook_bp.route('/<notebook_id>/execute', methods=['POST'])
@login_required
def execute_cell(notebook_id):
    try:
        data = request.json
        session_id = data.get('session_id')
        cell_id = data.get('cell_id')
        
        if not session_id or not cell_id:
            return jsonify({'success': False, 'error': 'Session ID and Cell ID required'}), 400

        # Get session and notebook
        from app.core.state_manager import SessionState
        session = SessionState.get_session(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
            
        notebook = SessionState.get_notebook(session_id, notebook_id)
        if not notebook:
            return jsonify({'success': False, 'error': 'Notebook not found'}), 404
            
        # Find the cell
        cell = next((c for c in notebook['cells'] if c['id'] == cell_id), None)
        if not cell:
            return jsonify({'success': False, 'error': 'Cell not found'}), 404
            
        # Execute code
        from app.core.safe_executor import SafeExecutor
        
        # Join source lines if it's a list
        code = "".join(cell['source']) if isinstance(cell['source'], list) else cell['source']
        
        # Execute using SafeExecutor
        result = SafeExecutor.execute_cell(cell_id, code, session_id, notebook_id=notebook_id)
        
        # Update cell outputs in the notebook object
        if result['success']:
            cell['outputs'] = [] # Clear previous outputs
            
            if result.get('text_output'):
                cell['outputs'].append({
                    'output_type': 'stream',
                    'name': 'stdout',
                    'text': result['text_output']
                })
                
            for plot in result.get('plots_generated', []):
                if plot['type'] == 'plotly':
                    cell['outputs'].append({
                        'output_type': 'display_data',
                        'data': {
                            'application/vnd.plotly.v1+json': json.loads(plot['figure'].to_json())
                        },
                        'metadata': {}
                    })
                elif plot['type'] == 'image/png':
                    cell['outputs'].append({
                        'output_type': 'display_data',
                        'data': {
                            'image/png': plot['data']
                        },
                        'metadata': {}
                    })
            
            cell['execution_count'] = (cell.get('execution_count') or 0) + 1
            
            # Save updated notebook state
            SessionState.update_notebook(session_id, notebook)
            
        return jsonify({
            'success': True,
            'result': result,
            'notebook': notebook # Return updated notebook
        })

    except Exception as e:
        logger.log_error('execution_failed', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

# --- 4. UPDATE CELL ENDPOINT ---
@notebook_bp.route('/<notebook_id>/update', methods=['POST'])
@login_required
def update_cell(notebook_id):
    try:
        data = request.json
        session_id = data.get('session_id')
        cell_id = data.get('cell_id')
        content = data.get('content')
        cell_type = data.get('cell_type')
        
        from app.core.state_manager import SessionState
        notebook = SessionState.get_notebook(session_id, notebook_id)
        
        if not notebook:
            return jsonify({'success': False, 'error': 'Notebook not found'}), 404
            
        cell = next((c for c in notebook['cells'] if c['id'] == cell_id), None)
        if not cell:
            return jsonify({'success': False, 'error': 'Cell not found'}), 404
            
        if content is not None:
            cell['source'] = content
            
        if cell_type:
            cell['cell_type'] = cell_type
            
        SessionState.update_notebook(session_id, notebook)
        
        return jsonify({
            'success': True,
            'notebook': notebook
        })

    except Exception as e:
        logger.log_error('update_failed', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

# --- 5. ADD CELL ENDPOINT ---
@notebook_bp.route('/<notebook_id>/add_cell', methods=['POST'])
@login_required
def add_cell(notebook_id):
    try:
        data = request.json
        session_id = data.get('session_id')
        index = data.get('index')
        cell_type = data.get('type', 'code')
        source = data.get('source', [])
        metadata = data.get('metadata', {})
        
        from app.core.state_manager import SessionState
        notebook = SessionState.get_notebook(session_id, notebook_id)
        
        if not notebook:
            return jsonify({'success': False, 'error': 'Notebook not found'}), 404
            
        new_cell = {
            "id": str(uuid.uuid4()),
            "cell_type": cell_type,
            "source": source if isinstance(source, list) else [source],
            "metadata": metadata,
            "outputs": [] if cell_type == 'code' else None
        }
        
        if index is not None and 0 <= index <= len(notebook['cells']):
            notebook['cells'].insert(index, new_cell)
        else:
            notebook['cells'].append(new_cell)
            
        SessionState.update_notebook(session_id, notebook)
        
        return jsonify({
            'success': True,
            'notebook': notebook,
            'new_cell': new_cell
        })


    except Exception as e:
        logger.log_error('add_cell_failed', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

# --- 6. DELETE CELL ENDPOINT ---
@notebook_bp.route('/<notebook_id>/delete_cell', methods=['POST'])
@login_required
def delete_cell(notebook_id):
    try:
        data = request.json
        session_id = data.get('session_id')
        cell_id = data.get('cell_id')
        
        from app.core.state_manager import SessionState
        notebook = SessionState.get_notebook(session_id, notebook_id)
        
        if not notebook:
            return jsonify({'success': False, 'error': 'Notebook not found'}), 404
            
        notebook['cells'] = [c for c in notebook['cells'] if c['id'] != cell_id]
        
        SessionState.update_notebook(session_id, notebook)
        
        return jsonify({
            'success': True,
            'notebook': notebook
        })

    except Exception as e:
        logger.log_error('delete_cell_failed', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

# Fallback code generator (works without AI/OpenAI)
def generate_code_from_instruction(instruction, df):
    """Generate basic pandas code based on instruction keywords"""
    instruction_lower = instruction.lower()
    code_suggestions = []
    
    # Analyze instruction and generate appropriate code
    if 'head' in instruction_lower or 'first' in instruction_lower or 'top' in instruction_lower:
        code_suggestions.append({
            'code': 'df.head(10)',
            'explanation': 'Display the first 10 rows of the dataset',
            'confidence': 0.9
        })
    
    elif 'describe' in instruction_lower or 'summary' in instruction_lower or 'statistics' in instruction_lower:
        code_suggestions.append({
            'code': 'df.describe()',
            'explanation': 'Show statistical summary of numerical columns',
            'confidence': 0.95
        })
    
    elif 'info' in instruction_lower or 'column' in instruction_lower or 'dtype' in instruction_lower:
        code_suggestions.append({
            'code': 'df.info()',
            'explanation': 'Display dataset information and column types',
            'confidence': 0.9
        })
    
    elif 'plot' in instruction_lower or 'visualiz' in instruction_lower or 'chart' in instruction_lower or 'graph' in instruction_lower:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if len(numeric_cols) >= 2:
            code_suggestions.append({
                'code': f"import plotly.express as px\nfig = px.scatter(df, x='{numeric_cols[0]}', y='{numeric_cols[1]}')\nfig.show()",
                'explanation': f'Create scatter plot of {numeric_cols[0]} vs {numeric_cols[1]}',
                'confidence': 0.8
            })
        elif len(numeric_cols) == 1:
            code_suggestions.append({
                'code': f"import plotly.express as px\nfig = px.histogram(df, x='{numeric_cols[0]}')\nfig.show()",
                'explanation': f'Create histogram of {numeric_cols[0]}',
                'confidence': 0.8
            })
    
    elif 'correlation' in instruction_lower or 'corr' in instruction_lower:
        code_suggestions.append({
            'code': 'df.corr()',
            'explanation': 'Calculate correlation matrix for numerical columns',
            'confidence': 0.85
        })
    
    elif 'missing' in instruction_lower or 'null' in instruction_lower or 'na' in instruction_lower:
        code_suggestions.append({
            'code': 'df.isnull().sum()',
            'explanation': 'Count missing values in each column',
            'confidence': 0.9
        })
    
    elif 'unique' in instruction_lower or 'distinct' in instruction_lower:
        code_suggestions.append({
            'code': 'df.nunique()',
            'explanation': 'Count unique values in each column',
            'confidence': 0.85
        })
    
    elif 'shape' in instruction_lower or 'size' in instruction_lower or 'dimension' in instruction_lower:
        code_suggestions.append({
            'code': 'print(f"Shape: {df.shape}")\nprint(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")',
            'explanation': 'Display dataset dimensions',
            'confidence': 0.95
        })
    
    else:
        # Default: show head
        code_suggestions.append({
            'code': 'df.head()',
            'explanation': 'Display first few rows (default analysis)',
            'confidence': 0.7
        })
    
    return code_suggestions

# --- 7. PROCESS INSTRUCTION ENDPOINT (Ghost Cell Generation) ---
@notebook_bp.route('/<notebook_id>/process_instruction', methods=['POST'])
@login_required
async def process_instruction(notebook_id):
    """
    Process natural language instruction and generate Ghost Cells
    This is the core of the AI Junior Analyst feature
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        instruction = data.get('instruction')
        
        if not session_id or not instruction:
            return jsonify({'success': False, 'error': 'Session ID and instruction required'}), 400

        # Get session and notebook
        from app.core.state_manager import SessionState
        session = SessionState.get_session(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
            
        notebook = SessionState.get_notebook(session_id, notebook_id)
        if not notebook:
            return jsonify({'success': False, 'error': 'Notebook not found'}), 404
            
        # Get dataframe for context
        df = SessionState.get_dataframe(session_id)
        if df is None:
            return jsonify({'success': False, 'error': 'No dataframe in session'}), 404
        
        # Generate Text Twin for context
        from app.core.text_twin_generator import TextTwinGenerator
        text_twin_gen = TextTwinGenerator()
        text_twin = text_twin_gen.generate_twin(df)
        
        # Use NotebookAgent to process instruction
        agent = NotebookAgent(session_id=session_id)
        result = await agent.process_instruction(instruction, dataframe_context=text_twin)
        
        proposed_cells = []
        if result.get('success') and 'proposed_code' in result.get('data', {}):
            code_cells = result['data']['proposed_code']
            
            for idx, code_block in enumerate(code_cells):
                ghost_cell = {
                    "id": f"ghost_{uuid.uuid4()}",
                    "cell_type": "code",
                    "source": code_block['code'].split('\n'),
                    "metadata": {
                        "ghost": True,
                        "explanation": code_block.get('explanation', ''),
                        "confidence": code_block.get('confidence', 0.8)
                    },
                    "outputs": []
                }
                proposed_cells.append(ghost_cell)
        else:
             # Fallback if AI fails
             logger.log_error('ai_generation_failed', result.get('error', 'Unknown error'))
             code_suggestions = generate_code_from_instruction(instruction, df)
             for code_block in code_suggestions:
                ghost_cell = {
                    "id": f"ghost_{uuid.uuid4()}",
                    "cell_type": "code",
                    "source": code_block['code'].split('\n'),
                    "metadata": {
                        "ghost": True,
                        "explanation": code_block.get('explanation', ''),
                        "confidence": code_block.get('confidence', 0.7)
                    },
                    "outputs": []
                }
                proposed_cells.append(ghost_cell)

        # Add proposed cells to notebook
        if proposed_cells:
            if 'cells' not in notebook:
                notebook['cells'] = []
            
            notebook['cells'].extend(proposed_cells)
            
            # Save updated notebook state
            SessionState.update_notebook(session_id, notebook)
        
        return jsonify({
            'success': True,
            'proposed_cells': proposed_cells,
            'explanation': f"Generated {len(proposed_cells)} code suggestion(s) for: {instruction}",
            'notebook': notebook
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.log_error('process_instruction_failed', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

# --- 8. GET SESSION VARIABLES ENDPOINT (Live State) ---
@notebook_bp.route('/session/<session_id>/variables', methods=['GET'])
@login_required  
def get_session_variables(session_id):
    """
    Get all Python variables from session for live DataDeck display
    """
    try:
        from app.core.state_manager import SessionState
        
        session = SessionState.get_session(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
            
        # Get all variables
        variables = SessionState.list_variables(session_id)
        
        # Get dataframe info
        df = SessionState.get_dataframe(session_id)
        df_info = None
        if df is not None:
            df_info = {
                'shape': list(df.shape),
                'columns': list(df.columns),
                'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                'memory_mb': df.memory_usage(deep=True).sum() / (1024 ** 2)
            }
        
        return jsonify({
            'success': True,
            'variables': variables,
            'dataframe': df_info,
            'session_id': session_id
        })

    except Exception as e:
        logger.log_error('get_variables_failed', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500