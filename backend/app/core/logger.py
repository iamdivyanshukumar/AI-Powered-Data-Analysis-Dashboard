import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import os
import functools
import time

class LogLevel(Enum):
    """Log levels for agent operations"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AgentLogger:
    """
    Structured logger for agent operations with rich context
    """
    
    def __init__(self, agent_name: str, session_id: str = None):
        self.agent_name = agent_name
        self.session_id = session_id
        self.logger = logging.getLogger(f"agent.{agent_name}")
        self.logger.setLevel(logging.INFO)
        
        # Ensure logs directory exists
        if not os.path.exists('logs'):
            try:
                os.makedirs('logs')
            except Exception:
                pass

        # Add handlers if they don't exist
        if not self.logger.handlers:
            # File Handler
            try:
                f_handler = logging.FileHandler('logs/autovizai.log')
                f_handler.setLevel(logging.INFO)
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                f_handler.setFormatter(formatter)
                self.logger.addHandler(f_handler)
            except Exception:
                pass

            # Console Handler
            c_handler = logging.StreamHandler()
            c_handler.setLevel(logging.INFO)
            c_handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(c_handler)
        
        # Structured log fields
        self.base_fields = {
            'agent': agent_name,
            'timestamp': None,
            'session_id': session_id
        }
    
    # --- BRIDGE METHOD (FIX FOR ROUTES) ---
    def log_info(self, operation: str, message: str, context: Dict[str, Any] = None):
        """
        Convenience wrapper for INFO logs to match route expectations.
        """
        details = {'message': message}
        if context:
            details.update(context)
            
        return self.log_operation(
            operation=operation,
            level=LogLevel.INFO,
            details=details,
            success=True
        )

    def log_operation(self, 
                     operation: str,
                     level: LogLevel = LogLevel.INFO,
                     details: Dict[str, Any] = None,
                     duration_ms: float = None,
                     success: bool = None,
                     error: str = None):
        """
        Log an agent operation
        """
        log_entry = {
            **self.base_fields,
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'level': level.value,
            'details': details or {},
            'duration_ms': duration_ms,
            'success': success,
            'error': error
        }
        
        # Remove None values
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        
        # Log based on level
        log_message = f"[{operation}]"
        
        if details and 'message' in details:
            log_message += f" {details['message']}"
            
        if duration_ms is not None:
            log_message += f" ({duration_ms:.1f}ms)"
        if success is not None:
            log_message += f" [{'✓' if success else '✗'}]"
        if error:
            log_message += f" Error: {error}"
        
        if level == LogLevel.DEBUG:
            self.logger.debug(log_message, extra={'structured_data': log_entry})
        elif level == LogLevel.INFO:
            self.logger.info(log_message, extra={'structured_data': log_entry})
        elif level == LogLevel.WARNING:
            self.logger.warning(log_message, extra={'structured_data': log_entry})
        elif level == LogLevel.ERROR:
            self.logger.error(log_message, extra={'structured_data': log_entry})
        elif level == LogLevel.CRITICAL:
            self.logger.critical(log_message, extra={'structured_data': log_entry})
        
        return log_entry
    
    def log_error(self,
                 error_type: str,
                 error_message: str,
                 context: Dict[str, Any] = None,
                 traceback: str = None):
        details = {
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {},
            'traceback': traceback
        }
        
        return self.log_operation(
            operation=f"error_{error_type}",
            level=LogLevel.ERROR,
            details=details,
            success=False,
            error=error_message
        )

# --- MISSING DECORATOR RESTORED HERE ---
def log_agent_operation(func):
    """
    Decorator to log agent operations automatically
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract agent name from class or function
        agent_name = "unknown"
        if args and hasattr(args[0], '__class__'):
            agent_name = args[0].__class__.__name__
        else:
            agent_name = func.__name__
        
        # Create logger
        logger = AgentLogger(agent_name)
        
        # Log start
        start_time = time.time()
        logger.log_operation(
            operation=f"start_{func.__name__}",
            level=LogLevel.DEBUG,
            details={'args_count': len(args), 'kwargs_keys': list(kwargs.keys())}
        )
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log success
            logger.log_operation(
                operation=f"end_{func.__name__}",
                level=LogLevel.INFO,
                duration_ms=duration_ms,
                success=True
            )
            
            return result
            
        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            logger.log_operation(
                operation=f"end_{func.__name__}",
                level=LogLevel.ERROR,
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )
            
            raise
    
    return wrapper