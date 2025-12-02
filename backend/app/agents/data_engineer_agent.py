from .base_agent import BaseAgent, AgentConfig
from app.core.logger import log_agent_operation
import pandas as pd
import numpy as np
from typing import Dict, Any

class DataEngineerAgent(BaseAgent):
    """
    Data Engineer Agent - Handles data cleaning, preprocessing, and feature engineering
    """
    
    def __init__(self, 
                 config: AgentConfig = None,
                 session_id: str = None):
        super().__init__(
            name="DataEngineerAgent",
            description="Handles data cleaning, preprocessing, and feature engineering",
            config=config or AgentConfig(model="gpt-3.5-turbo", temperature=0.1),
            session_id=session_id
        )
    
    @log_agent_operation
    async def execute(self, 
                     input_data: Dict[str, Any],
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process data cleaning and feature engineering
        """
        if not self.validate_input(input_data, ['dataframe_twin']):
            return self.create_response(
                success=False,
                error="Missing required input: dataframe_twin"
            )
        
        try:
            text_twin = input_data['dataframe_twin']
            operation = input_data.get('operation', 'clean')
            
            if operation == 'clean':
                result = await self._clean_data(text_twin)
            elif operation == 'engineer_features':
                result = await self._engineer_features(text_twin)
            elif operation == 'transform':
                result = await self._transform_data(text_twin)
            else:
                return self.create_response(
                    success=False,
                    error=f"Unknown operation: {operation}"
                )
            
            return self.create_response(success=True, data=result)
            
        except Exception as e:
            self.logger.log_error(
                error_type="data_engineering",
                error_message=str(e),
                context={'operation': input_data.get('operation')}
            )
            return self.create_response(
                success=False,
                error=f"Data engineering failed: {str(e)}"
            )
    
    async def _clean_data(self, text_twin: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and preprocess data"""
        # Mock cleaning logic
        cleaned_stats = {
            'original_rows': text_twin.get('metadata', {}).get('shape', [0, 0])[0],
            'original_columns': text_twin.get('metadata', {}).get('shape', [0, 0])[1],
            'cleaning_operations': [
                'Removed duplicate rows',
                'Handled missing values',
                'Standardized column names',
                'Fixed data types'
            ],
            'result': 'Data cleaned successfully'
        }
        
        return {
            'cleaned_data_twin': text_twin,  # In production, this would be the cleaned version
            'statistics': cleaned_stats
        }
    
    async def _engineer_features(self, text_twin: Dict[str, Any]) -> Dict[str, Any]:
        """Engineer new features"""
        # Mock feature engineering
        new_features = [
            {'name': 'age_group', 'description': 'Categorized age into groups'},
            {'name': 'income_category', 'description': 'Binned income into categories'},
            {'name': 'purchase_frequency', 'description': 'Calculated purchase frequency'},
            {'name': 'customer_segment', 'description': 'Created customer segments'}
        ]
        
        return {
            'new_features': new_features,
            'total_features_added': len(new_features),
            'feature_descriptions': {feat['name']: feat['description'] for feat in new_features}
        }
    
    async def _transform_data(self, text_twin: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data (normalization, encoding, etc.)"""
        # Mock transformations
        transformations = [
            'Normalized numerical columns',
            'Encoded categorical variables',
            'Scaled features to [0,1] range',
            'Created datetime features if applicable'
        ]
        
        return {
            'transformations_applied': transformations,
            'transformation_summary': f"Applied {len(transformations)} transformations"
        }