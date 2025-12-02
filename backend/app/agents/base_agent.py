from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

from app.core.logger import AgentLogger, LogLevel

logger = logging.getLogger(__name__)

class AgentConfig:
    """Configuration for agents"""
    
    def __init__(self, 
                 model: str = "gpt-4",
                 temperature: float = 0.1,
                 max_tokens: int = 2000,
                 timeout: int = 30,
                 retries: int = 3,
                 **kwargs):
        """
        Initialize agent configuration
        
        Args:
            model: LLM model to use
            temperature: Temperature for sampling
            max_tokens: Maximum tokens in response
            timeout: Timeout in seconds
            retries: Number of retries on failure
            **kwargs: Additional configuration
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retries = retries
        self.extra_config = kwargs
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'timeout': self.timeout,
            'retries': self.retries,
            **self.extra_config
        }

class BaseAgent(ABC):
    """
    Base class for all agents in AutoVizAI 2.0
    """
    
    def __init__(self, 
                 name: str,
                 description: str,
                 config: AgentConfig = None,
                 session_id: str = None):
        """
        Initialize base agent
        
        Args:
            name: Agent name
            description: Agent description
            config: Agent configuration
            session_id: Session identifier
        """
        self.name = name
        self.description = description
        self.config = config or AgentConfig()
        self.session_id = session_id
        
        # Initialize logger
        self.logger = AgentLogger(name, session_id)
        
        # Execution history
        self.execution_history: List[Dict[str, Any]] = []
        
        # Performance metrics
        self.metrics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_duration_ms': 0,
            'avg_duration_ms': 0
        }
        
        logger.info(f"Initialized agent: {name} ({description})")
    
    @abstractmethod
    async def execute(self, 
                     input_data: Dict[str, Any],
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute agent's main functionality
        
        Args:
            input_data: Input data for the agent
            context: Additional execution context
            
        Returns:
            Agent output
        """
        pass
    
    def log_execution(self, 
                     operation: str,
                     input_data: Dict[str, Any] = None,
                     output_data: Dict[str, Any] = None,
                     duration_ms: float = None,
                     success: bool = True,
                     error: str = None):
        """
        Log agent execution
        
        Args:
            operation: Operation name
            input_data: Input data
            output_data: Output data
            duration_ms: Execution duration
            success: Whether execution succeeded
            error: Error message if any
        """
        execution_record = {
            'agent': self.name,
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            'duration_ms': duration_ms,
            'success': success,
            'input_keys': list(input_data.keys()) if input_data else [],
            'output_keys': list(output_data.keys()) if output_data else [],
            'error': error
        }
        
        self.execution_history.append(execution_record)
        
        # Update metrics
        self.metrics['total_calls'] += 1
        if success:
            self.metrics['successful_calls'] += 1
        else:
            self.metrics['failed_calls'] += 1
        
        if duration_ms:
            self.metrics['total_duration_ms'] += duration_ms
            self.metrics['avg_duration_ms'] = self.metrics['total_duration_ms'] / self.metrics['total_calls']
        
        # Log using structured logger
        self.logger.log_operation(
            operation=operation,
            level=LogLevel.INFO if success else LogLevel.ERROR,
            details={
                'input_size': len(json.dumps(input_data)) if input_data else 0,
                'output_size': len(json.dumps(output_data)) if output_data else 0
            },
            duration_ms=duration_ms,
            success=success,
            error=error
        )
    
    async def call_llm(self, 
                      prompt: str,
                      system_prompt: str = None,
                      **kwargs) -> str:
        """
        Call LLM with error handling and logging using LangChain
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            **kwargs: Additional arguments
            
        Returns:
            LLM response
        """
        import time
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.config import Config
        
        start_time = time.time()
        
        try:
            # Initialize LangChain ChatOpenAI
            # Tracing is automatically enabled if LANGCHAIN_TRACING_V2=true in env
            chat = ChatOpenAI(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                api_key=Config.OPENAI_API_KEY,
                **kwargs
            )
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))
            
            # Make API call
            response = await chat.ainvoke(messages)
            result = response.content
            
            # Log success
            duration_ms = (time.time() - start_time) * 1000
            if hasattr(self.logger, 'log_llm_call'):
                self.logger.log_llm_call(
                    model=self.config.model,
                    prompt_length=len(prompt),
                    response_length=len(result),
                    duration_ms=duration_ms,
                    success=True
                )
            
            return result
            
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            if hasattr(self.logger, 'log_llm_call'):
                self.logger.log_llm_call(
                    model=self.config.model,
                    prompt_length=len(prompt),
                    response_length=0,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
            
            raise
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        return {
            'agent_name': self.name,
            'description': self.description,
            'total_executions': len(self.execution_history),
            'metrics': self.metrics,
            'recent_executions': self.execution_history[-10:] if self.execution_history else []
        }
    
    def validate_input(self, 
                      input_data: Dict[str, Any],
                      required_keys: List[str] = None) -> bool:
        """
        Validate input data
        
        Args:
            input_data: Input data to validate
            required_keys: List of required keys
            
        Returns:
            True if valid, False otherwise
        """
        if required_keys:
            for key in required_keys:
                if key not in input_data:
                    self.logger.log_operation(
                        operation="input_validation",
                        level=LogLevel.ERROR,
                        details={'missing_key': key},
                        success=False
                    )
                    return False
        
        return True
    
    def create_response(self, 
                       success: bool,
                       data: Dict[str, Any] = None,
                       error: str = None,
                       metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create standardized response
        
        Args:
            success: Whether operation succeeded
            data: Response data
            error: Error message
            metadata: Additional metadata
            
        Returns:
            Standardized response dictionary
        """
        response = {
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'agent': self.name,
            'data': data or {},
            'metadata': metadata or {}
        }
        
        if error:
            response['error'] = error
        
        return response
    
    def cleanup(self):
        """Clean up agent resources"""
        logger.info(f"Cleaning up agent: {self.name}")
        
        # Clear execution history if too large
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
        
        # Log cleanup
        self.logger.log_operation(
            operation="agent_cleanup",
            level=LogLevel.INFO,
            details={'execution_count': len(self.execution_history)},
            success=True
        )