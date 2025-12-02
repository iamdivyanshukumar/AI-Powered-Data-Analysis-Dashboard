import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import hashlib

logger = logging.getLogger(__name__)

class TextTwinGenerator:
    """
    Generates text twin representations of dataframes for efficient
    context passing to LLMs without exposing full data.
    """
    
    def __init__(self, max_samples: int = 50, max_chars: int = 10000):
        """
        Initialize TextTwinGenerator
        
        Args:
            max_samples: Maximum number of samples to include
            max_chars: Maximum characters in twin representation
        """
        self.max_samples = max_samples
        self.max_chars = max_chars
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
    
    def generate_twin(self, df: pd.DataFrame, 
                     include_samples: bool = True,
                     include_stats: bool = True,
                     include_insights: bool = True) -> Dict[str, Any]:
        """
        Generate text twin representation of dataframe
        
        Args:
            df: DataFrame to create twin for
            include_samples: Whether to include data samples
            include_stats: Whether to include statistics
            include_insights: Whether to include auto-generated insights
            
        Returns:
            Text twin dictionary
        """
        try:
            twin = {
                'metadata': self._get_metadata(df),
                'fingerprint': self._generate_fingerprint(df)
            }
            
            if include_samples:
                twin['samples'] = self._get_representative_samples(df)
            
            if include_stats:
                twin['statistics'] = self._get_comprehensive_statistics(df)
            
            if include_insights:
                twin['insights'] = self._generate_auto_insights(df)
            
            # Add schema information
            twin['schema'] = self._get_schema(df)
            
            # Add quality metrics
            twin['quality'] = self._get_quality_metrics(df)
            
            # Add semantic summary
            twin['semantic_summary'] = self._generate_semantic_summary(df)
            
            # Ensure size limits
            twin = self._enforce_size_limits(twin)
            
            logger.info(f"Generated text twin for {df.shape} dataframe")
            return twin
            
        except Exception as e:
            logger.error(f"Error generating text twin: {str(e)}")
            return {
                'metadata': {'error': str(e)},
                'fingerprint': 'error'
            }
    
    def _get_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get basic metadata about the dataframe"""
        return {
            'shape': list(df.shape),
            'columns': list(df.columns),
            'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'memory_usage_mb': round(df.memory_usage(deep=True).sum() / 1024**2, 2),
            'missing_values': int(df.isnull().sum().sum()),
            'duplicate_rows': int(df.duplicated().sum()),
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_fingerprint(self, df: pd.DataFrame) -> str:
        """
        Generate fingerprint for dataframe (deterministic hash)
        
        Args:
            df: DataFrame
            
        Returns:
            Fingerprint string
        """
        # Use column names, dtypes, and shape for fingerprint
        fingerprint_data = {
            'columns': sorted(df.columns.tolist()),
            'dtypes': {col: str(dtype) for col, dtype in sorted(df.dtypes.items())},
            'shape': list(df.shape),
            'sample_hash': self._get_sample_hash(df)
        }
        
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
    
    def _get_sample_hash(self, df: pd.DataFrame) -> str:
        """Get hash of sample data"""
        if len(df) == 0:
            return "empty"
        
        # Sample first and last rows
        sample_indices = list(range(min(3, len(df)))) + \
                        list(range(max(0, len(df)-3), len(df)))
        sample = df.iloc[sample_indices].fillna('').astype(str).to_string()
        return hashlib.sha256(sample.encode()).hexdigest()[:8]
    
    def _get_representative_samples(self, df: pd.DataFrame) -> Dict[str, List]:
        """
        Get representative samples from dataframe
        
        Args:
            df: DataFrame
            
        Returns:
            Dictionary with different sample types
        """
        samples = {
            'head': [],
            'tail': [],
            'random': [],
            'statistical': []
        }
        
        if len(df) == 0:
            return samples
        
        # Head samples (first rows)
        head_count = min(5, len(df))
        for i in range(head_count):
            samples['head'].append(self._row_to_dict(df.iloc[i]))
        
        # Tail samples (last rows)
        tail_count = min(5, len(df))
        for i in range(tail_count):
            samples['tail'].append(self._row_to_dict(df.iloc[-i-1]))
        
        # Random samples
        random_count = min(10, len(df))
        if len(df) > random_count:
            random_indices = np.random.choice(len(df), random_count, replace=False)
            for idx in random_indices:
                samples['random'].append(self._row_to_dict(df.iloc[idx]))
        
        # Statistical representatives (min, max, median for numeric columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
            if df[col].notna().any():
                # Min
                min_idx = df[col].idxmin()
                if pd.notna(min_idx):
                    samples['statistical'].append({
                        'type': f'min_{col}',
                        'row': self._row_to_dict(df.loc[min_idx]),
                        'value': float(df.loc[min_idx, col])
                    })
                
                # Max
                max_idx = df[col].idxmax()
                if pd.notna(max_idx):
                    samples['statistical'].append({
                        'type': f'max_{col}',
                        'row': self._row_to_dict(df.loc[max_idx]),
                        'value': float(df.loc[max_idx, col])
                    })
                
                # Median (closest to median)
                median_val = df[col].median()
                closest_idx = (df[col] - median_val).abs().idxmin()
                if pd.notna(closest_idx):
                    samples['statistical'].append({
                        'type': f'median_{col}',
                        'row': self._row_to_dict(df.loc[closest_idx]),
                        'value': float(df.loc[closest_idx, col])
                    })
        
        return samples
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert row to JSON-serializable dictionary"""
        row_dict = {}
        for col, val in row.items():
            if pd.isna(val):
                row_dict[col] = None
            elif isinstance(val, (np.integer, np.int64)):
                row_dict[col] = int(val)
            elif isinstance(val, (np.floating, np.float64)):
                row_dict[col] = float(val)
            elif isinstance(val, pd.Timestamp):
                row_dict[col] = val.isoformat()
            else:
                row_dict[col] = str(val)
        return row_dict
    
    def _get_comprehensive_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get comprehensive statistics for dataframe"""
        stats = {
            'basic': {},
            'numerical': {},
            'categorical': {},
            'correlations': {}
        }
        
        # Basic stats
        stats['basic'] = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'missing_values': int(df.isnull().sum().sum()),
            'missing_percentage': round((df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100, 2),
            'duplicate_rows': int(df.duplicated().sum()),
            'duplicate_percentage': round((df.duplicated().sum() / len(df)) * 100, 2)
        }
        
        # Numerical column statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            col_stats = {
                'count': int(df[col].count()),
                'mean': float(df[col].mean()) if df[col].count() > 0 else None,
                'std': float(df[col].std()) if df[col].count() > 0 else None,
                'min': float(df[col].min()) if df[col].count() > 0 else None,
                'max': float(df[col].max()) if df[col].count() > 0 else None,
                'median': float(df[col].median()) if df[col].count() > 0 else None,
                'q1': float(df[col].quantile(0.25)) if df[col].count() > 0 else None,
                'q3': float(df[col].quantile(0.75)) if df[col].count() > 0 else None,
                'skewness': float(df[col].skew()) if df[col].count() > 0 else None,
                'kurtosis': float(df[col].kurtosis()) if df[col].count() > 0 else None,
                'missing': int(df[col].isnull().sum()),
                'missing_percentage': round((df[col].isnull().sum() / len(df)) * 100, 2)
            }
            stats['numerical'][col] = col_stats
        
        # Categorical column statistics
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            value_counts = df[col].value_counts()
            top_values = value_counts.head(5).to_dict()
            
            col_stats = {
                'unique_count': int(df[col].nunique()),
                'missing': int(df[col].isnull().sum()),
                'missing_percentage': round((df[col].isnull().sum() / len(df)) * 100, 2),
                'top_values': {str(k): int(v) for k, v in top_values.items()},
                'entropy': self._calculate_entropy(value_counts)
            }
            stats['categorical'][col] = col_stats
        
        # Correlation matrix (for numerical columns)
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            # Get top correlations
            correlations = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    col1 = corr_matrix.columns[i]
                    col2 = corr_matrix.columns[j]
                    corr = corr_matrix.iloc[i, j]
                    if abs(corr) > 0.5:  # Only strong correlations
                        correlations.append({
                            'pair': [col1, col2],
                            'correlation': round(float(corr), 3),
                            'strength': 'strong' if abs(corr) > 0.7 else 'moderate'
                        })
            
            # Sort by absolute correlation
            correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
            stats['correlations'] = correlations[:10]  # Top 10 correlations
        
        return stats
    
    def _calculate_entropy(self, value_counts):
        """Calculate entropy of a distribution"""
        probabilities = value_counts / value_counts.sum()
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
        return round(float(entropy), 3)
    
    def _generate_auto_insights(self, df: pd.DataFrame) -> List[str]:
        """Generate automatic insights from data"""
        insights = []
        
        # Check for missing data
        missing_total = df.isnull().sum().sum()
        if missing_total > 0:
            missing_pct = round((missing_total / (len(df) * len(df.columns))) * 100, 1)
            insights.append(f"Dataset has {missing_pct}% missing values")
        
        # Check for duplicates
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            duplicate_pct = round((duplicate_count / len(df)) * 100, 1)
            insights.append(f"Found {duplicate_pct}% duplicate rows")
        
        # Check numerical column distributions
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols[:3]:  # Check first 3 numeric columns
            if df[col].notna().any():
                skewness = df[col].skew()
                if abs(skewness) > 1:
                    direction = "right" if skewness > 0 else "left"
                    insights.append(f"Column '{col}' is heavily skewed ({direction})")
                
                # Check for outliers using IQR
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers = df[(df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))]
                if len(outliers) > 0:
                    outlier_pct = round((len(outliers) / len(df)) * 100, 1)
                    insights.append(f"Column '{col}' has {outlier_pct}% outliers")
        
        # Check categorical column cardinality
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols[:3]:  # Check first 3 categorical columns
            unique_count = df[col].nunique()
            if unique_count > 50:
                insights.append(f"Column '{col}' has high cardinality ({unique_count} unique values)")
            elif unique_count < 5:
                insights.append(f"Column '{col}' has low cardinality ({unique_count} unique values)")
        
        return insights[:10]  # Limit to 10 insights
    
    def _get_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get detailed schema information"""
        schema = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            schema[col] = {
                'type': self._classify_type(dtype),
                'dtype': dtype,
                'nullable': df[col].isnull().any(),
                'unique_values': int(df[col].nunique()),
                'example': self._get_example_value(df[col])
            }
        return schema
    
    def _classify_type(self, dtype: str) -> str:
        """Classify dtype into broader categories"""
        dtype_lower = dtype.lower()
        if 'int' in dtype_lower or 'float' in dtype_lower:
            return 'numerical'
        elif 'object' in dtype_lower or 'string' in dtype_lower:
            return 'categorical'
        elif 'datetime' in dtype_lower or 'time' in dtype_lower:
            return 'datetime'
        elif 'bool' in dtype_lower:
            return 'boolean'
        else:
            return 'other'
    
    def _get_example_value(self, series) -> Any:
        """Get example value from series"""
        non_null = series.dropna()
        if len(non_null) > 0:
            example = non_null.iloc[0]
            if isinstance(example, (np.integer, np.int64)):
                return int(example)
            elif isinstance(example, (np.floating, np.float64)):
                return float(example)
            else:
                return str(example)
        return None
    
    def _get_quality_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate data quality metrics"""
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isnull().sum().sum()
        
        return {
            'completeness': round((1 - missing_cells / total_cells) * 100, 1),
            'uniqueness': round((1 - df.duplicated().sum() / len(df)) * 100, 1),
            'validity': self._calculate_validity_score(df),
            'consistency': self._calculate_consistency_score(df),
            'overall_score': 0  # Will be calculated
        }
    
    def _calculate_validity_score(self, df: pd.DataFrame) -> float:
        """Calculate validity score based on data types"""
        score = 0
        count = 0
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            if 'int' in dtype or 'float' in dtype:
                # Check if column contains only numeric values
                try:
                    pd.to_numeric(df[col], errors='coerce')
                    numeric_count = df[col].notna().sum()
                    total_count = len(df[col])
                    if total_count > 0:
                        score += numeric_count / total_count
                        count += 1
                except:
                    pass
        
        return round((score / count * 100), 1) if count > 0 else 0
    
    def _calculate_consistency_score(self, df: pd.DataFrame) -> float:
        """Calculate consistency score based on value patterns"""
        # Simple implementation - can be enhanced
        score = 0
        count = 0
        
        for col in df.columns:
            unique_ratio = df[col].nunique() / len(df)
            if 0.1 < unique_ratio < 0.9:  # Neither too unique nor too repetitive
                score += 1
            count += 1
        
        return round((score / count * 100), 1) if count > 0 else 0
    
    def _generate_semantic_summary(self, df: pd.DataFrame) -> str:
        """Generate semantic summary of the dataframe"""
        summary_parts = []
        
        # Add shape info
        summary_parts.append(f"A dataset with {len(df):,} rows and {len(df.columns)} columns")
        
        # Add column type info
        numeric_count = len(df.select_dtypes(include=[np.number]).columns)
        categorical_count = len(df.select_dtypes(include=['object']).columns)
        datetime_count = len(df.select_dtypes(include=['datetime']).columns)
        
        if numeric_count > 0:
            summary_parts.append(f"{numeric_count} numeric columns")
        if categorical_count > 0:
            summary_parts.append(f"{categorical_count} categorical columns")
        if datetime_count > 0:
            summary_parts.append(f"{datetime_count} datetime columns")
        
        # Add key statistics if available
        if numeric_count > 0:
            first_numeric = df.select_dtypes(include=[np.number]).columns[0]
            if df[first_numeric].notna().any():
                min_val = df[first_numeric].min()
                max_val = df[first_numeric].max()
                summary_parts.append(f"Values in '{first_numeric}' range from {min_val:.2f} to {max_val:.2f}")
        
        return ". ".join(summary_parts)
    
    def _enforce_size_limits(self, twin: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce size limits on twin representation"""
        import copy
        twin_copy = copy.deepcopy(twin)
        
        # Convert to JSON string to check size
        twin_json = json.dumps(twin_copy)
        
        if len(twin_json) > self.max_chars:
            # Remove detailed samples first
            if 'samples' in twin_copy:
                for sample_type in ['random', 'statistical', 'tail']:
                    if sample_type in twin_copy['samples']:
                        twin_copy['samples'][sample_type] = []
            
            # Truncate statistics
            if 'statistics' in twin_copy:
                stats = twin_copy['statistics']
                if 'numerical' in stats:
                    # Keep only first 5 numerical columns
                    numerical_cols = list(stats['numerical'].keys())
                    if len(numerical_cols) > 5:
                        for col in numerical_cols[5:]:
                            del stats['numerical'][col]
                
                if 'categorical' in stats:
                    # Keep only first 5 categorical columns
                    categorical_cols = list(stats['categorical'].keys())
                    if len(categorical_cols) > 5:
                        for col in categorical_cols[5:]:
                            del stats['categorical'][col]
        
        return twin_copy
    
    def get_compressed_twin(self, twin: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get compressed version of twin for LLM context
        
        Args:
            twin: Full twin dictionary
            
        Returns:
            Compressed twin dictionary
        """
        compressed = {
            'metadata': twin.get('metadata', {}),
            'fingerprint': twin.get('fingerprint', ''),
            'schema_summary': self._get_schema_summary(twin.get('schema', {})),
            'key_insights': twin.get('insights', [])[:5],
            'quality_score': twin.get('quality', {}).get('overall_score', 0)
        }
        
        # Add sample from head
        if 'samples' in twin and 'head' in twin['samples']:
            compressed['sample'] = twin['samples']['head'][:2]
        
        # Add key statistics
        if 'statistics' in twin:
            stats = twin['statistics']
            compressed['key_stats'] = {
                'shape': [stats['basic'].get('total_rows', 0), 
                         stats['basic'].get('total_columns', 0)],
                'missing_percentage': stats['basic'].get('missing_percentage', 0),
                'top_correlations': stats.get('correlations', [])[:3]
            }
        
        return compressed
    
    def _get_schema_summary(self, schema: Dict[str, Any]) -> str:
        """Generate schema summary string"""
        type_counts = {}
        for col_info in schema.values():
            col_type = col_info.get('type', 'unknown')
            type_counts[col_type] = type_counts.get(col_type, 0) + 1
        
        summary_parts = []
        for col_type, count in type_counts.items():
            summary_parts.append(f"{count} {col_type}")
        
        return f"Columns: {', '.join(summary_parts)}"