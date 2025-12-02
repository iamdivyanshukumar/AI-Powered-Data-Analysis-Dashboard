import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import uuid
import json
import threading
from datetime import datetime, timedelta
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

class SessionState:
    """
    Manages user session state including dataframes, variables, and execution history.
    Thread-safe with automatic cleanup.
    """
    
    _sessions: Dict[str, Dict[str, Any]] = {}
    _lock = threading.RLock()
    _cleanup_interval = 3600  # Cleanup every hour
    _session_timeout = 86400  # 24 hours
    
    @classmethod
    def _cleanup_old_sessions(cls):
        """Remove expired sessions"""
        with cls._lock:
            current_time = datetime.now()
            expired = []
            
            for session_id, session in cls._sessions.items():
                last_accessed = session.get('last_accessed')
                if last_accessed:
                    age = (current_time - last_accessed).total_seconds()
                    if age > cls._session_timeout:
                        expired.append(session_id)
                        logger.info(f"Session {session_id} expired (age: {age:.0f}s)")
            
            for session_id in expired:
                cls._cleanup_session(session_id)
    
    @classmethod
    def _cleanup_session(cls, session_id: str):
        """Clean up a specific session"""
        session = cls._sessions.get(session_id)
        if session:
            # Clear large objects from memory
            if 'dataframe' in session:
                del session['dataframe']
            if 'variables' in session:
                session['variables'].clear()
            if 'notebooks' in session:
                for notebook in session['notebooks'].values():
                    if 'cells' in notebook:
                        notebook['cells'].clear()
            
            del cls._sessions[session_id]
            logger.debug(f"Cleaned up session: {session_id}")
    
    @classmethod
    def _touch_session(cls, session_id: str):
        """Update last accessed time"""
        with cls._lock:
            session = cls._sessions.get(session_id)
            if session:
                session['last_accessed'] = datetime.now()
    
    @classmethod
    def create_session(cls, user_id: int, df: pd.DataFrame, filename: str, 
                      metadata: Dict[str, Any] = None) -> str:
        """
        Create a new session with the given dataframe
        
        Args:
            user_id: User identifier
            df: Pandas DataFrame
            filename: Original filename
            metadata: Additional session metadata
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        with cls._lock:
            cls._sessions[session_id] = {
                'id': session_id,
                'user_id': user_id,
                'dataframe': df.copy(),
                'filename': filename,
                'variables': {},
                'notebooks': {},
                'execution_history': [],
                'created_at': datetime.now(),
                'last_accessed': datetime.now(),
                'metadata': metadata or {},
                'stats': {
                    'original_shape': df.shape,
                    'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
                    'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024**2,
                    'missing_values': df.isnull().sum().sum(),
                    'unique_sessions': len(set(df.columns))
                }
            }
        
        logger.info(f"Created session {session_id} for user {user_id} with {df.shape} dataframe")
        return session_id
    
    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID, updating last accessed time
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session dictionary or None if not found
        """
        cls._touch_session(session_id)
        return cls._sessions.get(session_id)
    
    @classmethod
    def get_dataframe(cls, session_id: str) -> Optional[pd.DataFrame]:
        """
        Get dataframe from session
        
        Args:
            session_id: Session identifier
            
        Returns:
            DataFrame or None if session not found
        """
        session = cls.get_session(session_id)
        if session:
            return session.get('dataframe')
        return None
    
    @classmethod
    def update_dataframe(cls, session_id: str, df: pd.DataFrame, 
                        description: str = "Dataframe updated"):
        """
        Update dataframe in session and log the change
        
        Args:
            session_id: Session identifier
            df: New DataFrame
            description: Description of the update
        """
        with cls._lock:
            session = cls._sessions.get(session_id)
            if session:
                old_shape = session['dataframe'].shape if 'dataframe' in session else (0, 0)
                session['dataframe'] = df.copy()
                session['last_accessed'] = datetime.now()
                
                # Log the change
                change_record = {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'dataframe_update',
                    'description': description,
                    'old_shape': old_shape,
                    'new_shape': df.shape,
                    'columns_added': list(set(df.columns) - set(session.get('dataframe', pd.DataFrame()).columns)),
                    'columns_removed': list(set(session.get('dataframe', pd.DataFrame()).columns) - set(df.columns))
                }
                
                session['execution_history'].append(change_record)
                logger.info(f"Updated dataframe in session {session_id}: {old_shape} -> {df.shape}")
    
    @classmethod
    def get_variable(cls, session_id: str, variable_name: str) -> Any:
        """
        Get a variable from session
        
        Args:
            session_id: Session identifier
            variable_name: Name of the variable
            
        Returns:
            Variable value or None if not found
        """
        session = cls.get_session(session_id)
        if session:
            return session['variables'].get(variable_name)
        return None
    
    @classmethod
    def set_variable(cls, session_id: str, variable_name: str, value: Any, 
                    variable_type: str = None):
        """
        Set a variable in session
        
        Args:
            session_id: Session identifier
            variable_name: Name of the variable
            value: Variable value
            variable_type: Type of variable (optional)
        """
        with cls._lock:
            session = cls._sessions.get(session_id)
            if session:
                session['variables'][variable_name] = value
                session['last_accessed'] = datetime.now()
                
                # Log variable creation/update
                action = 'variable_updated' if variable_name in session['variables'] else 'variable_created'
                
                change_record = {
                    'timestamp': datetime.now().isoformat(),
                    'action': action,
                    'variable_name': variable_name,
                    'variable_type': variable_type or type(value).__name__,
                    'value_preview': str(value)[:100] if value else None
                }
                
                session['execution_history'].append(change_record)
                logger.debug(f"Set variable {variable_name} in session {session_id}")
    
    @classmethod
    def list_variables(cls, session_id: str) -> List[Dict[str, Any]]:
        """
        List all variables in session
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of variable information dictionaries
        """
        session = cls.get_session(session_id)
        if session:
            variables = []
            for name, value in session['variables'].items():
                variables.append({
                    'name': name,
                    'type': type(value).__name__,
                    'value_preview': str(value)[:50],
                    'size': len(str(value)) if hasattr(value, '__len__') else None
                })
            return variables
        return []
    
    @classmethod
    def add_notebook(cls, session_id: str, notebook: Dict[str, Any]):
        """
        Add a notebook to session
        
        Args:
            session_id: Session identifier
            notebook: Notebook dictionary
        """
        with cls._lock:
            session = cls._sessions.get(session_id)
            if session and 'notebook_id' in notebook:
                session['notebooks'][notebook['notebook_id']] = notebook
                session['last_accessed'] = datetime.now()
                logger.info(f"Added notebook {notebook['notebook_id']} to session {session_id}")
    
    @classmethod
    def get_notebook(cls, session_id: str, notebook_id: str) -> Optional[Dict[str, Any]]:
        """
        Get notebook from session
        
        Args:
            session_id: Session identifier
            notebook_id: Notebook identifier
            
        Returns:
            Notebook dictionary or None if not found
        """
        session = cls.get_session(session_id)
        if session:
            return session['notebooks'].get(notebook_id)
        return None
    
    @classmethod
    def update_notebook(cls, session_id: str, notebook: Dict[str, Any]):
        """
        Update notebook in session
        
        Args:
            session_id: Session identifier
            notebook: Updated notebook dictionary
        """
        with cls._lock:
            session = cls._sessions.get(session_id)
            if session and 'notebook_id' in notebook:
                session['notebooks'][notebook['notebook_id']] = notebook
                session['last_accessed'] = datetime.now()
                logger.debug(f"Updated notebook {notebook['notebook_id']} in session {session_id}")
    
    @classmethod
    def list_notebooks(cls, session_id: str) -> List[Dict[str, Any]]:
        """
        List all notebooks in session
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of notebook summaries
        """
        session = cls.get_session(session_id)
        if session:
            notebooks = []
            for notebook_id, notebook in session['notebooks'].items():
                notebooks.append({
                    'notebook_id': notebook_id,
                    'title': notebook.get('title', 'Untitled'),
                    'created_at': notebook.get('metadata', {}).get('created_at'),
                    'cell_count': len(notebook.get('cells', [])),
                    'description': notebook.get('description', '')
                })
            return notebooks
        return []
    
    @classmethod
    def log_execution(cls, session_id: str, log_entry: Dict[str, Any]):
        """
        Log an execution event
        
        Args:
            session_id: Session identifier
            log_entry: Log entry dictionary
        """
        with cls._lock:
            session = cls._sessions.get(session_id)
            if session:
                if 'timestamp' not in log_entry:
                    log_entry['timestamp'] = datetime.now().isoformat()
                session['execution_history'].append(log_entry)
                session['last_accessed'] = datetime.now()
                
                # Keep only last 1000 entries to prevent memory issues
                if len(session['execution_history']) > 1000:
                    session['execution_history'] = session['execution_history'][-1000:]
    
    @classmethod
    def get_execution_history(cls, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get execution history for session
        
        Args:
            session_id: Session identifier
            limit: Maximum number of entries to return
            
        Returns:
            List of execution log entries
        """
        session = cls.get_session(session_id)
        if session:
            return session['execution_history'][-limit:]
        return []
    
    @classmethod
    def get_session_stats(cls, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session statistics dictionary
        """
        session = cls.get_session(session_id)
        if session:
            df = session.get('dataframe')
            current_shape = df.shape if df is not None else (0, 0)
            
            return {
                'session_id': session_id,
                'user_id': session['user_id'],
                'filename': session['filename'],
                'created_at': session['created_at'].isoformat(),
                'last_accessed': session['last_accessed'].isoformat(),
                'dataframe_shape': current_shape,
                'variables_count': len(session['variables']),
                'notebooks_count': len(session['notebooks']),
                'execution_history_count': len(session['execution_history']),
                'original_shape': session['stats']['original_shape'],
                'memory_usage_mb': session['stats']['memory_usage_mb'],
                'missing_values': session['stats']['missing_values']
            }
        return {}
    
    @classmethod
    def delete_session(cls, session_id: str):
        """
        Delete a session
        
        Args:
            session_id: Session identifier
        """
        with cls._lock:
            if session_id in cls._sessions:
                cls._cleanup_session(session_id)
                logger.info(f"Deleted session: {session_id}")
    
    @classmethod
    def cleanup_all_sessions(cls):
        """Clean up all sessions (for testing/maintenance)"""
        with cls._lock:
            session_ids = list(cls._sessions.keys())
            for session_id in session_ids:
                cls._cleanup_session(session_id)
            logger.info(f"Cleaned up all {len(session_ids)} sessions")
    
    @classmethod
    def get_active_sessions_count(cls) -> int:
        """Get count of active sessions"""
        with cls._lock:
            return len(cls._sessions)
    
    @classmethod
    def session_exists(cls, session_id: str) -> bool:
        """Check if session exists"""
        return session_id in cls._sessions
    
    @classmethod
    def validate_session_ownership(cls, session_id: str, user_id: int) -> bool:
        """
        Validate that user owns the session
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            True if user owns the session, False otherwise
        """
        session = cls.get_session(session_id)
        if session:
            return session['user_id'] == user_id
        return False