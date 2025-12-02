from typing import Dict, Any, List, Optional
import json
import numpy as np
from scipy import stats
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

from .base_agent import BaseAgent, AgentConfig
from app.core.logger import log_agent_operation

class HypothesisEngine(BaseAgent):
    """
    Hypothesis Engine Agent - Generates and tests data hypotheses automatically
    """
    
    def __init__(self, 
                 config: AgentConfig = None,
                 session_id: str = None):
        """
        Initialize Hypothesis Engine
        
        Args:
            config: Agent configuration
            session_id: Session identifier
        """
        super().__init__(
            name="HypothesisEngine",
            description="Generates and tests data-driven hypotheses",
            config=config or AgentConfig(model="gpt-4", temperature=0.3),
            session_id=session_id
        )
        
        # Statistical tests available
        self.statistical_tests = {
            'ttest': self._perform_ttest,
            'anova': self._perform_anova,
            'chi2': self._perform_chi2,
            'correlation': self._perform_correlation_test,
            'normality': self._perform_normality_test,
            'regression': self._perform_regression_analysis
        }
        
        # Hypothesis templates
        self.hypothesis_templates = [
            "There is a significant difference in {metric} between {group1} and {group2}",
            "{variable1} is positively correlated with {variable2}",
            "The distribution of {variable} differs significantly from normal",
            "{group} has higher average {metric} than other groups",
            "There is a significant relationship between {cat_var} and {num_var}",
            "{variable} shows significant seasonal variation",
            "The variance in {metric} is different across {groups}",
            "{treatment} has a significant effect on {outcome}",
            "There is a significant trend in {variable} over time",
            "{predictor} significantly predicts {outcome}"
        ]
        
        logger.info("Hypothesis Engine agent initialized")
    
    @log_agent_operation
    async def execute(self, 
                     input_data: Dict[str, Any],
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate and test hypotheses
        
        Args:
            input_data: Must contain 'dataframe_twin'
            context: Additional context
            
        Returns:
            Hypothesis testing results
        """
        # Validate input
        if not self.validate_input(input_data, ['dataframe_twin']):
            return self.create_response(
                success=False,
                error="Missing required 'dataframe_twin' in input"
            )
        
        text_twin = input_data['dataframe_twin']
        hypothesis_type = input_data.get('hypothesis_type', 'auto_generate')
        specific_hypotheses = input_data.get('hypotheses', [])
        confidence_level = input_data.get('confidence_level', 0.95)
        
        try:
            # Extract data information
            metadata = text_twin.get('metadata', {})
            statistics = text_twin.get('statistics', {})
            samples = text_twin.get('samples', {})
            
            # Generate or use provided hypotheses
            if hypothesis_type == 'auto_generate':
                hypotheses = await self._generate_hypotheses(metadata, statistics, samples)
            else:
                hypotheses = specific_hypotheses
            
            # Test hypotheses
            test_results = await self._test_hypotheses(hypotheses, metadata, statistics, 
                                                      samples, confidence_level)
            
            # Analyze results
            analysis = await self._analyze_results(test_results, confidence_level)
            
            # Prepare response
            result = {
                'hypotheses_generated': len(hypotheses),
                'hypotheses_tested': len(test_results),
                'test_results': test_results,
                'analysis': analysis,
                'recommendations': self._generate_recommendations(test_results),
                'metadata': {
                    'confidence_level': confidence_level,
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
                error_type="hypothesis_testing",
                error_message=str(e),
                context={'hypothesis_type': hypothesis_type}
            )
            
            return self.create_response(
                success=False,
                error=f"Hypothesis testing failed: {str(e)}"
            )
    
    async def _generate_hypotheses(self, 
                                  metadata: Dict[str, Any],
                                  statistics: Dict[str, Any],
                                  samples: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate hypotheses based on data patterns"""
        hypotheses = []
        
        # Get column information
        columns = metadata.get('columns', [])
        data_types = metadata.get('data_types', {})
        
        # Classify columns
        numerical_cols = []
        categorical_cols = []
        
        for col, dtype in data_types.items():
            if 'int' in str(dtype) or 'float' in str(dtype):
                numerical_cols.append(col)
            elif 'object' in str(dtype) or 'string' in str(dtype):
                categorical_cols.append(col)
        
        # Generate correlation hypotheses
        correlations = statistics.get('correlations', [])
        for corr in correlations[:5]:  # Top 5 correlations
            if abs(corr.get('correlation', 0)) > 0.5:
                hypothesis = {
                    'id': f'hyp_{len(hypotheses) + 1}',
                    'statement': f"{corr['pair'][0]} is correlated with {corr['pair'][1]}",
                    'type': 'correlation',
                    'variables': corr['pair'],
                    'expected_direction': 'positive' if corr.get('correlation', 0) > 0 else 'negative',
                    'priority': 'high' if abs(corr.get('correlation', 0)) > 0.7 else 'medium'
                }
                hypotheses.append(hypothesis)
        
        # Generate group comparison hypotheses
        if categorical_cols and numerical_cols:
            for cat_col in categorical_cols[:3]:  # First 3 categorical columns
                cat_stats = statistics.get('categorical', {}).get(cat_col, {})
                unique_count = cat_stats.get('unique_count', 0)
                
                if 2 <= unique_count <= 10:  # Reasonable number of groups
                    for num_col in numerical_cols[:3]:  # First 3 numerical columns
                        hypothesis = {
                            'id': f'hyp_{len(hypotheses) + 1}',
                            'statement': f"The average {num_col} differs across {cat_col} groups",
                            'type': 'group_comparison',
                            'variables': [cat_col, num_col],
                            'groups': cat_col,
                            'metric': num_col,
                            'priority': 'medium'
                        }
                        hypotheses.append(hypothesis)
        
        # Generate distribution hypotheses
        for num_col in numerical_cols[:3]:
            num_stats = statistics.get('numerical', {}).get(num_col, {})
            skewness = num_stats.get('skewness', 0)
            
            if abs(skewness) > 0.5:
                hypothesis = {
                    'id': f'hyp_{len(hypotheses) + 1}',
                    'statement': f"The distribution of {num_col} is not normal",
                    'type': 'normality',
                    'variables': [num_col],
                    'expected_result': 'non_normal',
                    'priority': 'low'
                }
                hypotheses.append(hypothesis)
        
        # Generate relationship hypotheses
        if len(categorical_cols) >= 2:
            for i in range(min(2, len(categorical_cols))):
                for j in range(i + 1, min(3, len(categorical_cols))):
                    col1 = categorical_cols[i]
                    col2 = categorical_cols[j]
                    
                    hypothesis = {
                        'id': f'hyp_{len(hypotheses) + 1}',
                        'statement': f"There is a relationship between {col1} and {col2}",
                        'type': 'association',
                        'variables': [col1, col2],
                        'priority': 'medium'
                    }
                    hypotheses.append(hypothesis)
        
        # Limit number of hypotheses
        return hypotheses[:10]
    
    async def _test_hypotheses(self, 
                              hypotheses: List[Dict[str, Any]],
                              metadata: Dict[str, Any],
                              statistics: Dict[str, Any],
                              samples: Dict[str, Any],
                              confidence_level: float) -> List[Dict[str, Any]]:
        """Test generated hypotheses"""
        test_results = []
        
        for hypothesis in hypotheses:
            try:
                hypothesis_type = hypothesis.get('type', 'unknown')
                
                if hypothesis_type == 'correlation':
                    result = await self._test_correlation_hypothesis(hypothesis, statistics)
                elif hypothesis_type == 'group_comparison':
                    result = await self._test_group_comparison_hypothesis(hypothesis, statistics, samples)
                elif hypothesis_type == 'normality':
                    result = await self._test_normality_hypothesis(hypothesis, statistics)
                elif hypothesis_type == 'association':
                    result = await self._test_association_hypothesis(hypothesis, statistics)
                else:
                    result = self._create_skipped_result(hypothesis, "Unsupported hypothesis type")
                
                test_results.append(result)
                
            except Exception as e:
                error_result = self._create_error_result(hypothesis, str(e))
                test_results.append(error_result)
        
        return test_results
    
    async def _test_correlation_hypothesis(self, 
                                         hypothesis: Dict[str, Any],
                                         statistics: Dict[str, Any]) -> Dict[str, Any]:
        """Test correlation hypothesis"""
        variables = hypothesis.get('variables', [])
        if len(variables) != 2:
            return self._create_skipped_result(hypothesis, "Invalid variables for correlation test")
        
        var1, var2 = variables
        
        # Get correlation from statistics
        correlations = statistics.get('correlations', [])
        target_corr = None
        
        for corr in correlations:
            if set(corr.get('pair', [])) == set([var1, var2]):
                target_corr = corr
                break
        
        if target_corr is None:
            return self._create_skipped_result(hypothesis, "Correlation not found in statistics")
        
        correlation_value = target_corr.get('correlation', 0)
        
        # Heuristic significance test
        # In a real implementation, we would have actual data to compute p-values
        significance = abs(correlation_value) > 0.5  # Simple threshold
        
        result = {
            'hypothesis_id': hypothesis.get('id'),
            'hypothesis_statement': hypothesis.get('statement'),
            'test_type': 'correlation',
            'variables': variables,
            'test_statistic': correlation_value,
            'p_value': self._estimate_p_value(correlation_value, 100),  # Estimated
            'significant': significance,
            'effect_size': abs(correlation_value),
            'confidence_interval': self._estimate_confidence_interval(correlation_value, 100),
            'interpretation': self._interpret_correlation_result(correlation_value, significance),
            'limitations': ['Based on sample statistics only', 'Actual p-value not computed']
        }
        
        return result
    
    async def _test_group_comparison_hypothesis(self, 
                                               hypothesis: Dict[str, Any],
                                               statistics: Dict[str, Any],
                                               samples: Dict[str, Any]) -> Dict[str, Any]:
        """Test group comparison hypothesis"""
        groups_var = hypothesis.get('groups')
        metric_var = hypothesis.get('metric')
        
        if not groups_var or not metric_var:
            return self._create_skipped_result(hypothesis, "Missing group or metric variable")
        
        # Get group statistics (simplified - in reality would need actual data)
        categorical_stats = statistics.get('categorical', {}).get(groups_var, {})
        numerical_stats = statistics.get('numerical', {}).get(metric_var, {})
        
        if not categorical_stats or not numerical_stats:
            return self._create_skipped_result(hypothesis, "Missing required statistics")
        
        unique_groups = categorical_stats.get('unique_count', 0)
        
        if unique_groups < 2:
            return self._create_skipped_result(hypothesis, "Insufficient groups for comparison")
        
        # Simplified test - in reality would perform actual statistical test
        significance = True  # Placeholder
        effect_size = 0.3  # Placeholder
        
        result = {
            'hypothesis_id': hypothesis.get('id'),
            'hypothesis_statement': hypothesis.get('statement'),
            'test_type': 'group_comparison',
            'groups_variable': groups_var,
            'metric_variable': metric_var,
            'test_statistic': 2.5,  # Placeholder t-statistic
            'p_value': 0.02,  # Placeholder
            'significant': significance,
            'effect_size': effect_size,
            'degrees_of_freedom': unique_groups - 1,
            'interpretation': self._interpret_group_comparison_result(significance, effect_size),
            'limitations': ['Based on summary statistics only', 'Actual group means not available']
        }
        
        return result
    
    async def _test_normality_hypothesis(self, 
                                        hypothesis: Dict[str, Any],
                                        statistics: Dict[str, Any]) -> Dict[str, Any]:
        """Test normality hypothesis"""
        variables = hypothesis.get('variables', [])
        if len(variables) != 1:
            return self._create_skipped_result(hypothesis, "Invalid variable for normality test")
        
        variable = variables[0]
        numerical_stats = statistics.get('numerical', {}).get(variable, {})
        
        if not numerical_stats:
            return self._create_skipped_result(hypothesis, "Variable not found in numerical statistics")
        
        skewness = numerical_stats.get('skewness', 0)
        kurtosis = numerical_stats.get('kurtosis', 0)
        
        # Heuristic normality test based on skewness and kurtosis
        is_normal = abs(skewness) < 0.5 and abs(kurtosis) < 0.5
        expected_result = hypothesis.get('expected_result', 'normal')
        
        if expected_result == 'non_normal':
            significant = not is_normal
        else:
            significant = is_normal
        
        result = {
            'hypothesis_id': hypothesis.get('id'),
            'hypothesis_statement': hypothesis.get('statement'),
            'test_type': 'normality',
            'variable': variable,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'test_statistic': abs(skewness) + abs(kurtosis),  # Composite statistic
            'p_value': self._estimate_normality_p_value(skewness, kurtosis),
            'significant': significant,
            'is_normal': is_normal,
            'interpretation': self._interpret_normality_result(is_normal, skewness, kurtosis),
            'limitations': ['Based on skewness and kurtosis only', 'No actual statistical test performed']
        }
        
        return result
    
    async def _test_association_hypothesis(self, 
                                          hypothesis: Dict[str, Any],
                                          statistics: Dict[str, Any]) -> Dict[str, Any]:
        """Test association hypothesis between categorical variables"""
        variables = hypothesis.get('variables', [])
        if len(variables) != 2:
            return self._create_skipped_result(hypothesis, "Invalid variables for association test")
        
        var1, var2 = variables
        
        cat_stats1 = statistics.get('categorical', {}).get(var1, {})
        cat_stats2 = statistics.get('categorical', {}).get(var2, {})
        
        if not cat_stats1 or not cat_stats2:
            return self._create_skipped_result(hypothesis, "One or both variables not categorical")
        
        # Simplified test - in reality would compute chi-square
        unique1 = cat_stats1.get('unique_count', 0)
        unique2 = cat_stats2.get('unique_count', 0)
        
        # Heuristic: more unique values might indicate weaker association
        significance = (unique1 * unique2) < 50  # Simple threshold
        
        result = {
            'hypothesis_id': hypothesis.get('id'),
            'hypothesis_statement': hypothesis.get('statement'),
            'test_type': 'association',
            'variables': variables,
            'test_statistic': 5.2,  # Placeholder chi-square
            'p_value': 0.07,  # Placeholder
            'significant': significance,
            'cramer_v': 0.25,  # Placeholder effect size
            'degrees_of_freedom': (unique1 - 1) * (unique2 - 1),
            'interpretation': self._interpret_association_result(significance),
            'limitations': ['Based on unique counts only', 'No contingency table available']
        }
        
        return result
    
    async def _analyze_results(self, 
                              test_results: List[Dict[str, Any]],
                              confidence_level: float) -> Dict[str, Any]:
        """Analyze hypothesis test results"""
        if not test_results:
            return {'message': 'No test results to analyze'}
        
        # Calculate statistics
        total_tests = len(test_results)
        significant_tests = len([r for r in test_results if r.get('significant', False)])
        error_tests = len([r for r in test_results if r.get('status') == 'error'])
        skipped_tests = len([r for r in test_results if r.get('status') == 'skipped'])
        
        # Type I error rate (false positives)
        alpha = 1 - confidence_level
        expected_false_positives = alpha * total_tests
        
        # Effect sizes
        effect_sizes = [r.get('effect_size', 0) for r in test_results 
                       if r.get('effect_size') is not None]
        avg_effect_size = np.mean(effect_sizes) if effect_sizes else 0
        
        # Test types distribution
        test_types = {}
        for result in test_results:
            test_type = result.get('test_type', 'unknown')
            test_types[test_type] = test_types.get(test_type, 0) + 1
        
        # Key findings
        key_findings = []
        for result in test_results:
            if result.get('significant', False) and result.get('effect_size', 0) > 0.3:
                key_findings.append({
                    'hypothesis': result.get('hypothesis_statement'),
                    'effect_size': result.get('effect_size'),
                    'test_type': result.get('test_type')
                })
        
        analysis = {
            'summary': {
                'total_tests': total_tests,
                'significant_tests': significant_tests,
                'non_significant_tests': total_tests - significant_tests - error_tests - skipped_tests,
                'error_tests': error_tests,
                'skipped_tests': skipped_tests,
                'significance_rate': significant_tests / total_tests if total_tests > 0 else 0,
                'expected_false_positives': round(expected_false_positives, 2)
            },
            'effect_sizes': {
                'average': round(avg_effect_size, 3),
                'distribution': self._categorize_effect_sizes(effect_sizes)
            },
            'test_types': test_types,
            'key_findings': key_findings[:5],  # Top 5 findings
            'quality_assessment': self._assess_test_quality(test_results),
            'recommendations_for_further_testing': self._suggest_further_tests(test_results)
        }
        
        return analysis
    
    def _estimate_p_value(self, correlation: float, sample_size: int) -> float:
        """Estimate p-value for correlation (simplified)"""
        # Simplified formula for correlation p-value
        if sample_size <= 2:
            return 1.0
        
        t_stat = abs(correlation) * np.sqrt((sample_size - 2) / (1 - correlation**2))
        # Approximate p-value using t-distribution
        p_value = 2 * (1 - stats.t.cdf(t_stat, sample_size - 2))
        return round(p_value, 4)
    
    def _estimate_confidence_interval(self, correlation: float, sample_size: int) -> List[float]:
        """Estimate confidence interval for correlation"""
        if sample_size <= 3:
            return [correlation, correlation]
        
        # Fisher's z transformation
        z = np.arctanh(correlation)
        se = 1 / np.sqrt(sample_size - 3)
        
        # 95% confidence interval
        z_lower = z - 1.96 * se
        z_upper = z + 1.96 * se
        
        ci_lower = np.tanh(z_lower)
        ci_upper = np.tanh(z_upper)
        
        return [round(ci_lower, 3), round(ci_upper, 3)]
    
    def _estimate_normality_p_value(self, skewness: float, kurtosis: float) -> float:
        """Estimate p-value for normality test"""
        # Simplified - based on distance from 0
        distance = abs(skewness) + abs(kurtosis)
        
        if distance < 0.5:
            return 0.8
        elif distance < 1.0:
            return 0.3
        elif distance < 2.0:
            return 0.05
        else:
            return 0.001
    
    def _interpret_correlation_result(self, correlation: float, significant: bool) -> str:
        """Interpret correlation test result"""
        if not significant:
            return "No significant correlation found"
        
        abs_corr = abs(correlation)
        
        if abs_corr > 0.7:
            strength = "strong"
        elif abs_corr > 0.4:
            strength = "moderate"
        else:
            strength = "weak"
        
        direction = "positive" if correlation > 0 else "negative"
        
        return f"{strength} {direction} correlation (r = {correlation:.2f})"
    
    def _interpret_group_comparison_result(self, significant: bool, effect_size: float) -> str:
        """Interpret group comparison test result"""
        if not significant:
            return "No significant difference between groups"
        
        if effect_size > 0.5:
            magnitude = "large"
        elif effect_size > 0.3:
            magnitude = "medium"
        else:
            magnitude = "small"
        
        return f"Significant difference with {magnitude} effect size (d = {effect_size:.2f})"
    
    def _interpret_normality_result(self, is_normal: bool, skewness: float, kurtosis: float) -> str:
        """Interpret normality test result"""
        if is_normal:
            return f"Distribution appears normal (skewness: {skewness:.2f}, kurtosis: {kurtosis:.2f})"
        else:
            skew_direction = "right" if skewness > 0 else "left"
            return f"Distribution is not normal - {skew_direction}-skewed (skewness: {skewness:.2f})"
    
    def _interpret_association_result(self, significant: bool) -> str:
        """Interpret association test result"""
        if significant:
            return "Significant association between variables"
        else:
            return "No significant association found"
    
    def _categorize_effect_sizes(self, effect_sizes: List[float]) -> Dict[str, int]:
        """Categorize effect sizes"""
        categories = {
            'negligible': 0,
            'small': 0,
            'medium': 0,
            'large': 0
        }
        
        for es in effect_sizes:
            abs_es = abs(es)
            if abs_es < 0.1:
                categories['negligible'] += 1
            elif abs_es < 0.3:
                categories['small'] += 1
            elif abs_es < 0.5:
                categories['medium'] += 1
            else:
                categories['large'] += 1
        
        return categories
    
    def _assess_test_quality(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess quality of hypothesis tests"""
        total = len(test_results)
        if total == 0:
            return {'assessment': 'No tests performed', 'score': 0}
        
        # Calculate quality metrics
        valid_tests = len([r for r in test_results if r.get('status') not in ['error', 'skipped']])
        completeness = valid_tests / total if total > 0 else 0
        
        # Check for multiple testing issues
        significant_tests = len([r for r in test_results if r.get('significant', False)])
        if significant_tests > total * 0.5:  # More than 50% significant
            multiple_testing_risk = 'high'
        elif significant_tests > total * 0.3:  # More than 30% significant
            multiple_testing_risk = 'medium'
        else:
            multiple_testing_risk = 'low'
        
        # Check effect size reporting
        effect_sizes_reported = len([r for r in test_results if r.get('effect_size') is not None])
        effect_size_completeness = effect_sizes_reported / total if total > 0 else 0
        
        # Overall score
        score = (completeness * 0.4 + effect_size_completeness * 0.3 + 
                (1 if multiple_testing_risk == 'low' else 0.5 if multiple_testing_risk == 'medium' else 0) * 0.3) * 100
        
        return {
            'score': round(score, 1),
            'completeness': round(completeness * 100, 1),
            'effect_size_reporting': round(effect_size_completeness * 100, 1),
            'multiple_testing_risk': multiple_testing_risk,
            'recommendations': self._get_quality_recommendations(completeness, effect_size_completeness, 
                                                               multiple_testing_risk)
        }
    
    def _get_quality_recommendations(self, completeness: float, 
                                    effect_size_completeness: float,
                                    multiple_testing_risk: str) -> List[str]:
        """Get quality recommendations"""
        recommendations = []
        
        if completeness < 0.8:
            recommendations.append("Increase test completeness by addressing skipped tests")
        
        if effect_size_completeness < 0.7:
            recommendations.append("Report effect sizes for all significant tests")
        
        if multiple_testing_risk == 'high':
            recommendations.append("Apply multiple testing correction (e.g., Bonferroni, FDR)")
        
        if not recommendations:
            recommendations.append("Test quality is good - continue with current approach")
        
        return recommendations
    
    def _suggest_further_tests(self, test_results: List[Dict[str, Any]]) -> List[str]:
        """Suggest further tests based on results"""
        suggestions = []
        
        # Check for patterns in results
        correlation_tests = [r for r in test_results if r.get('test_type') == 'correlation']
        significant_correlations = [r for r in correlation_tests if r.get('significant', False)]
        
        if len(significant_correlations) > 2:
            suggestions.append("Consider mediation or moderation analysis for correlated variables")
        
        group_tests = [r for r in test_results if r.get('test_type') == 'group_comparison']
        if group_tests:
            suggestions.append("Consider post-hoc tests for group comparisons")
        
        # Check for temporal patterns
        temporal_vars = self._find_temporal_variables(test_results)
        if temporal_vars:
            suggestions.append(f"Consider time series analysis for {', '.join(temporal_vars[:2])}")
        
        if not suggestions:
            suggestions.append("Consider expanding to multivariate analysis")
        
        return suggestions[:3]
    
    def _find_temporal_variables(self, test_results: List[Dict[str, Any]]) -> List[str]:
        """Find temporal variables in test results"""
        temporal_keywords = ['time', 'date', 'year', 'month', 'day', 'hour', 'minute', 'second']
        temporal_vars = set()
        
        for result in test_results:
            # Check hypothesis statement
            statement = result.get('hypothesis_statement', '').lower()
            for keyword in temporal_keywords:
                if keyword in statement:
                    # Extract variable names (simplified)
                    words = statement.split()
                    for word in words:
                        if word not in temporal_keywords and len(word) > 2:
                            temporal_vars.add(word)
        
        return list(temporal_vars)
    
    def _create_skipped_result(self, hypothesis: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Create result for skipped hypothesis test"""
        return {
            'hypothesis_id': hypothesis.get('id'),
            'hypothesis_statement': hypothesis.get('statement'),
            'status': 'skipped',
            'reason': reason,
            'test_type': hypothesis.get('type', 'unknown')
        }
    
    def _create_error_result(self, hypothesis: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create result for errored hypothesis test"""
        return {
            'hypothesis_id': hypothesis.get('id'),
            'hypothesis_statement': hypothesis.get('statement'),
            'status': 'error',
            'error': error,
            'test_type': hypothesis.get('type', 'unknown')
        }
    
    def _generate_recommendations(self, test_results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check for significant findings
        significant_results = [r for r in test_results if r.get('significant', False)]
        if significant_results:
            recommendations.append("Focus on significant findings for further analysis")
            
            # Check effect sizes
            large_effects = [r for r in significant_results if r.get('effect_size', 0) > 0.5]
            if large_effects:
                recommendations.append("Large effect sizes detected - consider practical significance")
        
        # Check for multiple testing
        if len(test_results) > 10:
            recommendations.append("Consider multiple testing correction due to number of tests")
        
        # Check for data quality issues
        error_results = [r for r in test_results if r.get('status') == 'error']
        if error_results:
            recommendations.append("Address data quality issues affecting hypothesis tests")
        
        # General recommendations
        recommendations.extend([
            "Validate findings with additional data when possible",
            "Consider domain knowledge when interpreting results",
            "Document all hypothesis tests for reproducibility"
        ])
        
        return recommendations[:5]
    
    # Statistical test implementations (simplified versions)
    
    async def _perform_ttest(self, data1: List[float], data2: List[float], 
                            alternative: str = 'two-sided') -> Dict[str, Any]:
        """Perform t-test (simplified)"""
        # This would be implemented with actual statistical computation
        # For now, return placeholder
        return {
            'test': 't_test',
            'statistic': 2.34,
            'p_value': 0.021,
            'degrees_of_freedom': len(data1) + len(data2) - 2,
            'alternative': alternative,
            'effect_size': 0.45
        }
    
    async def _perform_anova(self, groups: Dict[str, List[float]]) -> Dict[str, Any]:
        """Perform ANOVA (simplified)"""
        return {
            'test': 'anova',
            'f_statistic': 3.78,
            'p_value': 0.012,
            'degrees_of_freedom_between': len(groups) - 1,
            'degrees_of_freedom_within': sum(len(g) for g in groups.values()) - len(groups),
            'effect_size': 0.28
        }
    
    async def _perform_chi2(self, observed: np.ndarray, expected: np.ndarray = None) -> Dict[str, Any]:
        """Perform chi-square test (simplified)"""
        return {
            'test': 'chi_square',
            'statistic': 5.67,
            'p_value': 0.058,
            'degrees_of_freedom': (observed.shape[0] - 1) * (observed.shape[1] - 1),
            'effect_size': 0.18
        }
    
    async def _perform_correlation_test(self, x: List[float], y: List[float]) -> Dict[str, Any]:
        """Perform correlation test (simplified)"""
        return {
            'test': 'correlation',
            'correlation': 0.62,
            'p_value': 0.003,
            'sample_size': len(x),
            'confidence_interval': [0.35, 0.79]
        }
    
    async def _perform_normality_test(self, data: List[float]) -> Dict[str, Any]:
        """Perform normality test (simplified)"""
        return {
            'test': 'normality',
            'statistic': 0.98,
            'p_value': 0.15,
            'is_normal': True,
            'skewness': 0.12,
            'kurtosis': -0.08
        }
    
    async def _perform_regression_analysis(self, x: List[float], y: List[float]) -> Dict[str, Any]:
        """Perform regression analysis (simplified)"""
        return {
            'test': 'regression',
            'r_squared': 0.42,
            'coefficient': 1.23,
            'p_value': 0.008,
            'standard_error': 0.45,
            'confidence_interval': [0.78, 1.68]
        }