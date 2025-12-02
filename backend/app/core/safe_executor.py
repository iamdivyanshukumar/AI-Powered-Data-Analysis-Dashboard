import pandas as pd
import numpy as np
import re
import ast
import logging
from typing import Dict, Any, List, Optional, Tuple
import traceback
from datetime import datetime
import warnings

logger = logging.getLogger(__name__)

class SafeExecutor:
    """
    Safe code execution environment with sandboxing and resource limits.
    Prevents malicious code execution while allowing data analysis.
    """
    
    # Forbidden patterns and imports
    FORBIDDEN_PATTERNS = [
        # System access
        r'__import__\s*\(', r'eval\s*\(', r'exec\s*\(', r'compile\s*\(',
        r'open\s*\(', r'file\s*\(', r'input\s*\(', r'raw_input\s*\(',
        
        # Dangerous modules
        r'import\s+os\b', r'import\s+sys\b', r'import\s+subprocess\b',
        r'import\s+shutil\b', r'import\s+pickle\b', r'import\s+socket\b',
        r'import\s+ctypes\b', r'import\s+multiprocessing\b',
        
        # Dangerous operations
        r'\.system\s*\(', r'\.popen\s*\(', r'\.call\s*\(', r'\.run\s*\(',
        r'\.spawn\s*\(', r'\.kill\s*\(', r'\.terminate\s*\(',
        r'\.rmdir\s*\(', r'\.remove\s*\(', r'\.unlink\s*\(', r'\.rmtree\s*\(',
        r'\.chmod\s*\(', r'\.chown\s*\(', r'\.symlink\s*\(',
        
        # Network operations
        r'\.connect\s*\(', r'\.send\s*\(', r'\.recv\s*\(', r'\.bind\s*\(',
        
        # Reflection/metaprogramming
        r'__builtins__', r'__globals__', r'__locals__', r'__code__',
        r'\.__class__', r'\.__bases__', r'\.__subclasses__',
        
        # File operations
        r'\.read\s*\(', r'\.write\s*\(', r'\.append\s*\(', r'\.writelines\s*\(',
    ]
    
    # Allowed imports (must be imported via our safe environment)
    ALLOWED_IMPORTS = {
        'pandas': ['pd'],
        'numpy': ['np'],
        'matplotlib.pyplot': ['plt'],
        'seaborn': ['sns'],
        'plotly.express': ['px'],
        'plotly.graph_objects': ['go'],
        'scipy': ['stats', 'signal', 'optimize'],
        'sklearn': [
            'preprocessing', 'model_selection', 'metrics',
            'linear_model', 'ensemble', 'cluster', 'decomposition'
        ],
        'datetime': ['datetime', 'timedelta'],
        'math': ['*'],
        'statistics': ['*'],
        'json': ['*'],
        're': ['*'],
        'collections': ['Counter', 'defaultdict', 'OrderedDict'],
        'itertools': ['*'],
        'functools': ['*'],
        'typing': ['*'],
    }
    
    # Resource limits
    MAX_EXECUTION_TIME = 30  # seconds
    MAX_MEMORY_MB = 500  # MB (approximate)
    MAX_OUTPUT_SIZE = 10000  # characters
    
    @classmethod
    def execute(cls, code: str, dataframe: pd.DataFrame, 
               context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute code safely with the given dataframe and context
        
        Args:
            code: Python code to execute
            dataframe: Pandas DataFrame
            context: Additional variables for execution
            
        Returns:
            Dictionary with execution results
        """
        start_time = datetime.now()
        
        # Validate code safety
        validation_result = cls._validate_code(code)
        if not validation_result['safe']:
            return {
                'success': False,
                'error': f"Code validation failed: {validation_result['reason']}",
                'execution_time': 0,
                'validated': False
            }
        
        try:
            # Create safe execution environment
            exec_globals = cls._create_safe_environment(dataframe, context)
            
            # Execute the code
            warnings.filterwarnings('ignore')  # Suppress warnings during execution
            
            # Use compile to get better error messages
            try:
                compiled_code = compile(code, '<user_code>', 'exec')
            except SyntaxError as e:
                return {
                    'success': False,
                    'error': f"Syntax error: {str(e)}",
                    'execution_time': (datetime.now() - start_time).total_seconds(),
                    'validated': True
                }
            
            # Execute with timeout protection
            result = cls._execute_with_timeout(compiled_code, exec_globals)
            
            if result['timeout']:
                return {
                    'success': False,
                    'error': f"Execution timeout after {cls.MAX_EXECUTION_TIME} seconds",
                    'execution_time': cls.MAX_EXECUTION_TIME,
                    'validated': True
                }
            
            if result['error']:
                return {
                    'success': False,
                    'error': f"Execution error: {result['error']}",
                    'traceback': result.get('traceback'),
                    'execution_time': result['execution_time'],
                    'validated': True
                }
            
            # Extract results from execution
            execution_results = cls._extract_results(exec_globals, dataframe)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Code executed successfully in {execution_time:.2f}s")
            
            return {
                'success': True,
                'execution_time': execution_time,
                'dataframe_updated': not dataframe.equals(exec_globals.get('df', dataframe)),
                'new_dataframe_shape': exec_globals.get('df', dataframe).shape,
                'variables_created': execution_results['variables_created'],
                'plots_generated': execution_results['plots_generated'],
                'text_output': execution_results['text_output'],
                'warnings': execution_results['warnings'],
                'validated': True
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Unexpected execution error: {str(e)}")
            
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'traceback': traceback.format_exc(),
                'execution_time': execution_time,
                'validated': True
            }
    
    @classmethod
    def _validate_code(cls, code: str) -> Dict[str, Any]:
        """
        Validate code for safety
        
        Args:
            code: Python code to validate
            
        Returns:
            Validation result dictionary
        """
        # Check for forbidden patterns
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return {
                    'safe': False,
                    'reason': f"Forbidden pattern detected: {pattern}",
                    'pattern': pattern
                }
        
        # Check for import statements (should be handled by our environment)
        if re.search(r'^\s*import\s+\w', code, re.MULTILINE) or \
           re.search(r'^\s*from\s+\w+\s+import', code, re.MULTILINE):
            # Check if import is in our allowed list
            lines = code.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Extract module name
                    if line.startswith('import '):
                        module = line[7:].split()[0].split('.')[0]
                    else:  # from x import y
                        module = line[5:].split()[0].split('.')[0]
                    
                    if module not in cls.ALLOWED_IMPORTS:
                        return {
                            'safe': False,
                            'reason': f"Forbidden import: {module}",
                            'module': module
                        }
        
        # Check code complexity (simple heuristic)
        lines = code.strip().split('\n')
        if len(lines) > 100:
            return {
                'safe': False,
                'reason': f"Code too long ({len(lines)} lines). Maximum is 100 lines.",
                'line_count': len(lines)
            }
        
        # Check for potentially dangerous operations
        dangerous_ops = [
            r'while\s+True:', r'for\s+\w+\s+in\s+range\s*\(\s*10\s*\*\s*\d+',
            r'\.append\s*\(\s*\w+\s*\)\s*\.append',  # Nested appends
        ]
        
        for op in dangerous_ops:
            if re.search(op, code):
                return {
                    'safe': False,
                    'reason': f"Potentially dangerous operation: {op}",
                    'operation': op
                }
        
        return {'safe': True, 'reason': 'Code passed validation'}
    
    @classmethod
    def _create_safe_environment(cls, dataframe: pd.DataFrame, 
                                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a safe execution environment with allowed imports
        
        Args:
            dataframe: DataFrame to make available
            context: Additional context variables
            
        Returns:
            Execution globals dictionary
        """
        # Import allowed modules
        import pandas as pd
        import numpy as np
        import math
        import re
        import json
        import statistics
        from datetime import datetime, timedelta
        from collections import Counter, defaultdict, OrderedDict
        import itertools
        import functools
        
        # Create base environment
        env = {
            'df': dataframe.copy(),
            'pd': pd,
            'np': np,
            'math': math,
            're': re,
            'json': json,
            'statistics': statistics,
            'datetime': datetime,
            'timedelta': timedelta,
            'Counter': Counter,
            'defaultdict': defaultdict,
            'OrderedDict': OrderedDict,
                        'itertools': itertools,
            'functools': functools,
            '__builtins__': {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'sorted': sorted,
                'reversed': reversed,
                'min': min,
                'max': max,
                'sum': sum,
                'abs': abs,
                'round': round,
                'isinstance': isinstance,
                'type': type,
                'hasattr': hasattr,
                'getattr': getattr,
            }
        }
        
        # Add context variables if provided
        if context:
            env.update(context)
        
        # Lazy imports for heavier modules (only when needed)
        def lazy_import(module_name, import_path):
            """Lazy import helper"""
            try:
                module = __import__(import_path, fromlist=[module_name])
                env[module_name] = module
                return module
            except ImportError as e:
                logger.warning(f"Could not import {module_name}: {e}")
                return None
        
        # Add lazy import wrappers
        env['plt'] = lambda: lazy_import('plt', 'matplotlib.pyplot')
        env['sns'] = lambda: lazy_import('sns', 'seaborn')
        env['px'] = lambda: lazy_import('px', 'plotly.express')
        env['go'] = lambda: lazy_import('go', 'plotly.graph_objects')
        
        return env
    
    @classmethod
    def _execute_with_timeout(cls, compiled_code, exec_globals) -> Dict[str, Any]:
        """
        Execute code with timeout protection
        
        Args:
            compiled_code: Compiled code object
            exec_globals: Execution globals
            
        Returns:
            Execution result dictionary
        """
        import threading
        import queue
        
        result_queue = queue.Queue()
        
        def worker():
            """Worker function to execute code"""
            try:
                exec(compiled_code, exec_globals)
                result_queue.put({
                    'success': True,
                    'error': None,
                    'traceback': None
                })
            except Exception as e:
                result_queue.put({
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
        
        # Start execution thread
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        
        # Wait for completion or timeout
        thread.join(cls.MAX_EXECUTION_TIME)
        
        if thread.is_alive():
            return {
                'success': False,
                'error': 'Timeout',
                'timeout': True,
                'execution_time': cls.MAX_EXECUTION_TIME
            }
        
        try:
            result = result_queue.get_nowait()
            result['timeout'] = False
            result['execution_time'] = (datetime.now() - cls._execution_start_time).total_seconds()
            return result
        except queue.Empty:
            return {
                'success': False,
                'error': 'Execution failed without error',
                'timeout': False,
                'execution_time': (datetime.now() - cls._execution_start_time).total_seconds()
            }
    
    @classmethod
    def _extract_results(cls, exec_globals, original_df) -> Dict[str, Any]:
        """
        Extract results from execution environment
        
        Args:
            exec_globals: Execution globals dictionary
            original_df: Original DataFrame
            
        Returns:
            Results dictionary
        """
        results = {
            'variables_created': [],
            'plots_generated': [],
            'text_output': '',
            'warnings': []
        }
        
        # Get all variables defined (excluding built-ins and modules)
        excluded = {'df', 'pd', 'np', 'math', 're', 'json', 'statistics',
                   'datetime', 'timedelta', 'Counter', 'defaultdict', 
                   'OrderedDict', 'itertools', 'functools', '__builtins__',
                   'plt', 'sns', 'px', 'go'}
        
        for var_name, var_value in exec_globals.items():
            if var_name not in excluded and not var_name.startswith('_'):
                var_type = type(var_value).__name__
                
                # Check if it's a new variable (not in original env)
                if var_name not in dir(__builtins__):
                    results['variables_created'].append({
                        'name': var_name,
                        'type': var_type,
                        'value_preview': str(var_value)[:100]
                    })
        
        # Check for plots (matplotlib or plotly figures)
        for var_name, var_value in exec_globals.items():
            if var_name not in excluded:
                var_type = type(var_value).__name__
                if var_type in ['Figure', 'Axes', 'AxesSubplot']:
                    results['plots_generated'].append({
                        'name': var_name,
                        'type': 'matplotlib',
                        'figure': var_value
                    })
                elif hasattr(var_value, '_data_objs'):  # Plotly figure
                    results['plots_generated'].append({
                        'name': var_name,
                        'type': 'plotly',
                        'figure': var_value
                    })
        
        # Check if dataframe was modified
        new_df = exec_globals.get('df', original_df)
        if not new_df.equals(original_df):
            logger.info(f"DataFrame modified: {original_df.shape} -> {new_df.shape}")
        
        return results
    
    @classmethod
    def execute_cell(cls, cell_id: str, code: str, session_id: str, 
                    notebook_id: str = None) -> Dict[str, Any]:
        """
        Execute a notebook cell with full context
        
        Args:
            cell_id: Cell identifier
            code: Cell code
            session_id: Session ID string
            notebook_id: Notebook identifier
            
        Returns:
            Execution result dictionary
        """
        from app.core.state_manager import SessionState
        
        # Get dataframe from session
        df = SessionState.get_dataframe(session_id)
        if df is None:
            return {
                'success': False,
                'error': 'No dataframe available in session',
                'execution_time': 0
            }
        
        # Get existing variables from session
        variables = {}
        for var_info in SessionState.list_variables(session_id):
            var_value = SessionState.get_variable(session_id, var_info['name'])
            if var_value is not None:
                variables[var_info['name']] = var_value
        
        # Execute code
        result = cls.execute(code, df, variables)
        
        # Update session state if successful
        if result['success']:
            # Update dataframe if modified
            if result.get('dataframe_updated', False):
                new_df = result.get('new_dataframe')
                if new_df is not None:
                    SessionState.update_dataframe(session_id, new_df, f"Cell {cell_id} execution")
            
            # Store new variables
            for var_info in result.get('variables_created', []):
                var_name = var_info['name']
                # Get the variable from the execution environment
                # Note: We need to extract this from the execution context
                # For now, we'll skip storing individual variables
                pass
        
        # Log execution
        execution_log = {
            'cell_id': cell_id,
            'notebook_id': notebook_id,
            'timestamp': datetime.now().isoformat(),
            'execution_time': result.get('execution_time', 0),
            'success': result.get('success', False),
            'error': result.get('error'),
            'variables_created': result.get('variables_created', []),
            'plots_generated': len(result.get('plots_generated', []))
        }
        
        SessionState.log_execution(session_id, execution_log)
        
        return result