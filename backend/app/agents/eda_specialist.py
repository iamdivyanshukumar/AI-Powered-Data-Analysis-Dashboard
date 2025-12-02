import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import json
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from sklearn.preprocessing import LabelEncoder

import logging

logger = logging.getLogger(__name__)

from .base_agent import BaseAgent, AgentConfig
from app.core.logger import log_agent_operation

class EDASpecialist(BaseAgent):
    """
    EDA Specialist Agent - Performs comprehensive exploratory data analysis
    """
    
    def __init__(self, 
                 config: AgentConfig = None,
                 session_id: str = None):
        """
        Initialize EDA Specialist
        
        Args:
            config: Agent configuration
            session_id: Session identifier
        """
        super().__init__(
            name="EDASpecialist",
            description="Performs comprehensive exploratory data analysis",
            config=config or AgentConfig(model="gpt-4", temperature=0.1),
            session_id=session_id
        )
        
        # Analysis templates
        self.analysis_templates = {
            'comprehensive': self._comprehensive_analysis,
            'quick': self._quick_analysis,
            'statistical': self._statistical_analysis,
            'visual': self._visual_analysis
        }
        
        logger.info("EDA Specialist agent initialized")
    
    @log_agent_operation
    async def execute(self, 
                     input_data: Dict[str, Any],
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute EDA analysis
        
        Args:
            input_data: Must contain 'dataframe_twin'
            context: Additional context
            
        Returns:
            EDA analysis results
        """
        # Validate input
        if not self.validate_input(input_data, ['dataframe_twin']):
            return self.create_response(
                success=False,
                error="Missing required 'dataframe_twin' in input"
            )
        
        text_twin = input_data['dataframe_twin']
        analysis_type = input_data.get('analysis_type', 'comprehensive')
        user_context = input_data.get('user_context', '')
        focus_areas = input_data.get('focus_areas', [])
        
        # Check if analysis type is supported
        if analysis_type not in self.analysis_templates:
            return self.create_response(
                success=False,
                error=f"Unsupported analysis type: {analysis_type}. "
                      f"Supported: {list(self.analysis_templates.keys())}"
            )
        
        try:
            # Extract metadata from twin
            metadata = text_twin.get('metadata', {})
            samples = text_twin.get('samples', {})
            statistics = text_twin.get('statistics', {})
            
            # Convert twin to analysis context
            analysis_context = self._create_analysis_context(
                metadata, statistics, samples, user_context, focus_areas
            )
            
            # Perform analysis
            analysis_func = self.analysis_templates[analysis_type]
            analysis_result = await analysis_func(analysis_context)
            
            # Generate insights
            insights = await self._generate_insights(analysis_result, user_context)
            
            # Create recommendations
            recommendations = await self._generate_recommendations(analysis_result)
            
            # Prepare response
            result = {
                'summary': self._create_summary(analysis_result),
                'detailed_analysis': analysis_result,
                'key_insights': insights,
                'recommendations': recommendations,
                'visualization_suggestions': self._suggest_visualizations(analysis_result),
                'metadata': {
                    'analysis_type': analysis_type,
                    'dataframe_shape': metadata.get('shape', []),
                    'columns_analyzed': len(metadata.get('columns', [])),
                    'focus_areas': focus_areas
                }
            }
            
            return self.create_response(
                success=True,
                data=result
            )
            
        except Exception as e:
            self.logger.log_error(
                error_type="eda_analysis",
                error_message=str(e),
                context={'analysis_type': analysis_type}
            )
            
            return self.create_response(
                success=False,
                error=f"EDA analysis failed: {str(e)}"
            )
    
    async def _comprehensive_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive EDA analysis"""
        analysis = {
            'data_quality': await self._analyze_data_quality(context),
            'descriptive_statistics': await self._compute_descriptive_stats(context),
            'distributions': await self._analyze_distributions(context),
            'correlations': await self._analyze_correlations(context),
            'categorical_analysis': await self._analyze_categorical(context),
            'outliers': await self._detect_outliers(context),
            'missing_patterns': await self._analyze_missing_patterns(context),
            'temporal_trends': await self._analyze_temporal_trends(context) if context.get('has_temporal') else {}
        }
        
        return analysis
    
    async def _quick_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform quick analysis"""
        analysis = {
            'summary_stats': await self._compute_summary_stats(context),
            'key_correlations': await self._get_key_correlations(context),
            'data_issues': await self._identify_data_issues(context),
            'quick_insights': await self._generate_quick_insights(context)
        }
        
        return analysis
    
    async def _statistical_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform statistical analysis"""
        analysis = {
            'hypothesis_tests': await self._perform_hypothesis_tests(context),
            'anova': await self._perform_anova(context) if context.get('has_categorical') else {},
            'regression_analysis': await self._perform_regression_analysis(context),
            'normality_tests': await self._test_normality(context),
            'variance_analysis': await self._analyze_variance(context)
        }
        
        return analysis
    
    async def _visual_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform visual analysis"""
        analysis = {
            'distribution_plots': await self._suggest_distribution_plots(context),
            'relationship_plots': await self._suggest_relationship_plots(context),
            'composition_plots': await self._suggest_composition_plots(context),
            'comparison_plots': await self._suggest_comparison_plots(context),
            'temporal_plots': await self._suggest_temporal_plots(context) if context.get('has_temporal') else {}
        }
        
        return analysis
    
    def _create_analysis_context(self, 
                                metadata: Dict[str, Any],
                                statistics: Dict[str, Any],
                                samples: Dict[str, Any],
                                user_context: str,
                                focus_areas: List[str]) -> Dict[str, Any]:
        """Create analysis context from text twin"""
        columns = metadata.get('columns', [])
        data_types = metadata.get('data_types', {})
        
        # Classify columns
        numerical_cols = []
        categorical_cols = []
        temporal_cols = []
        
        for col, dtype in data_types.items():
            if 'int' in str(dtype) or 'float' in str(dtype):
                numerical_cols.append(col)
            elif 'object' in str(dtype) or 'string' in str(dtype):
                categorical_cols.append(col)
            elif 'datetime' in str(dtype) or 'time' in str(dtype):
                temporal_cols.append(col)
        
        context = {
            'columns': columns,
            'numerical_columns': numerical_cols,
            'categorical_columns': categorical_cols,
            'temporal_columns': temporal_cols,
            'has_numerical': len(numerical_cols) > 0,
            'has_categorical': len(categorical_cols) > 0,
            'has_temporal': len(temporal_cols) > 0,
            'data_shape': metadata.get('shape', [0, 0]),
            'missing_values': metadata.get('missing_values', 0),
            'basic_statistics': statistics.get('basic', {}),
            'numerical_statistics': statistics.get('numerical', {}),
            'categorical_statistics': statistics.get('categorical', {}),
            'correlations': statistics.get('correlations', []),
            'samples': samples,
            'user_context': user_context,
            'focus_areas': focus_areas
        }
        
        return context
    
    async def _analyze_data_quality(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data quality"""
        basic_stats = context.get('basic_statistics', {})
        numerical_stats = context.get('numerical_statistics', {})
        categorical_stats = context.get('categorical_statistics', {})
        
        quality_issues = []
        quality_score = 100  # Start with perfect score
        
        # Check missing values
        missing_pct = basic_stats.get('missing_percentage', 0)
        if missing_pct > 0:
            severity = 'high' if missing_pct > 20 else 'medium' if missing_pct > 5 else 'low'
            quality_issues.append({
                'issue': 'missing_values',
                'severity': severity,
                'description': f'{missing_pct}% missing values',
                'impact': 'May affect analysis reliability'
            })
            quality_score -= min(30, missing_pct * 1.5)
        
        # Check duplicates
        duplicate_pct = basic_stats.get('duplicate_percentage', 0)
        if duplicate_pct > 0:
            severity = 'high' if duplicate_pct > 10 else 'medium' if duplicate_pct > 2 else 'low'
            quality_issues.append({
                'issue': 'duplicate_rows',
                'severity': severity,
                'description': f'{duplicate_pct}% duplicate rows',
                'impact': 'May skew statistical analysis'
            })
            quality_score -= min(20, duplicate_pct * 2)
        
        # Check numerical column quality
        for col, stats in numerical_stats.items():
            missing_pct = stats.get('missing_percentage', 0)
            if missing_pct > 50:
                quality_issues.append({
                    'issue': 'high_missing_numerical',
                    'severity': 'high',
                    'column': col,
                    'description': f'{missing_pct}% missing values',
                    'impact': 'Column may not be usable for analysis'
                })
                quality_score -= 10
        
        # Check categorical column cardinality
        for col, stats in categorical_stats.items():
            unique_ratio = stats.get('unique_ratio', 0)
            if unique_ratio > 0.9:
                quality_issues.append({
                    'issue': 'high_cardinality',
                    'severity': 'medium',
                    'column': col,
                    'description': 'High number of unique values',
                    'impact': 'May not be useful for grouping'
                })
                quality_score -= 5
        
        return {
            'overall_score': max(0, min(100, quality_score)),
            'quality_issues': quality_issues,
            'summary': {
                'total_issues': len(quality_issues),
                'critical_issues': len([i for i in quality_issues if i['severity'] == 'high']),
                'data_usable': quality_score >= 70,
                'recommendations': [
                    'Consider imputation for missing values' if missing_pct > 0 else None,
                    'Remove duplicate rows' if duplicate_pct > 0 else None,
                    'Review high cardinality columns' if any('high_cardinality' in i['issue'] for i in quality_issues) else None
                ]
            }
        }
    
    async def _compute_descriptive_stats(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compute descriptive statistics"""
        numerical_stats = context.get('numerical_statistics', {})
        categorical_stats = context.get('categorical_statistics', {})
        
        descriptive_stats = {
            'numerical': {},
            'categorical': {},
            'overall': {}
        }
        
        # Process numerical columns
        for col, stats in numerical_stats.items():
            descriptive_stats['numerical'][col] = {
                'count': stats.get('count', 0),
                'mean': stats.get('mean'),
                'std': stats.get('std'),
                'min': stats.get('min'),
                '25%': stats.get('q1'),
                '50%': stats.get('median'),
                '75%': stats.get('q3'),
                'max': stats.get('max'),
                'skewness': stats.get('skewness'),
                'kurtosis': stats.get('kurtosis'),
                'range': stats.get('max', 0) - stats.get('min', 0) if stats.get('max') and stats.get('min') else None,
                'cv': (stats.get('std', 0) / stats.get('mean', 1)) * 100 if stats.get('mean') and stats.get('mean') != 0 else None
            }
        
        # Process categorical columns
        for col, stats in categorical_stats.items():
            descriptive_stats['categorical'][col] = {
                'unique_values': stats.get('unique_count', 0),
                'most_frequent': stats.get('most_frequent', {}),
                'entropy': stats.get('entropy'),
                'missing': stats.get('missing', 0),
                'missing_percentage': stats.get('missing_percentage', 0)
            }
        
        # Overall statistics
        descriptive_stats['overall'] = {
            'total_columns': len(context.get('columns', [])),
            'numerical_columns': len(context.get('numerical_columns', [])),
            'categorical_columns': len(context.get('categorical_columns', [])),
            'temporal_columns': len(context.get('temporal_columns', [])),
            'total_rows': context.get('data_shape', [0, 0])[0],
            'memory_usage_mb': context.get('basic_statistics', {}).get('memory_usage_mb', 0)
        }
        
        return descriptive_stats
    
    async def _analyze_distributions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze distributions of numerical columns"""
        numerical_stats = context.get('numerical_statistics', {})
        distributions = {}
        
        for col, stats in numerical_stats.items():
            skewness = stats.get('skewness', 0)
            kurtosis = stats.get('kurtosis', 0)
            
            # Determine distribution type
            if abs(skewness) < 0.5:
                skew_label = 'Symmetric'
            elif skewness > 0:
                skew_label = 'Right-skewed'
            else:
                skew_label = 'Left-skewed'
            
            if abs(kurtosis) < 0.5:
                kurtosis_label = 'Mesokurtic (normal-like)'
            elif kurtosis > 0:
                kurtosis_label = 'Leptokurtic (peaked)'
            else:
                kurtosis_label = 'Platykurtic (flat)'
            
            # Check for normality
            is_normal = abs(skewness) < 1 and abs(kurtosis) < 1
            
            distributions[col] = {
                'skewness': skewness,
                'skewness_label': skew_label,
                'kurtosis': kurtosis,
                'kurtosis_label': kurtosis_label,
                'is_normal_like': is_normal,
                'outliers_present': stats.get('outliers', {}).get('count', 0) > 0,
                'outliers_percentage': stats.get('outliers', {}).get('percentage', 0),
                'iqr': stats.get('q3', 0) - stats.get('q1', 0) if stats.get('q1') and stats.get('q3') else None,
                'recommended_transformations': self._suggest_transformations(skewness, is_normal)
            }
        
        return distributions
    
    async def _analyze_correlations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze correlations between numerical columns"""
        correlations = context.get('correlations', [])
        numerical_cols = context.get('numerical_columns', [])
        
        if len(numerical_cols) < 2:
            return {'message': 'Not enough numerical columns for correlation analysis'}
        
        # Group correlations by strength
        strong_correlations = [c for c in correlations if abs(c.get('correlation', 0)) > 0.7]
        moderate_correlations = [c for c in correlations if 0.5 < abs(c.get('correlation', 0)) <= 0.7]
        weak_correlations = [c for c in correlations if abs(c.get('correlation', 0)) <= 0.5]
        
        # Find most correlated pairs
        top_correlations = sorted(
            correlations, 
            key=lambda x: abs(x.get('correlation', 0)), 
            reverse=True
        )[:10]
        
        # Identify potential multicollinearity
        multicollinearity_issues = []
        correlation_matrix = {}
        
        for corr in correlations:
            pair = tuple(sorted(corr['pair']))
            correlation_matrix[pair] = corr['correlation']
        
        # Check for highly correlated groups
        highly_correlated_groups = self._find_correlated_groups(correlation_matrix)
        
        return {
            'correlation_summary': {
                'total_pairs': len(correlations),
                'strong_correlations': len(strong_correlations),
                'moderate_correlations': len(moderate_correlations),
                'weak_correlations': len(weak_correlations)
            },
            'top_correlations': top_correlations,
            'strong_correlations': strong_correlations,
            'multicollinearity_issues': multicollinearity_issues,
            'highly_correlated_groups': highly_correlated_groups,
            'insights': self._generate_correlation_insights(correlations, numerical_cols)
        }
    
    async def _analyze_categorical(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze categorical columns"""
        categorical_stats = context.get('categorical_statistics', {})
        categorical_cols = context.get('categorical_columns', [])
        
        analysis = {}
        
        for col in categorical_cols:
            stats = categorical_stats.get(col, {})
            top_values = stats.get('top_values', {})
            unique_count = stats.get('unique_count', 0)
            
            # Calculate dominance
            if top_values:
                top_value_count = list(top_values.values())[0]
                total_count = context.get('data_shape', [0, 0])[0]
                dominance = (top_value_count / total_count) * 100 if total_count > 0 else 0
                
                is_imbalanced = dominance > 80
                is_diverse = unique_count > 10 and dominance < 30
                
                analysis[col] = {
                    'unique_values': unique_count,
                    'top_values': top_values,
                    'dominance_percentage': round(dominance, 2),
                    'entropy': stats.get('entropy', 0),
                    'is_imbalanced': is_imbalanced,
                    'is_diverse': is_diverse,
                    'missing_percentage': stats.get('missing_percentage', 0),
                    'recommendations': [
                        'Consider encoding for modeling' if unique_count < 10 else 'May need special handling due to high cardinality',
                        'Address class imbalance' if is_imbalanced else None
                    ]
                }
        
        return analysis
    
    async def _detect_outliers(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect outliers in numerical columns"""
        numerical_stats = context.get('numerical_statistics', {})
        outliers_report = {}
        
        for col, stats in numerical_stats.items():
            outlier_info = stats.get('outliers', {})
            if outlier_info:
                outliers_report[col] = {
                    'count': outlier_info.get('count', 0),
                    'percentage': outlier_info.get('percentage', 0),
                    'bounds': outlier_info.get('bounds', {}),
                    'severity': 'high' if outlier_info.get('percentage', 0) > 5 else 'medium' if outlier_info.get('percentage', 0) > 1 else 'low',
                    'potential_causes': self._suggest_outlier_causes(col, stats),
                    'handling_recommendations': self._suggest_outlier_handling(outlier_info.get('percentage', 0))
                }
        
        # Summary
        total_outliers = sum(col_report.get('count', 0) for col_report in outliers_report.values())
        outlier_cols = [col for col, report in outliers_report.items() if report.get('count', 0) > 0]
        
        return {
            'column_wise_outliers': outliers_report,
            'summary': {
                'columns_with_outliers': len(outlier_cols),
                'total_outliers': total_outliers,
                'most_affected_column': max(outliers_report.items(), key=lambda x: x[1].get('percentage', 0))[0] if outliers_report else None,
                'recommendation': 'Review outliers for potential data quality issues or natural variation'
            }
        }
    
    async def _analyze_missing_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns in missing data"""
        basic_stats = context.get('basic_statistics', {})
        numerical_stats = context.get('numerical_statistics', {})
        categorical_stats = context.get('categorical_statistics', {})
        
        missing_analysis = {
            'overall': {
                'total_missing': basic_stats.get('missing_values', 0),
                'percentage': basic_stats.get('missing_percentage', 0),
                'pattern': self._determine_missing_pattern(basic_stats.get('missing_percentage', 0))
            },
            'by_column_type': {
                'numerical': {},
                'categorical': {}
            },
            'patterns': {}
        }
        
        # Analyze numerical columns
        numerical_missing = {}
        for col, stats in numerical_stats.items():
            missing_pct = stats.get('missing_percentage', 0)
            if missing_pct > 0:
                numerical_missing[col] = {
                    'percentage': missing_pct,
                    'severity': 'high' if missing_pct > 20 else 'medium' if missing_pct > 5 else 'low'
                }
        
        # Analyze categorical columns
        categorical_missing = {}
        for col, stats in categorical_stats.items():
            missing_pct = stats.get('missing_percentage', 0)
            if missing_pct > 0:
                categorical_missing[col] = {
                    'percentage': missing_pct,
                    'severity': 'high' if missing_pct > 20 else 'medium' if missing_pct > 5 else 'low'
                }
        
        missing_analysis['by_column_type']['numerical'] = numerical_missing
        missing_analysis['by_column_type']['categorical'] = categorical_missing
        
        # Check for systematic missingness
        systematic_issues = self._check_systematic_missing(
            numerical_missing, 
            categorical_missing
        )
        missing_analysis['systematic_issues'] = systematic_issues
        
        # Imputation recommendations
        missing_analysis['imputation_recommendations'] = self._suggest_imputation_methods(
            numerical_missing, 
            categorical_missing
        )
        
        return missing_analysis
    
    async def _analyze_temporal_trends(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze temporal trends if temporal columns exist"""
        temporal_cols = context.get('temporal_columns', [])
        
        if not temporal_cols:
            return {'message': 'No temporal columns found'}
        
        analysis = {
            'temporal_columns': temporal_cols,
            'analysis_possible': len(temporal_cols) > 0,
            'suggested_analyses': [
                'Time series decomposition',
                'Seasonality analysis',
                'Trend analysis',
                'Periodicity detection'
            ],
            'visualizations': [
                'Line plots over time',
                'Seasonal subseries plots',
                'Autocorrelation plots',
                'Decomposition plots'
            ]
        }
        
        return analysis
    
    async def _generate_insights(self, 
                                analysis_result: Dict[str, Any], 
                                user_context: str) -> List[str]:
        """Generate business insights from analysis results"""
        insights = []
        
        # Data quality insights
        quality = analysis_result.get('data_quality', {})
        if quality.get('overall_score', 100) < 80:
            insights.append(f"Data quality score: {quality['overall_score']}/100. "
                           f"Consider addressing {quality['summary']['critical_issues']} critical issues.")
        
        # Distribution insights
        distributions = analysis_result.get('distributions', {})
        for col, dist in distributions.items():
            if dist.get('outliers_present', False):
                insights.append(f"Column '{col}' contains {dist['outliers_percentage']:.1f}% outliers "
                               f"which may need attention.")
            if not dist.get('is_normal_like', True):
                insights.append(f"Column '{col}' shows {dist['skewness_label'].lower()} distribution "
                               f"(skewness: {dist['skewness']:.2f}).")
        
        # Correlation insights
        correlations = analysis_result.get('correlations', {})
        strong_corrs = correlations.get('strong_correlations', [])
        if strong_corrs:
            top_corr = strong_corrs[0]
            insights.append(f"Strong correlation detected between {top_corr['pair'][0]} and "
                           f"{top_corr['pair'][1]} (r={top_corr['correlation']:.2f}).")
        
        # Categorical insights
        categorical = analysis_result.get('categorical_analysis', {})
        for col, cat_analysis in categorical.items():
            if cat_analysis.get('is_imbalanced', False):
                insights.append(f"Column '{col}' is imbalanced with "
                               f"{cat_analysis['dominance_percentage']:.1f}% dominance by one category.")
        
        # Add user context specific insights
        if user_context:
            insights.append(f"Based on your context '{user_context}', consider focusing on the identified patterns.")
        
        return insights[:10]  # Limit to 10 insights
    
    async def _generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Data quality recommendations
        quality = analysis_result.get('data_quality', {})
        for issue in quality.get('quality_issues', []):
            if issue['severity'] == 'high':
                recommendations.append(f"Address {issue['issue']}: {issue['description']}")
        
        # Outlier handling recommendations
        outliers = analysis_result.get('outliers', {})
        for col, outlier_info in outliers.get('column_wise_outliers', {}).items():
            if outlier_info['severity'] == 'high':
                recommendations.append(f"Investigate outliers in '{col}' "
                                      f"({outlier_info['percentage']:.1f}% of data)")
        
        # Missing data recommendations
        missing = analysis_result.get('missing_patterns', {})
        imp_recs = missing.get('imputation_recommendations', [])
        recommendations.extend(imp_recs)
        
        # Statistical recommendations
        distributions = analysis_result.get('distributions', {})
        for col, dist in distributions.items():
            for trans in dist.get('recommended_transformations', []):
                recommendations.append(f"Consider {trans} transformation for '{col}' "
                                      f"to normalize distribution")
        
        # General recommendations
        recommendations.extend([
            "Create visualizations to better understand data patterns",
            "Consider feature engineering based on correlations",
            "Validate analysis with domain experts when possible"
        ])
        
        return recommendations[:10]  # Limit to 10 recommendations
    
    def _create_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create executive summary"""
        quality = analysis_result.get('data_quality', {})
        distributions = analysis_result.get('distributions', {})
        correlations = analysis_result.get('correlations', {})
        categorical = analysis_result.get('categorical_analysis', {})
        
        # Count key findings
        critical_issues = quality.get('summary', {}).get('critical_issues', 0)
        outlier_columns = sum(
            1 for dist in distributions.values() 
            if dist.get('outliers_present', False)
        )
        strong_correlations = len(correlations.get('strong_correlations', []))
        imbalanced_categories = sum(
            1 for cat in categorical.values() 
            if cat.get('is_imbalanced', False)
        )
        
        summary = {
            'data_quality_score': quality.get('overall_score', 100),
            'key_findings': {
                'critical_data_issues': critical_issues,
                'columns_with_outliers': outlier_columns,
                'strong_correlations': strong_correlations,
                'imbalanced_categories': imbalanced_categories
            },
            'overall_assessment': self._generate_assessment(
                quality.get('overall_score', 100),
                critical_issues
            ),
            'next_steps': [
                'Review data quality issues' if critical_issues > 0 else None,
                'Investigate outliers' if outlier_columns > 0 else None,
                'Explore strong correlations' if strong_correlations > 0 else None,
                'Address class imbalance' if imbalanced_categories > 0 else None
            ]
        }
        
        return summary
    
    # Helper methods for various analyses
    def _suggest_transformations(self, skewness: float, is_normal: bool) -> List[str]:
        """Suggest transformations based on skewness"""
        transformations = []
        
        if not is_normal:
            if skewness > 1:
                transformations.extend(['log', 'square_root', 'box_cox'])
            elif skewness < -1:
                transformations.extend(['square', 'cube', 'exponential'])
            elif abs(skewness) > 0.5:
                transformations.append('yeo_johnson')
        
        return transformations
    
    def _find_correlated_groups(self, correlation_matrix: Dict[tuple, float]) -> List[List[str]]:
        """Find groups of highly correlated variables"""
        # Simple implementation - can be enhanced
        groups = []
        processed = set()
        
        for (col1, col2), corr in correlation_matrix.items():
            if abs(corr) > 0.8 and col1 not in processed and col2 not in processed:
                groups.append([col1, col2])
                processed.update([col1, col2])
        
        return groups
    
    def _generate_correlation_insights(self, correlations: List[Dict], numerical_cols: List[str]) -> List[str]:
        """Generate insights from correlation analysis"""
        insights = []
        
        if not correlations:
            return insights
        
        # Find strongest positive and negative correlations
        pos_corrs = [c for c in correlations if c.get('correlation', 0) > 0]
        neg_corrs = [c for c in correlations if c.get('correlation', 0) < 0]
        
        if pos_corrs:
            strongest_pos = max(pos_corrs, key=lambda x: x.get('correlation', 0))
            insights.append(f"Strongest positive correlation: {strongest_pos['pair'][0]} & "
                           f"{strongest_pos['pair'][1]} (r={strongest_pos['correlation']:.2f})")
        
        if neg_corrs:
            strongest_neg = min(neg_corrs, key=lambda x: x.get('correlation', 0))
            insights.append(f"Strongest negative correlation: {strongest_neg['pair'][0]} & "
                           f"{strongest_neg['pair'][1]} (r={strongest_neg['correlation']:.2f})")
        
        # Check for potential multicollinearity
        strong_pairs = [c for c in correlations if abs(c.get('correlation', 0)) > 0.9]
        if len(strong_pairs) > 3:
            insights.append(f"Found {len(strong_pairs)} highly correlated pairs - "
                           "potential multicollinearity concerns")
        
        return insights
    
    def _suggest_outlier_causes(self, column: str, stats: Dict[str, Any]) -> List[str]:
        """Suggest potential causes for outliers"""
        causes = []
        
        # Check data range
        min_val = stats.get('min')
        max_val = stats.get('max')
        if min_val is not None and max_val is not None:
            range_val = max_val - min_val
            if range_val > 1000:  # Arbitrary threshold
                causes.append('Wide data range may indicate measurement errors or valid extremes')
        
        # Check skewness
        skewness = stats.get('skewness', 0)
        if abs(skewness) > 1:
            causes.append(f"Skewed distribution (skewness: {skewness:.2f}) may naturally produce outliers")
        
        return causes
    
    def _suggest_outlier_handling(self, outlier_percentage: float) -> List[str]:
        """Suggest outlier handling strategies"""
        strategies = []
        
        if outlier_percentage < 1:
            strategies.append('Consider keeping outliers as they may represent valid edge cases')
        elif outlier_percentage < 5:
            strategies.extend([
                'Winsorize or cap extreme values',
                'Use robust statistical methods',
                'Investigate each outlier individually'
            ])
        else:
            strategies.extend([
                'Consider data transformation',
                'Investigate for data entry errors',
                'Use median instead of mean for central tendency',
                'Consider removing if proven to be errors'
            ])
        
        return strategies
    
    def _determine_missing_pattern(self, missing_percentage: float) -> str:
        """Determine pattern of missing data"""
        if missing_percentage == 0:
            return 'Complete data'
        elif missing_percentage < 5:
            return 'Missing completely at random (MCAR)'
        elif missing_percentage < 20:
            return 'Missing at random (MAR)'
        else:
            return 'Missing not at random (MNAR) - systematic missingness'
    
    def _check_systematic_missing(self, 
                                 numerical_missing: Dict[str, Dict],
                                 categorical_missing: Dict[str, Dict]) -> List[str]:
        """Check for systematic missing patterns"""
        issues = []
        
        # Check if missingness is concentrated in specific columns
        high_missing_cols = [
            col for col, info in {**numerical_missing, **categorical_missing}.items()
            if info.get('percentage', 0) > 30
        ]
        
        if high_missing_cols:
            issues.append(f"High missingness (>30%) in columns: {', '.join(high_missing_cols)}")
        
        # Check for pattern in missingness
        if len(numerical_missing) > 0 and len(categorical_missing) > 0:
            avg_num_missing = sum(info.get('percentage', 0) for info in numerical_missing.values()) / len(numerical_missing)
            avg_cat_missing = sum(info.get('percentage', 0) for info in categorical_missing.values()) / len(categorical_missing)
            
            if abs(avg_num_missing - avg_cat_missing) > 20:
                issues.append("Significant difference in missingness between numerical and categorical columns")
        
        return issues
    
    def _suggest_imputation_methods(self,
                                   numerical_missing: Dict[str, Dict],
                                   categorical_missing: Dict[str, Dict]) -> List[str]:
        """Suggest imputation methods for missing data"""
        recommendations = []
        
        # For numerical columns
        for col, info in numerical_missing.items():
            missing_pct = info.get('percentage', 0)
            if missing_pct < 5:
                recommendations.append(f"Consider mean/median imputation for '{col}' ({missing_pct:.1f}% missing)")
            elif missing_pct < 20:
                recommendations.append(f"Consider regression imputation or MICE for '{col}' ({missing_pct:.1f}% missing)")
            else:
                recommendations.append(f"Consider advanced imputation or exclusion for '{col}' ({missing_pct:.1f}% missing)")
        
        # For categorical columns
        for col, info in categorical_missing.items():
            missing_pct = info.get('percentage', 0)
            if missing_pct < 10:
                recommendations.append(f"Consider mode imputation or 'Unknown' category for '{col}' ({missing_pct:.1f}% missing)")
            else:
                recommendations.append(f"Consider advanced techniques or exclusion for '{col}' ({missing_pct:.1f}% missing)")
        
        return recommendations
    
    def _generate_assessment(self, quality_score: float, critical_issues: int) -> str:
        """Generate overall assessment"""
        if quality_score >= 90 and critical_issues == 0:
            return "Excellent data quality, ready for advanced analysis"
        elif quality_score >= 80:
            return "Good data quality, minor improvements recommended"
        elif quality_score >= 70:
            return "Fair data quality, some issues need attention"
        else:
            return "Poor data quality, significant improvements needed before analysis"
    
    def _suggest_visualizations(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest visualizations based on analysis"""
        visualizations = []
        
        # Distribution plots
        distributions = analysis_result.get('distributions', {})
        for col in distributions.keys():
            visualizations.append({
                'type': 'histogram',
                'columns': [col],
                'purpose': f'Distribution of {col}',
                'priority': 'high' if not distributions[col].get('is_normal_like', True) else 'medium'
            })
        
        # Correlation plots
        correlations = analysis_result.get('correlations', {}).get('strong_correlations', [])
        for corr in correlations[:3]:  # Top 3 correlations
            visualizations.append({
                'type': 'scatter',
                'columns': corr['pair'],
                'purpose': f'Relationship between {corr["pair"][0]} and {corr["pair"][1]}',
                'priority': 'high'
            })
        
        # Categorical plots
        categorical = analysis_result.get('categorical_analysis', {})
        for col in categorical.keys():
            if categorical[col].get('is_imbalanced', False):
                visualizations.append({
                    'type': 'bar',
                    'columns': [col],
                    'purpose': f'Category distribution for {col}',
                    'priority': 'medium'
                })
        
        # Missing data plot
        missing = analysis_result.get('missing_patterns', {})
        if missing.get('overall', {}).get('percentage', 0) > 0:
            visualizations.append({
                'type': 'heatmap',
                'columns': ['missing_pattern'],
                'purpose': 'Missing data pattern',
                'priority': 'medium'
            })
        
        return visualizations[:10]
    
    # Quick analysis methods
    async def _compute_summary_stats(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compute summary statistics for quick analysis"""
        basic = context.get('basic_statistics', {})
        numerical = context.get('numerical_statistics', {})
        categorical = context.get('categorical_statistics', {})
        
        return {
            'dataset_size': f"{context.get('data_shape', [0, 0])[0]:,} rows × {context.get('data_shape', [0, 0])[1]} columns",
            'missing_data': f"{basic.get('missing_percentage', 0):.1f}%",
            'duplicate_rows': f"{basic.get('duplicate_percentage', 0):.1f}%",
            'numerical_columns': len(context.get('numerical_columns', [])),
            'categorical_columns': len(context.get('categorical_columns', [])),
            'key_metrics': {
                'avg_missing_per_column': basic.get('missing_percentage', 0) / max(1, len(context.get('columns', []))),
                'data_completeness': 100 - basic.get('missing_percentage', 0)
            }
        }
    
    async def _get_key_correlations(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get key correlations for quick analysis"""
        correlations = context.get('correlations', [])
        return sorted(correlations, key=lambda x: abs(x.get('correlation', 0)), reverse=True)[:5]
    
    async def _identify_data_issues(self, context: Dict[str, Any]) -> List[str]:
        """Identify key data issues for quick analysis"""
        issues = []
        
        basic = context.get('basic_statistics', {})
        if basic.get('missing_percentage', 0) > 10:
            issues.append(f"High missing data: {basic.get('missing_percentage', 0):.1f}%")
        
        if basic.get('duplicate_percentage', 0) > 5:
            issues.append(f"High duplicate rows: {basic.get('duplicate_percentage', 0):.1f}%")
        
        numerical = context.get('numerical_statistics', {})
        for col, stats in numerical.items():
            if stats.get('missing_percentage', 0) > 50:
                issues.append(f"Column '{col}' has {stats.get('missing_percentage', 0):.1f}% missing values")
        
        return issues[:5]
    
    async def _generate_quick_insights(self, context: Dict[str, Any]) -> List[str]:
        """Generate quick insights"""
        insights = []
        
        # Size insight
        rows, cols = context.get('data_shape', [0, 0])
        insights.append(f"Dataset with {rows:,} rows and {cols} columns")
        
        # Missing data insight
        missing_pct = context.get('basic_statistics', {}).get('missing_percentage', 0)
        if missing_pct > 0:
            insights.append(f"Contains {missing_pct:.1f}% missing values")
        
        # Column type insight
        num_cols = len(context.get('numerical_columns', []))
        cat_cols = len(context.get('categorical_columns', []))
        insights.append(f"{num_cols} numerical and {cat_cols} categorical columns")
        
        # Correlation insight
        correlations = context.get('correlations', [])
        strong_corrs = [c for c in correlations if abs(c.get('correlation', 0)) > 0.7]
        if strong_corrs:
            insights.append(f"{len(strong_corrs)} strong correlations detected")
        
        return insights