from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime

from .base_agent import BaseAgent, AgentConfig
from .eda_specialist import EDASpecialist
from .storyteller_agent import StorytellerAgent
from .quality_inspector import QualityInspector
from .notebook_agent import NotebookAgent
from .data_engineer_agent import DataEngineerAgent
from .ml_specialist_agent import MLSpecialistAgent
from app.core.text_twin_generator import TextTwinGenerator
from app.core.state_manager import SessionState
from app.core.logger import log_agent_operation, LogLevel

import logging

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent that coordinates between different specialist agents
    """
    
    def __init__(self, 
                 config: AgentConfig = None,
                 session_id: str = None):
        """
        Initialize orchestrator agent
        
        Args:
            config: Agent configuration
            session_id: Session identifier
        """
        super().__init__(
            name="Orchestrator",
            description="Coordinates data analysis workflow between specialist agents",
            config=config or AgentConfig(model="gpt-4", temperature=0.1),
            session_id=session_id
        )
        
        # Initialize specialist agents
        self.eda_specialist = EDASpecialist(session_id=session_id)
        self.storyteller = StorytellerAgent(session_id=session_id)
        self.quality_inspector = QualityInspector(session_id=session_id)
        self.notebook_agent = NotebookAgent(session_id=session_id)
        self.data_engineer = DataEngineerAgent(session_id=session_id)
        self.ml_specialist = MLSpecialistAgent(session_id=session_id)
        
        # Initialize utilities
        self.text_twin_generator = TextTwinGenerator()
        
        # Workflow registry
        self.workflows = {
            'comprehensive_eda': self.execute_comprehensive_eda,
            'quick_analysis': self.execute_quick_analysis,
            'data_cleaning': self.execute_data_cleaning,
            'feature_engineering': self.execute_feature_engineering,
            'ml_pipeline': self.execute_ml_pipeline,
            'notebook_generation': self.execute_notebook_generation
        }
        
        logger.info("Orchestrator agent initialized")
    
    async def execute(self, 
                     input_data: Dict[str, Any],
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute orchestrator workflow
        
        Args:
            input_data: Must contain 'workflow' and 'session_id'
            context: Additional context
            
        Returns:
            Orchestration result
        """
        # Validate input
        required_keys = ['workflow', 'session_id']
        if not self.validate_input(input_data, required_keys):
            return self.create_response(
                success=False,
                error=f"Missing required keys: {required_keys}"
            )
        
        workflow = input_data['workflow']
        session_id = input_data['session_id']
        
        # Check if workflow exists
        if workflow not in self.workflows:
            return self.create_response(
                success=False,
                error=f"Unknown workflow: {workflow}. Available: {list(self.workflows.keys())}"
            )
        
        # Update session ID for all agents
        self._update_session_id(session_id)
        
        # Execute workflow
        try:
            start_time = datetime.now()
            
            # Log workflow start
            self.logger.log_operation(
                operation=f"workflow_start_{workflow}",
                level=LogLevel.INFO,
                details={'input_data': input_data},
                success=True
            )
            
            # Execute workflow
            workflow_func = self.workflows[workflow]
            result = await workflow_func(input_data, context)
            
            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log workflow completion
            self.logger.log_operation(
                operation=f"workflow_end_{workflow}",
                level=LogLevel.INFO,
                details={'duration_ms': duration_ms},
                duration_ms=duration_ms,
                success=result.get('success', False)
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error(
                error_type="workflow_execution",
                error_message=str(e),
                context={'workflow': workflow, 'session_id': session_id}
            )
            
            return self.create_response(
                success=False,
                error=f"Workflow execution failed: {str(e)}"
            )
    
    async def execute_comprehensive_eda(self, 
                                       input_data: Dict[str, Any],
                                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute comprehensive EDA workflow
        
        Args:
            input_data: Input data
            context: Additional context
            
        Returns:
            EDA results
        """
        session_id = input_data['session_id']
        user_context = input_data.get('user_context', '')
        
        # Get dataframe from session
        df = SessionState.get_dataframe(session_id)
        if df is None:
            return self.create_response(
                success=False,
                error="No dataframe found in session"
            )
        
        # Generate text twin for efficient context passing
        text_twin = self.text_twin_generator.generate_twin(df)
        
        # Execute agents in parallel where possible
        tasks = [
            self.eda_specialist.execute({
                'dataframe_twin': text_twin,
                'analysis_type': 'comprehensive',
                'user_context': user_context
            }),
            self.quality_inspector.execute({
                'dataframe_twin': text_twin
            }),
            self.storyteller.execute({
                'dataframe_twin': text_twin,
                'user_context': user_context
            })
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        eda_result = results[0] if not isinstance(results[0], Exception) else None
        quality_result = results[1] if not isinstance(results[1], Exception) else None
        storytelling_result = results[2] if not isinstance(results[2], Exception) else None
        
        # Create comprehensive report
        report = {
            'eda': eda_result.get('data', {}) if eda_result else {},
            'quality_assessment': quality_result.get('data', {}) if quality_result else {},
            'narrative': storytelling_result.get('data', {}) if storytelling_result else {},
            'metadata': {
                'session_id': session_id,
                'workflow': 'comprehensive_eda',
                'dataframe_shape': df.shape,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Check for errors
        errors = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Agent {i} failed: {str(result)}")
        
        success = len(errors) == 0
        
        return self.create_response(
            success=success,
            data=report,
            error='; '.join(errors) if errors else None,
            metadata={'agents_executed': 3, 'errors_count': len(errors)}
        )
    
    async def execute_quick_analysis(self, 
                                    input_data: Dict[str, Any],
                                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute quick analysis workflow
        
        Args:
            input_data: Input data
            context: Additional context
            
        Returns:
            Quick analysis results
        """
        session_id = input_data['session_id']
        
        # Get dataframe from session
        df = SessionState.get_dataframe(session_id)
        if df is None:
            return self.create_response(
                success=False,
                error="No dataframe found in session"
            )
        
        # Generate text twin
        text_twin = self.text_twin_generator.generate_twin(df)
        
        # Execute quick EDA
        eda_result = await self.eda_specialist.execute({
            'dataframe_twin': text_twin,
            'analysis_type': 'quick',
            'focus_areas': ['summary', 'correlations', 'distributions']
        })
        
        # Create quick report
        report = {
            'summary': eda_result.get('data', {}).get('summary', {}),
            'key_insights': eda_result.get('data', {}).get('key_insights', []),
            'recommendations': eda_result.get('data', {}).get('recommendations', []),
            'metadata': {
                'session_id': session_id,
                'workflow': 'quick_analysis',
                'dataframe_shape': df.shape,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return self.create_response(
            success=eda_result.get('success', False),
            data=report,
            error=eda_result.get('error')
        )
    
    async def execute_data_cleaning(self, 
                                   input_data: Dict[str, Any],
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute data cleaning workflow
        
        Args:
            input_data: Input data
            context: Additional context
            
        Returns:
            Data cleaning results
        """
        session_id = input_data['session_id']
        cleaning_options = input_data.get('cleaning_options', {})
        
        # Get dataframe from session
        df = SessionState.get_dataframe(session_id)
        if df is None:
            return self.create_response(
                success=False,
                error="No dataframe found in session"
            )
        
        # Generate text twin
        text_twin = self.text_twin_generator.generate_twin(df)
        
        # Execute quality inspection first
        quality_result = await self.quality_inspector.execute({
            'dataframe_twin': text_twin
        })
        
        if not quality_result.get('success', False):
            return self.create_response(
                success=False,
                error="Quality inspection failed",
                data={'quality_result': quality_result}
            )
        
        # Execute data engineering for cleaning
        cleaning_result = await self.data_engineer.execute({
            'dataframe_twin': text_twin,
            'operation': 'cleaning',
            'quality_report': quality_result.get('data', {}),
            'options': cleaning_options
        })
        
        # Update session with cleaned dataframe
        if cleaning_result.get('success', False) and 'cleaned_dataframe' in cleaning_result.get('data', {}):
            cleaned_df = cleaning_result['data']['cleaned_dataframe']
            SessionState.update_dataframe(
                session_id, 
                cleaned_df,
                "Data cleaning workflow"
            )
        
        report = {
            'quality_assessment': quality_result.get('data', {}),
            'cleaning_operations': cleaning_result.get('data', {}).get('operations', []),
            'before_after': {
                'original_shape': df.shape,
                'cleaned_shape': cleaned_df.shape if 'cleaned_df' in locals() else df.shape,
                'rows_removed': df.shape[0] - (cleaned_df.shape[0] if 'cleaned_df' in locals() else df.shape[0]),
                'columns_modified': cleaning_result.get('data', {}).get('columns_modified', [])
            },
            'metadata': {
                'session_id': session_id,
                'workflow': 'data_cleaning',
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return self.create_response(
            success=cleaning_result.get('success', False),
            data=report,
            error=cleaning_result.get('error')
        )
    
    async def execute_feature_engineering(self, 
                                         input_data: Dict[str, Any],
                                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute feature engineering workflow
        
        Args:
            input_data: Input data
            context: Additional context
            
        Returns:
            Feature engineering results
        """
        session_id = input_data['session_id']
        target_column = input_data.get('target_column')
        
        # Get dataframe from session
        df = SessionState.get_dataframe(session_id)
        if df is None:
            return self.create_response(
                success=False,
                error="No dataframe found in session"
            )
        
        # Generate text twin
        text_twin = self.text_twin_generator.generate_twin(df)
        
        # Execute data engineering for feature generation
        feature_result = await self.data_engineer.execute({
            'dataframe_twin': text_twin,
            'operation': 'feature_engineering',
            'target_column': target_column
        })
        
        # Update session with engineered features
        if feature_result.get('success', False) and 'engineered_dataframe' in feature_result.get('data', {}):
            engineered_df = feature_result['data']['engineered_dataframe']
            SessionState.update_dataframe(
                session_id, 
                engineered_df,
                "Feature engineering workflow"
            )
        
        report = {
            'new_features': feature_result.get('data', {}).get('new_features', []),
            'feature_importance': feature_result.get('data', {}).get('feature_importance', {}),
            'transformations_applied': feature_result.get('data', {}).get('transformations_applied', []),
            'before_after': {
                'original_shape': df.shape,
                'engineered_shape': engineered_df.shape if 'engineered_df' in locals() else df.shape,
                'features_added': len(feature_result.get('data', {}).get('new_features', []))
            },
            'metadata': {
                'session_id': session_id,
                'workflow': 'feature_engineering',
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return self.create_response(
            success=feature_result.get('success', False),
            data=report,
            error=feature_result.get('error')
        )
    
    async def execute_ml_pipeline(self, 
                                 input_data: Dict[str, Any],
                                 context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute ML pipeline workflow
        
        Args:
            input_data: Input data
            context: Additional context
            
        Returns:
            ML pipeline results
        """
        session_id = input_data['session_id']
        task_type = input_data.get('task_type', 'classification')  # or 'regression'
        target_column = input_data.get('target_column')
        
        # Get dataframe from session
        df = SessionState.get_dataframe(session_id)
        if df is None:
            return self.create_response(
                success=False,
                error="No dataframe found in session"
            )
        
        if not target_column:
            return self.create_response(
                success=False,
                error="Target column must be specified for ML pipeline"
            )
        
        if target_column not in df.columns:
            return self.create_response(
                success=False,
                error=f"Target column '{target_column}' not found in dataframe"
            )
        
        # Generate text twin
        text_twin = self.text_twin_generator.generate_twin(df)
        
        # Execute ML specialist
        ml_result = await self.ml_specialist.execute({
            'dataframe_twin': text_twin,
            'task_type': task_type,
            'target_column': target_column,
            'options': input_data.get('ml_options', {})
        })
        
        report = {
            'model_performance': ml_result.get('data', {}).get('performance', {}),
            'best_model': ml_result.get('data', {}).get('best_model', {}),
            'feature_importance': ml_result.get('data', {}).get('feature_importance', {}),
            'predictions_sample': ml_result.get('data', {}).get('predictions_sample', []),
            'recommendations': ml_result.get('data', {}).get('recommendations', []),
            'metadata': {
                'session_id': session_id,
                'workflow': 'ml_pipeline',
                'task_type': task_type,
                'target_column': target_column,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return self.create_response(
            success=ml_result.get('success', False),
            data=report,
            error=ml_result.get('error')
        )
    
    async def execute_notebook_generation(self, 
                                         input_data: Dict[str, Any],
                                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute notebook generation workflow
        
        Args:
            input_data: Input data
            context: Additional context
            
        Returns:
            Notebook generation results
        """
        session_id = input_data['session_id']
        notebook_type = input_data.get('notebook_type', 'comprehensive_eda')
        user_context = input_data.get('user_context', '')
        
        # Get dataframe from session
        df = SessionState.get_dataframe(session_id)
        if df is None:
            return self.create_response(
                success=False,
                error="No dataframe found in session"
            )
        
        # Generate text twin
        text_twin = self.text_twin_generator.generate_twin(df)
        
        # Execute notebook agent
        notebook_result = await self.notebook_agent.execute({
            'dataframe_twin': text_twin,
            'notebook_type': notebook_type,
            'user_context': user_context
        })
        
        # Create notebook in session
        if notebook_result.get('success', False):
            notebook_data = notebook_result.get('data', {})
            SessionState.add_notebook(session_id, notebook_data)
        
        report = {
            'notebook': notebook_result.get('data', {}),
            'metadata': {
                'session_id': session_id,
                'workflow': 'notebook_generation',
                'notebook_type': notebook_type,
                'cell_count': len(notebook_result.get('data', {}).get('cells', [])),
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return self.create_response(
            success=notebook_result.get('success', False),
            data=report,
            error=notebook_result.get('error')
        )
    
    def _update_session_id(self, session_id: str):
        """Update session ID for all agents"""
        self.session_id = session_id
        self.eda_specialist.session_id = session_id
        self.storyteller.session_id = session_id
        self.quality_inspector.session_id = session_id
        self.notebook_agent.session_id = session_id
        self.data_engineer.session_id = session_id
        self.ml_specialist.session_id = session_id
    
    async def analyze_workflow_performance(self) -> Dict[str, Any]:
        """
        Analyze performance of all workflows
        
        Returns:
            Performance analysis
        """
        performance_data = []
        
        for workflow_name in self.workflows.keys():
            # Get execution history for this workflow
            workflow_executions = [
                exec for exec in self.execution_history
                if f'workflow_{workflow_name}' in exec.get('operation', '')
            ]
            
            if workflow_executions:
                success_count = sum(1 for exec in workflow_executions if exec.get('success', False))
                total_count = len(workflow_executions)
                avg_duration = sum(
                    exec.get('duration_ms', 0) for exec in workflow_executions
                ) / total_count if total_count > 0 else 0
                
                performance_data.append({
                    'workflow': workflow_name,
                    'total_executions': total_count,
                    'success_rate': (success_count / total_count) * 100 if total_count > 0 else 0,
                    'avg_duration_ms': avg_duration,
                    'last_executed': workflow_executions[-1].get('timestamp') if workflow_executions else None
                })
        
        return self.create_response(
            success=True,
            data={'workflow_performance': performance_data}
        )
    
    def get_available_workflows(self) -> Dict[str, Any]:
        """Get list of available workflows"""
        workflow_descriptions = {
            'comprehensive_eda': 'Comprehensive Exploratory Data Analysis',
            'quick_analysis': 'Quick Data Analysis and Insights',
            'data_cleaning': 'Automated Data Cleaning and Quality Improvement',
            'feature_engineering': 'Feature Generation and Transformation',
            'ml_pipeline': 'End-to-end Machine Learning Pipeline',
            'notebook_generation': 'Interactive Notebook Generation'
        }
        
        return self.create_response(
            success=True,
            data={
                'available_workflows': list(self.workflows.keys()),
                'workflow_descriptions': workflow_descriptions,
                'total_workflows': len(self.workflows)
            }
        )