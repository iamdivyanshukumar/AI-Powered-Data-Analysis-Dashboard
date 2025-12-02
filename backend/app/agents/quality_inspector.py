from typing import Dict, Any, List, Optional
import json
import pandas as pd
import numpy as np
from datetime import datetime

from .base_agent import BaseAgent, AgentConfig
from app.core.logger import log_agent_operation

import logging

logger = logging.getLogger(__name__)

class QualityInspector(BaseAgent):
    """
    Quality Inspector Agent - Performs comprehensive data quality assessment
    """
    
    def __init__(self, 
                 config: AgentConfig = None,
                 session_id: str = None):
        """
        Initialize Quality Inspector
        
        Args:
            config: Agent configuration
            session_id: Session identifier
        """
        super().__init__(
            name="QualityInspector",
            description="Comprehensive data quality assessment and validation",
            config=config or AgentConfig(model="gpt-4", temperature=0.1),
            session_id=session_id
        )
        
        # Quality dimensions to check
        self.quality_dimensions = [
            'completeness',
            'accuracy',
            'consistency',
            'validity',
            'uniqueness',
            'timeliness',
            'relevance'
        ]
        
        # Quality thresholds
        self.thresholds = {
            'completeness': {'excellent': 95, 'good': 85, 'fair': 70, 'poor': 0},
            'accuracy': {'excellent': 98, 'good': 90, 'fair': 80, 'poor': 0},
            'consistency': {'excellent': 95, 'good': 85, 'fair': 75, 'poor': 0},
            'validity': {'excellent': 98, 'good': 90, 'fair': 80, 'poor': 0},
            'uniqueness': {'excellent': 99, 'good': 95, 'fair': 90, 'poor': 0}
        }
        
        logger.info("Quality Inspector agent initialized")
    
    @log_agent_operation
    async def execute(self, 
                     input_data: Dict[str, Any],
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute data quality assessment
        
        Args:
            input_data: Must contain 'dataframe_twin'
            context: Additional context
            
        Returns:
            Quality assessment results
        """
        # Validate input
        if not self.validate_input(input_data, ['dataframe_twin']):
            return self.create_response(
                success=False,
                error="Missing required 'dataframe_twin' in input"
            )
        
        text_twin = input_data['dataframe_twin']
        quality_dimensions = input_data.get('quality_dimensions', self.quality_dimensions)
        detailed_analysis = input_data.get('detailed_analysis', True)
        
        try:
            # Extract metadata and statistics
            metadata = text_twin.get('metadata', {})
            statistics = text_twin.get('statistics', {})
            schema = text_twin.get('schema', {})
            
            # Perform quality assessment
            quality_assessment = await self._assess_data_quality(
                metadata, statistics, schema, quality_dimensions, detailed_analysis
            )
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(quality_assessment)
            
            # Generate quality report
            quality_report = self._generate_quality_report(quality_assessment, overall_score)
            
            # Prepare response
            result = {
                'quality_assessment': quality_assessment,
                'quality_report': quality_report,
                'overall_score': overall_score,
                'grade': self._calculate_grade(overall_score),
                'recommendations': self._generate_recommendations(quality_assessment),
                'metadata': {
                    'dimensions_assessed': quality_dimensions,
                    'dataframe_shape': metadata.get('shape', []),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            return self.create_response(
                success=True,
                data=result
            )
            
        except Exception as e:
            self.logger.log_error(
                error_type="quality_assessment",
                error_message=str(e),
                context={'dimensions': quality_dimensions}
            )
            
            return self.create_response(
                success=False,
                error=f"Quality assessment failed: {str(e)}"
            )
    
    async def _assess_data_quality(self,
                                 metadata: Dict[str, Any],
                                 statistics: Dict[str, Any],
                                 schema: Dict[str, Any],
                                 dimensions: List[str],
                                 detailed: bool = True) -> Dict[str, Any]:
        """
        Assess data quality across specified dimensions
        """
        assessment = {}
        
        for dimension in dimensions:
            if dimension == 'completeness':
                assessment[dimension] = await self._assess_completeness(metadata, statistics, detailed)
            elif dimension == 'accuracy':
                assessment[dimension] = await self._assess_accuracy(metadata, statistics, schema, detailed)
            elif dimension == 'consistency':
                assessment[dimension] = await self._assess_consistency(metadata, statistics, detailed)
            elif dimension == 'validity':
                assessment[dimension] = await self._assess_validity(metadata, statistics, schema, detailed)
            elif dimension == 'uniqueness':
                assessment[dimension] = await self._assess_uniqueness(metadata, statistics, detailed)
            elif dimension == 'timeliness':
                assessment[dimension] = await self._assess_timeliness(metadata, detailed)
            elif dimension == 'relevance':
                assessment[dimension] = await self._assess_relevance(metadata, detailed)
        
        return assessment
    
    async def _assess_completeness(self,
                                 metadata: Dict[str, Any],
                                 statistics: Dict[str, Any],
                                 detailed: bool = True) -> Dict[str, Any]:
        """Assess data completeness"""
        basic_stats = statistics.get('basic', {})
        numerical_stats = statistics.get('numerical', {})
        categorical_stats = statistics.get('categorical', {})
        
        total_cells = metadata.get('total_rows', 0) * metadata.get('total_columns', 0)
        missing_cells = basic_stats.get('missing_values', 0)
        
        if total_cells == 0:
            completeness_score = 0
        else:
            completeness_score = ((total_cells - missing_cells) / total_cells) * 100
        
        # Column-wise completeness
        column_completeness = {}
        if detailed:
            # Numerical columns
            for col, stats in numerical_stats.items():
                missing_pct = stats.get('missing_percentage', 0)
                column_completeness[col] = {
                    'completeness': 100 - missing_pct,
                    'missing_count': stats.get('missing_count', 0),
                    'missing_percentage': missing_pct
                }
            
            # Categorical columns
            for col, stats in categorical_stats.items():
                missing_pct = stats.get('missing_percentage', 0)
                column_completeness[col] = {
                    'completeness': 100 - missing_pct,
                    'missing_count': stats.get('missing', 0),
                    'missing_percentage': missing_pct
                }
        
        # Pattern analysis
        missing_pattern = self._analyze_missing_pattern(column_completeness)
        
        return {
            'score': round(completeness_score, 2),
            'grade': self._get_dimension_grade('completeness', completeness_score),
            'metrics': {
                'total_cells': total_cells,
                'missing_cells': missing_cells,
                'completeness_percentage': round(completeness_score, 2),
                'columns_with_missing': len([c for c in column_completeness.values() 
                                            if c.get('missing_percentage', 0) > 0])
            },
            'column_analysis': column_completeness if detailed else None,
            'missing_pattern': missing_pattern,
            'issues': self._identify_completeness_issues(column_completeness),
            'recommendations': self._get_completeness_recommendations(completeness_score, column_completeness)
        }
    
    async def _assess_accuracy(self,
                              metadata: Dict[str, Any],
                              statistics: Dict[str, Any],
                              schema: Dict[str, Any],
                              detailed: bool = True) -> Dict[str, Any]:
        """Assess data accuracy (heuristic based on patterns)"""
        numerical_stats = statistics.get('numerical', {})
        
        accuracy_issues = []
        column_accuracy = {}
        
        # Check for impossible values in numerical columns
        for col, stats in numerical_stats.items():
            col_type = schema.get(col, {}).get('type', 'unknown')
            
            if col_type == 'numerical':
                min_val = stats.get('min')
                max_val = stats.get('max')
                
                # Check for impossible ranges
                if min_val is not None and max_val is not None:
                    # Check for negative values where not expected
                    if min_val < 0 and self._should_be_positive(col):
                        accuracy_issues.append({
                            'column': col,
                            'issue': 'negative_values',
                            'description': f'Negative values found in {col}',
                            'severity': 'medium'
                        })
                    
                    # Check for unrealistic ranges
                    if self._is_unrealistic_range(col, min_val, max_val):
                        accuracy_issues.append({
                            'column': col,
                            'issue': 'unrealistic_range',
                            'description': f'Unrealistic value range in {col}',
                            'severity': 'high'
                        })
                
                # Check for decimal precision issues
                if self._has_decimal_issues(col, stats):
                    accuracy_issues.append({
                        'column': col,
                        'issue': 'precision_issue',
                        'description': f'Decimal precision issues in {col}',
                        'severity': 'low'
                    })
            
            # Calculate heuristic accuracy score
            accuracy_score = self._calculate_column_accuracy(col, stats, schema.get(col, {}))
            column_accuracy[col] = {
                'score': accuracy_score,
                'grade': self._get_dimension_grade('accuracy', accuracy_score),
                'issues': [issue for issue in accuracy_issues if issue.get('column') == col]
            }
        
        # Overall accuracy score (heuristic)
        if column_accuracy:
            overall_accuracy = sum(acc['score'] for acc in column_accuracy.values()) / len(column_accuracy)
        else:
            overall_accuracy = 100  # Default if no numerical columns
        
        return {
            'score': round(overall_accuracy, 2),
            'grade': self._get_dimension_grade('accuracy', overall_accuracy),
            'metrics': {
                'columns_assessed': len(column_accuracy),
                'accuracy_issues': len(accuracy_issues),
                'critical_issues': len([i for i in accuracy_issues if i.get('severity') == 'high'])
            },
            'column_analysis': column_accuracy if detailed else None,
            'accuracy_issues': accuracy_issues,
            'recommendations': self._get_accuracy_recommendations(accuracy_issues)
        }
    
    async def _assess_consistency(self,
                                 metadata: Dict[str, Any],
                                 statistics: Dict[str, Any],
                                 detailed: bool = True) -> Dict[str, Any]:
        """Assess data consistency"""
        consistency_issues = []
        column_consistency = {}
        
        # Check data type consistency
        schema = metadata.get('data_types', {})
        for col, dtype in schema.items():
            if isinstance(dtype, str):
                # Check for mixed types (heuristic)
                if 'mixed' in dtype.lower() or 'object' in dtype.lower():
                    consistency_issues.append({
                        'column': col,
                        'issue': 'mixed_data_types',
                        'description': f'Potential mixed data types in {col}',
                        'severity': 'medium'
                    })
        
        # Check for inconsistent formatting
        formatting_issues = self._check_formatting_consistency(metadata, statistics)
        consistency_issues.extend(formatting_issues)
        
        # Check for inconsistent units
        unit_issues = self._check_unit_consistency(metadata)
        consistency_issues.extend(unit_issues)
        
        # Calculate consistency score
        total_columns = len(metadata.get('columns', []))
        if total_columns > 0:
            consistency_score = 100 - (len(consistency_issues) / total_columns * 20)  # Penalty factor
            consistency_score = max(0, min(100, consistency_score))
        else:
            consistency_score = 100
        
        return {
            'score': round(consistency_score, 2),
            'grade': self._get_dimension_grade('consistency', consistency_score),
            'metrics': {
                'total_columns': total_columns,
                'consistency_issues': len(consistency_issues),
                'formatting_issues': len(formatting_issues),
                'unit_issues': len(unit_issues)
            },
            'consistency_issues': consistency_issues,
            'recommendations': self._get_consistency_recommendations(consistency_issues)
        }
    
    async def _assess_validity(self,
                              metadata: Dict[str, Any],
                              statistics: Dict[str, Any],
                              schema: Dict[str, Any],
                              detailed: bool = True) -> Dict[str, Any]:
        """Assess data validity (adherence to constraints)"""
        validity_issues = []
        column_validity = {}
        
        numerical_stats = statistics.get('numerical', {})
        categorical_stats = statistics.get('categorical', {})
        
        # Check numerical column validity
        for col, stats in numerical_stats.items():
            col_info = schema.get(col, {})
            col_type = col_info.get('type', 'unknown')
            
            if col_type == 'numerical':
                # Check for out-of-bounds values
                bounds_issues = self._check_value_bounds(col, stats, col_info)
                validity_issues.extend(bounds_issues)
                
                # Check for invalid numerical values
                invalid_numerics = self._check_invalid_numerics(col, stats)
                validity_issues.extend(invalid_numerics)
                
                # Calculate validity score for column
                validity_score = self._calculate_column_validity(col, stats, bounds_issues, invalid_numerics)
                column_validity[col] = {
                    'score': validity_score,
                    'grade': self._get_dimension_grade('validity', validity_score),
                    'issues': bounds_issues + invalid_numerics
                }
        
        # Check categorical column validity
        for col, stats in categorical_stats.items():
            col_info = schema.get(col, {})
            
            # Check for invalid categories
            category_issues = self._check_invalid_categories(col, stats, col_info)
            validity_issues.extend(category_issues)
            
            # Calculate validity score for column
            validity_score = self._calculate_categorical_validity(col, stats, category_issues)
            column_validity[col] = {
                'score': validity_score,
                'grade': self._get_dimension_grade('validity', validity_score),
                'issues': category_issues
            }
        
        # Overall validity score
        if column_validity:
            overall_validity = sum(val['score'] for val in column_validity.values()) / len(column_validity)
        else:
            overall_validity = 100
        
        return {
            'score': round(overall_validity, 2),
            'grade': self._get_dimension_grade('validity', overall_validity),
            'metrics': {
                'columns_assessed': len(column_validity),
                'validity_issues': len(validity_issues),
                'bounds_violations': len([i for i in validity_issues if i.get('issue') == 'out_of_bounds']),
                'invalid_values': len([i for i in validity_issues if i.get('issue') == 'invalid_value'])
            },
            'column_analysis': column_validity if detailed else None,
            'validity_issues': validity_issues,
            'recommendations': self._get_validity_recommendations(validity_issues)
        }
    
    async def _assess_uniqueness(self,
                                metadata: Dict[str, Any],
                                statistics: Dict[str, Any],
                                detailed: bool = True) -> Dict[str, Any]:
        """Assess data uniqueness"""
        basic_stats = statistics.get('basic', {})
        categorical_stats = statistics.get('categorical', {})
        
        duplicate_rows = basic_stats.get('duplicate_rows', 0)
        total_rows = metadata.get('total_rows', 1)
        
        # Row uniqueness
        if total_rows > 0:
            uniqueness_score = 100 - (duplicate_rows / total_rows * 100)
        else:
            uniqueness_score = 100
        
        # Column uniqueness analysis
        column_uniqueness = {}
        uniqueness_issues = []
        
        for col, stats in categorical_stats.items():
            unique_count = stats.get('unique_count', 0)
            total_count = total_rows - stats.get('missing', 0)
            
            if total_count > 0:
                uniqueness_ratio = (unique_count / total_count) * 100
                
                column_uniqueness[col] = {
                    'unique_count': unique_count,
                    'total_count': total_count,
                    'uniqueness_ratio': round(uniqueness_ratio, 2),
                    'is_identifier': uniqueness_ratio == 100,
                    'is_low_diversity': uniqueness_ratio < 10
                }
                
                # Check for uniqueness issues
                if uniqueness_ratio == 100 and total_count > 1:
                    # Potential identifier column
                    uniqueness_issues.append({
                        'column': col,
                        'issue': 'potential_identifier',
                        'description': f'Column {col} contains only unique values',
                        'severity': 'info'
                    })
                elif uniqueness_ratio < 10:
                    # Very low diversity
                    uniqueness_issues.append({
                        'column': col,
                        'issue': 'low_diversity',
                        'description': f'Column {col} has very low diversity ({uniqueness_ratio:.1f}%)',
                        'severity': 'medium'
                    })
        
        # Check for duplicate rows
        if duplicate_rows > 0:
            uniqueness_issues.append({
                'issue': 'duplicate_rows',
                'description': f'Found {duplicate_rows} duplicate rows',
                'severity': 'high' if (duplicate_rows / total_rows * 100) > 10 else 'medium'
            })
        
        return {
            'score': round(uniqueness_score, 2),
            'grade': self._get_dimension_grade('uniqueness', uniqueness_score),
            'metrics': {
                'total_rows': total_rows,
                'duplicate_rows': duplicate_rows,
                'duplicate_percentage': round((duplicate_rows / total_rows * 100), 2) if total_rows > 0 else 0,
                'potential_identifiers': len([c for c in column_uniqueness.values() if c.get('is_identifier')]),
                'low_diversity_columns': len([c for c in column_uniqueness.values() if c.get('is_low_diversity')])
            },
            'column_analysis': column_uniqueness if detailed else None,
            'uniqueness_issues': uniqueness_issues,
            'recommendations': self._get_uniqueness_recommendations(uniqueness_issues, duplicate_rows)
        }
    
    async def _assess_timeliness(self,
                                metadata: Dict[str, Any],
                                detailed: bool = True) -> Dict[str, Any]:
        """Assess data timeliness (heuristic based on metadata)"""
        # This is a heuristic assessment since we don't have actual timestamps
        timeliness_score = 100  # Default
        
        # Check if there are datetime columns
        temporal_cols = metadata.get('temporal_columns', [])
        has_temporal = len(temporal_cols) > 0
        
        timeliness_issues = []
        
        if has_temporal:
            # If there are temporal columns, assume data might be time-sensitive
            timeliness_score = 85  # Slightly reduced score
            
            timeliness_issues.append({
                'issue': 'temporal_data_present',
                'description': 'Dataset contains temporal columns - consider freshness assessment',
                'severity': 'info'
            })
        else:
            timeliness_issues.append({
                'issue': 'no_temporal_data',
                'description': 'No temporal columns found - timeliness assessment limited',
                'severity': 'info'
            })
        
        return {
            'score': timeliness_score,
            'grade': self._get_dimension_grade('timeliness', timeliness_score),
            'metrics': {
                'has_temporal_data': has_temporal,
                'temporal_columns': temporal_cols,
                'assessment_type': 'heuristic'
            },
            'timeliness_issues': timeliness_issues,
            'recommendations': [
                'Add data collection timestamps for better timeliness assessment',
                'Implement data freshness monitoring if this is time-sensitive data'
            ]
        }
    
    async def _assess_relevance(self,
                               metadata: Dict[str, Any],
                               detailed: bool = True) -> Dict[str, Any]:
        """Assess data relevance (heuristic)"""
        columns = metadata.get('columns', [])
        
        relevance_issues = []
        column_relevance = {}
        
        # Heuristic relevance assessment based on column names
        for col in columns:
            relevance_score = self._assess_column_relevance(col)
            column_relevance[col] = {
                'score': relevance_score,
                'grade': self._get_dimension_grade('relevance', relevance_score),
                'notes': self._get_relevance_notes(col, relevance_score)
            }
            
            if relevance_score < 70:
                relevance_issues.append({
                    'column': col,
                    'issue': 'low_relevance',
                    'description': f'Column {col} may have low relevance',
                    'severity': 'low'
                })
        
        # Overall relevance score
        if column_relevance:
            overall_relevance = sum(rel['score'] for rel in column_relevance.values()) / len(column_relevance)
        else:
            overall_relevance = 100
        
        return {
            'score': round(overall_relevance, 2),
            'grade': self._get_dimension_grade('relevance', overall_relevance),
            'metrics': {
                'columns_assessed': len(columns),
                'low_relevance_columns': len([c for c in column_relevance.values() if c.get('score', 100) < 70]),
                'assessment_method': 'heuristic_based_on_naming'
            },
            'column_analysis': column_relevance if detailed else None,
            'relevance_issues': relevance_issues,
            'recommendations': [
                'Review column relevance with domain experts',
                'Consider removing or archiving low-relevance columns',
                'Document the purpose of each column'
            ]
        }
    
    # Helper methods for quality assessment
    
    def _analyze_missing_pattern(self, column_completeness: Dict[str, Dict]) -> Dict[str, Any]:
        """Analyze pattern of missing data"""
        missing_cols = {col: info for col, info in column_completeness.items() 
                       if info.get('missing_percentage', 0) > 0}
        
        if not missing_cols:
            return {'pattern': 'complete', 'description': 'No missing data'}
        
        # Calculate statistics
        missing_percentages = [info.get('missing_percentage', 0) for info in missing_cols.values()]
        
        return {
            'pattern': 'random' if max(missing_percentages) < 20 else 'systematic',
            'description': f'Missing data in {len(missing_cols)} columns',
            'statistics': {
                'columns_with_missing': len(missing_cols),
                'max_missing_percentage': round(max(missing_percentages), 2),
                'avg_missing_percentage': round(sum(missing_percentages) / len(missing_percentages), 2),
                'missing_columns': list(missing_cols.keys())
            }
        }
    
    def _identify_completeness_issues(self, column_completeness: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """Identify completeness issues"""
        issues = []
        
        for col, info in column_completeness.items():
            missing_pct = info.get('missing_percentage', 0)
            
            if missing_pct > 50:
                issues.append({
                    'column': col,
                    'issue': 'high_missing_data',
                    'description': f'{missing_pct:.1f}% missing data in {col}',
                    'severity': 'critical'
                })
            elif missing_pct > 20:
                issues.append({
                    'column': col,
                    'issue': 'significant_missing_data',
                    'description': f'{missing_pct:.1f}% missing data in {col}',
                    'severity': 'high'
                })
            elif missing_pct > 5:
                issues.append({
                    'column': col,
                    'issue': 'moderate_missing_data',
                    'description': f'{missing_pct:.1f}% missing data in {col}',
                    'severity': 'medium'
                })
        
        return issues
    
    def _should_be_positive(self, column_name: str) -> bool:
        """Check if column should contain only positive values"""
        positive_indicators = ['price', 'cost', 'amount', 'salary', 'revenue', 'profit', 
                              'quantity', 'count', 'age', 'height', 'weight', 'distance']
        
        column_lower = column_name.lower()
        return any(indicator in column_lower for indicator in positive_indicators)
    
    def _is_unrealistic_range(self, column_name: str, min_val: float, max_val: float) -> bool:
        """Check for unrealistic value ranges"""
        column_lower = column_name.lower()
        
        # Define reasonable ranges for common columns
        ranges = {
            'age': (0, 150),
            'salary': (0, 10000000),  # 10 million
            'price': (0, 1000000),     # 1 million
            'temperature': (-100, 200),  # Celsius
            'percentage': (0, 100),
            'rating': (0, 10),
            'score': (0, 100)
        }
        
        for key, (min_range, max_range) in ranges.items():
            if key in column_lower:
                return min_val < min_range or max_val > max_range
        
        # Check for extreme outliers
        if min_val != 0 and max_val / min_val > 10000:  # Extreme range
            return True
        
        return False
    
    def _has_decimal_issues(self, column_name: str, stats: Dict[str, Any]) -> bool:
        """Check for decimal precision issues"""
        # Heuristic: if std is very small compared to mean, might have precision issues
        mean = stats.get('mean')
        std = stats.get('std')
        
        if mean and std and mean != 0:
            cv = std / mean
            if cv < 0.001:  # Very low coefficient of variation
                return True
        
        return False
    
    def _calculate_column_accuracy(self, column_name: str, stats: Dict[str, Any], 
                                 schema: Dict[str, Any]) -> float:
        """Calculate heuristic accuracy score for a column"""
        score = 100
        
        # Penalty for negative values where they shouldn't exist
        min_val = stats.get('min')
        if min_val is not None and min_val < 0 and self._should_be_positive(column_name):
            score -= 15
        
        # Penalty for unrealistic ranges
        max_val = stats.get('max')
        if min_val is not None and max_val is not None and self._is_unrealistic_range(column_name, min_val, max_val):
            score -= 20
        
        # Penalty for decimal issues
        if self._has_decimal_issues(column_name, stats):
            score -= 5
        
        # Bonus for reasonable statistical properties
        skewness = abs(stats.get('skewness', 0))
        if skewness < 1:  # Not too skewed
            score += 5
        
        return max(0, min(100, score))
    
    def _check_formatting_consistency(self, metadata: Dict[str, Any], 
                                    statistics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for formatting consistency issues"""
        issues = []
        
        # This is a simplified check - in reality would need actual data
        categorical_stats = statistics.get('categorical', {})
        
        for col, stats in categorical_stats.items():
            # Check for mixed case issues (heuristic based on unique values)
            unique_ratio = stats.get('unique_ratio', 0)
            if 0.1 < unique_ratio < 0.9:  # Moderate uniqueness
                # Could have formatting issues
                issues.append({
                    'column': col,
                    'issue': 'potential_formatting_inconsistency',
                    'description': f'Potential formatting inconsistencies in {col}',
                    'severity': 'low'
                })
        
        return issues
    
    def _check_unit_consistency(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for unit consistency issues"""
        issues = []
        columns = metadata.get('columns', [])
        
        # Look for columns that might have unit issues
        unit_keywords = ['weight', 'height', 'distance', 'temperature', 'speed', 'time']
        
        for col in columns:
            col_lower = col.lower()
            for keyword in unit_keywords:
                if keyword in col_lower:
                    issues.append({
                        'column': col,
                        'issue': 'unit_specification_needed',
                        'description': f'Column {col} might need unit specification',
                        'severity': 'medium'
                    })
                    break
        
        return issues
    
    def _check_value_bounds(self, column_name: str, stats: Dict[str, Any], 
                           schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for values outside reasonable bounds"""
        issues = []
        min_val = stats.get('min')
        max_val = stats.get('max')
        
        # Check based on column name
        if 'age' in column_name.lower() and min_val is not None and max_val is not None:
            if min_val < 0 or max_val > 150:
                issues.append({
                    'column': column_name,
                    'issue': 'out_of_bounds',
                    'description': f'Age values outside reasonable range (0-150): {min_val}-{max_val}',
                    'severity': 'high'
                })
        
        elif 'percentage' in column_name.lower() and min_val is not None and max_val is not None:
            if min_val < 0 or max_val > 100:
                issues.append({
                    'column': column_name,
                    'issue': 'out_of_bounds',
                    'description': f'Percentage values outside 0-100 range: {min_val}-{max_val}',
                    'severity': 'high'
                })
        
        return issues
    
    def _check_invalid_numerics(self, column_name: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for invalid numerical values"""
        issues = []
        
        # Check for placeholder values that might indicate missing data
        # Common placeholders: -1, -999, 999, 9999
        placeholder_check = self._check_for_placeholders(column_name, stats)
        if placeholder_check:
            issues.append(placeholder_check)
        
        return issues
    
    def _check_invalid_categories(self, column_name: str, stats: Dict[str, Any], 
                                 schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for invalid categorical values"""
        issues = []
        
        # Check for placeholder categories
        top_values = stats.get('top_values', {})
        for value in top_values:
            value_str = str(value).lower()
            if value_str in ['null', 'nan', 'none', 'unknown', 'missing', 'na', 'n/a', '-', '']:
                issues.append({
                    'column': column_name,
                    'issue': 'placeholder_categories',
                    'description': f'Found placeholder category: {value}',
                    'severity': 'medium'
                })
        
        return issues
    
    def _check_for_placeholders(self, column_name: str, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for common placeholder values"""
        min_val = stats.get('min')
        max_val = stats.get('max')
        
        common_placeholders = [-1, -999, 999, 9999, 99999]
        
        if min_val in common_placeholders or max_val in common_placeholders:
            return {
                'column': column_name,
                'issue': 'placeholder_values',
                'description': f'Potential placeholder values detected ({min_val}, {max_val})',
                'severity': 'medium'
            }
        
        return None
    
    def _calculate_column_validity(self, column_name: str, stats: Dict[str, Any],
                                 bounds_issues: List[Dict], invalid_numerics: List[Dict]) -> float:
        """Calculate validity score for a column"""
        score = 100
        
        # Penalties for issues
        if bounds_issues:
            score -= 20 * len([i for i in bounds_issues if i.get('severity') == 'high'])
            score -= 10 * len([i for i in bounds_issues if i.get('severity') == 'medium'])
        
        if invalid_numerics:
            score -= 15 * len([i for i in invalid_numerics if i.get('severity') == 'high'])
            score -= 5 * len([i for i in invalid_numerics if i.get('severity') == 'medium'])
        
        return max(0, min(100, score))
    
    def _calculate_categorical_validity(self, column_name: str, stats: Dict[str, Any],
                                       category_issues: List[Dict]) -> float:
        """Calculate validity score for a categorical column"""
        score = 100
        
        if category_issues:
            score -= 10 * len(category_issues)
        
        # Bonus for reasonable number of categories
        unique_count = stats.get('unique_count', 0)
        if 2 <= unique_count <= 50:  # Reasonable number of categories
            score += 5
        
        return max(0, min(100, score))
    
    def _assess_column_relevance(self, column_name: str) -> float:
        """Heuristic assessment of column relevance based on name"""
        column_lower = column_name.lower()
        
        # Common irrelevant indicators
        irrelevant_indicators = ['id', 'index', 'uuid', 'guid', 'key', 'hash', 'checksum', 
                                'timestamp', 'created', 'updated', 'deleted', 'row', 'version']
        
        # Common relevant indicators
        relevant_indicators = ['name', 'date', 'time', 'price', 'cost', 'value', 'amount',
                              'quantity', 'score', 'rating', 'status', 'type', 'category',
                              'age', 'gender', 'location', 'address', 'email', 'phone']
        
        score = 50  # Neutral starting point
        
        # Adjust based on indicators
        for indicator in irrelevant_indicators:
            if indicator in column_lower:
                score -= 20
        
        for indicator in relevant_indicators:
            if indicator in column_lower:
                score += 10
        
        # Penalize very short column names (often IDs)
        if len(column_name) <= 3:
            score -= 10
        
        # Bonus for descriptive names
        if len(column_name) > 15 and '_' in column_name:  # Descriptive with underscores
            score += 15
        
        return max(0, min(100, score))
    
    def _get_relevance_notes(self, column_name: str, relevance_score: float) -> str:
        """Get notes about column relevance"""
        if relevance_score >= 80:
            return "Highly relevant - clear business meaning"
        elif relevance_score >= 60:
            return "Moderately relevant - some business context"
        elif relevance_score >= 40:
            return "Neutral relevance - unclear business purpose"
        else:
            return "Low relevance - likely technical or identifier column"
    
    def _get_dimension_grade(self, dimension: str, score: float) -> str:
        """Get letter grade for a dimension score"""
        thresholds = self.thresholds.get(dimension, self.thresholds['completeness'])
        
        if score >= thresholds['excellent']:
            return 'A'
        elif score >= thresholds['good']:
            return 'B'
        elif score >= thresholds['fair']:
            return 'C'
        else:
            return 'D'
    
    def _calculate_overall_score(self, assessment: Dict[str, Any]) -> float:
        """Calculate overall data quality score"""
        scores = []
        weights = {
            'completeness': 0.25,
            'accuracy': 0.20,
            'consistency': 0.15,
            'validity': 0.20,
            'uniqueness': 0.10,
            'timeliness': 0.05,
            'relevance': 0.05
        }
        
        for dimension, results in assessment.items():
            if 'score' in results:
                weight = weights.get(dimension, 0.10)
                scores.append(results['score'] * weight)
        
        if scores:
            return round(sum(scores), 2)
        return 100.0
    
    def _calculate_grade(self, overall_score: float) -> str:
        """Calculate overall letter grade"""
        if overall_score >= 90:
            return 'A'
        elif overall_score >= 80:
            return 'B'
        elif overall_score >= 70:
            return 'C'
        elif overall_score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _generate_quality_report(self, assessment: Dict[str, Any], overall_score: float) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        report = {
            'summary': {
                'overall_score': overall_score,
                'overall_grade': self._calculate_grade(overall_score),
                'dimensions_assessed': list(assessment.keys()),
                'assessment_date': datetime.now().isoformat()
            },
            'dimension_scores': {},
            'key_findings': [],
            'risk_assessment': {
                'high_risk_issues': 0,
                'medium_risk_issues': 0,
                'low_risk_issues': 0
            }
        }
        
        # Collect dimension scores and key findings
        for dimension, results in assessment.items():
            report['dimension_scores'][dimension] = {
                'score': results.get('score', 0),
                'grade': results.get('grade', 'N/A')
            }
            
            # Extract key findings
            issues = results.get('issues', [])
            for issue in issues:
                severity = issue.get('severity', 'medium')
                
                if severity == 'high':
                    report['risk_assessment']['high_risk_issues'] += 1
                    report['key_findings'].append({
                        'issue': issue.get('description', 'Unknown issue'),
                        'severity': 'high',
                        'dimension': dimension,
                        'column': issue.get('column')
                    })
                elif severity == 'medium':
                    report['risk_assessment']['medium_risk_issues'] += 1
        
        # Sort key findings by severity
        report['key_findings'].sort(key=lambda x: 0 if x['severity'] == 'high' else 1)
        
        # Add overall assessment
        if overall_score >= 80:
            report['summary']['assessment'] = 'Good quality - suitable for analysis'
        elif overall_score >= 70:
            report['summary']['assessment'] = 'Fair quality - some improvements needed'
        elif overall_score >= 60:
            report['summary']['assessment'] = 'Poor quality - significant improvements needed'
        else:
            report['summary']['assessment'] = 'Very poor quality - not suitable for analysis'
        
        return report
    
    def _generate_recommendations(self, assessment: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on quality assessment"""
        recommendations = []
        
        for dimension, results in assessment.items():
            dim_recommendations = results.get('recommendations', [])
            recommendations.extend(dim_recommendations)
        
        # Add overall recommendations
        overall_score = self._calculate_overall_score(assessment)
        
        if overall_score < 70:
            recommendations.append("Consider comprehensive data cleaning before analysis")
            recommendations.append("Establish data quality monitoring processes")
        
        if overall_score >= 80:
            recommendations.append("Data quality is good - proceed with analysis")
        
        # Remove duplicates and limit
        unique_recommendations = list(dict.fromkeys(recommendations))
        return unique_recommendations[:10]
    
    # Recommendation generators for each dimension
    
    def _get_completeness_recommendations(self, completeness_score: float, 
                                         column_completeness: Dict[str, Dict]) -> List[str]:
        """Get recommendations for completeness issues"""
        recommendations = []
        
        if completeness_score < 90:
            recommendations.append("Implement data validation rules to prevent missing data")
        
        # Check for specific column issues
        high_missing_cols = [col for col, info in column_completeness.items() 
                            if info.get('missing_percentage', 0) > 20]
        
        if high_missing_cols:
            recommendations.append(f"Investigate missing data in columns: {', '.join(high_missing_cols[:3])}")
            recommendations.append("Consider imputation strategies for columns with high missing rates")
        
        if completeness_score < 70:
            recommendations.append("Review data collection processes to address systematic missingness")
        
        return recommendations[:5]
    
    def _get_accuracy_recommendations(self, accuracy_issues: List[Dict]) -> List[str]:
        """Get recommendations for accuracy issues"""
        recommendations = []
        
        high_severity = [issue for issue in accuracy_issues if issue.get('severity') == 'high']
        medium_severity = [issue for issue in accuracy_issues if issue.get('severity') == 'medium']
        
        if high_severity:
            recommendations.append("Immediate review needed for critical accuracy issues")
            high_columns = list(set(issue.get('column') for issue in high_severity))
            recommendations.append(f"Focus on: {', '.join(high_columns[:3])}")
        
        if medium_severity:
            recommendations.append("Implement range checks for numerical columns")
        
        if accuracy_issues:
            recommendations.append("Establish data accuracy validation rules")
        
        return recommendations[:5]
    
    def _get_consistency_recommendations(self, consistency_issues: List[Dict]) -> List[str]:
        """Get recommendations for consistency issues"""
        recommendations = []
        
        if consistency_issues:
            recommendations.append("Standardize data formats across the dataset")
            recommendations.append("Implement data transformation rules for consistency")
        
        formatting_issues = [issue for issue in consistency_issues 
                            if 'formatting' in issue.get('issue', '')]
        if formatting_issues:
            recommendations.append("Apply consistent formatting rules (e.g., case, date formats)")
        
        return recommendations[:5]
    
    def _get_validity_recommendations(self, validity_issues: List[Dict]) -> List[str]:
        """Get recommendations for validity issues"""
        recommendations = []
        
        bounds_issues = [issue for issue in validity_issues 
                        if issue.get('issue') == 'out_of_bounds']
        if bounds_issues:
            recommendations.append("Implement value range validation")
            recommendations.append("Add domain-specific validation rules")
        
        placeholder_issues = [issue for issue in validity_issues 
                             if 'placeholder' in issue.get('issue', '')]
        if placeholder_issues:
            recommendations.append("Replace placeholder values with proper missing value indicators")
        
        if validity_issues:
            recommendations.append("Establish data validation framework")
        
        return recommendations[:5]
    
    def _get_uniqueness_recommendations(self, uniqueness_issues: List[Dict], 
                                       duplicate_rows: int) -> List[str]:
        """Get recommendations for uniqueness issues"""
        recommendations = []
        
        if duplicate_rows > 0:
            duplicate_pct = duplicate_rows  # This would need total_rows to calculate percentage
            if duplicate_pct > 10:
                recommendations.append("Immediate deduplication required")
            else:
                recommendations.append("Remove duplicate rows before analysis")
            
            recommendations.append("Implement duplicate prevention in data collection")
        
        identifier_issues = [issue for issue in uniqueness_issues 
                            if 'identifier' in issue.get('issue', '')]
        if identifier_issues:
            recommendations.append("Verify that identifier columns are truly unique")
        
        low_diversity = [issue for issue in uniqueness_issues 
                        if 'low_diversity' in issue.get('issue', '')]
        if low_diversity:
            recommendations.append("Review low-diversity columns for data collection issues")
        
        return recommendations[:5]