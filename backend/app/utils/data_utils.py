import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Any
from sklearn.preprocessing import LabelEncoder
import json
import logging
import random

logger = logging.getLogger(__name__)

def validate_csv(filename: str) -> bool:
    """Validate that the file has a CSV extension."""
    allowed_extensions = {'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_column_info(df: pd.DataFrame) -> List[Dict[str, str]]:
    """Extract column names and types from DataFrame."""
    column_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        if 'object' in dtype or 'category' in dtype:
            col_type = 'categorical'
        elif 'datetime' in dtype:
            col_type = 'datetime'
        else:
            col_type = 'numerical'
        
        column_info.append({'name': col, 'type': col_type})
    
    return column_info

def clean_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """Comprehensive data cleaning for the uploaded CSV."""
    df_clean = df.copy()
    encoding_mappings = {}
    
    # Drop duplicate rows
    df_clean = df_clean.drop_duplicates()
    
    # Fill missing values
    for col in df_clean.columns:
        if pd.api.types.is_numeric_dtype(df_clean[col]):
            median_val = df_clean[col].median()
            df_clean[col] = df_clean[col].fillna(median_val)
        else:
            mode_val = df_clean[col].mode()
            fill_value = mode_val[0] if not mode_val.empty else "Unknown"
            df_clean[col] = df_clean[col].fillna(fill_value)
    
    # Store original categorical values before encoding
    categorical_cols = df_clean.select_dtypes(include=['object']).columns
    
    for col in categorical_cols:
        # Store original values and their frequencies
        value_counts = df_clean[col].value_counts().to_dict()
        encoding_mappings[col] = {
            'original_values': value_counts,
            'unique_count': len(value_counts),
            'most_frequent': max(value_counts, key=value_counts.get) if value_counts else None
        }
    
    return df_clean, encoding_mappings

def get_dataset_stats(df: pd.DataFrame) -> Dict:
    """Get comprehensive statistics about the dataset."""
    try:
        # Basic info
        basic_info = {
            'total_rows': int(len(df)),
            'total_columns': int(len(df.columns)),
            'missing_values': int(df.isnull().sum().sum()),
            'duplicate_rows': int(df.duplicated().sum()),
            'memory_usage_mb': float(round(df.memory_usage(deep=True).sum() / 1024**2, 2))
        }
        
        # Column details
        column_details = {}
        for col in df.columns:
            col_info = {
                'data_type': str(df[col].dtype),
                'missing_count': int(df[col].isnull().sum()),
                'missing_percentage': float(round((df[col].isnull().sum() / len(df)) * 100, 2)),
                'unique_count': int(df[col].nunique())
            }
            
            if pd.api.types.is_numeric_dtype(df[col]):
                col_info.update({
                    'min': float(df[col].min()) if not df[col].isna().all() else None,
                    'max': float(df[col].max()) if not df[col].isna().all() else None,
                    'mean': float(df[col].mean()) if not df[col].isna().all() else None,
                    'median': float(df[col].median()) if not df[col].isna().all() else None,
                    'std': float(df[col].std()) if not df[col].isna().all() else None
                })
            else:
                # For categorical columns
                top_values = df[col].value_counts().head(5).to_dict()
                col_info['top_values'] = {str(k): int(v) for k, v in top_values.items()}
            
            column_details[col] = col_info
        
        # Sample data (first 5 rows with original values)
        sample_data = []
        for i in range(min(5, len(df))):
            # Convert each value to standard python type to avoid JSON errors
            row_dict = {}
            for k, v in df.iloc[i].to_dict().items():
                if isinstance(v, (np.integer, np.int64)):
                    row_dict[k] = int(v)
                elif isinstance(v, (np.floating, np.float64)):
                    row_dict[k] = float(v)
                else:
                    row_dict[k] = v
            sample_data.append(row_dict)
        
        stats = {
            'basic_info': basic_info,
            'column_details': column_details,
            'sample_data': sample_data,
            'data_types_summary': {
                'numerical_columns': list(df.select_dtypes(include=[np.number]).columns),
                'categorical_columns': list(df.select_dtypes(include=['object']).columns),
                'datetime_columns': list(df.select_dtypes(include=['datetime']).columns)
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error generating dataset stats: {str(e)}")
        return {
            'basic_info': {},
            'column_details': {},
            'sample_data': [],
            'data_types_summary': {},
            'error': str(e)
        }

def get_smart_context(df: pd.DataFrame, max_samples: int = 15, chunks_per_sample: int = 3) -> Dict[str, Any]:
    """
    Generate smart context with multiple random chunks for better context.
    """
    if df.empty:
        return {"error": "Empty dataset"}
    
    try:
        # Increase number of random samples and use multiple chunks
        random_samples = get_multiple_chunk_samples(df, max_samples=max_samples, chunks_per_sample=chunks_per_sample)
        
        # Statistical representatives
        statistical_samples = get_statistical_samples(df, max_samples=5)
        
        # Category examples
        category_samples = get_category_samples(df, max_categories=3)
        
        # Combine all samples
        all_samples = random_samples + statistical_samples + category_samples
        
        # Limit total exposure but keep more than before
        exposed_samples = all_samples[:max_samples]
        
        # Get comprehensive statistics
        numerical_summary = get_numerical_summary(df)
        categorical_summary = get_categorical_summary(df)
        
        # --- NEW: Run the Insight Engine (Detective) ---
        detective_report = run_insight_engine(df)
        # -----------------------------------------------

        context = {
            "metadata": {
                "shape": [len(df), len(df.columns)],
                "total_rows": int(len(df)),
                "columns": list(df.columns),
                "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "numerical_cols": list(df.select_dtypes(include=[np.number]).columns),
                "categorical_cols": list(df.select_dtypes(include=['object']).columns),
                "missing_values": int(df.isnull().sum().sum())
            },
            "exposed_samples": {
                "random_samples": random_samples[:8],
                "statistical_representatives": statistical_samples,
                "category_examples": category_samples,
                "all_samples": exposed_samples
            },
            "summary_statistics": {
                "numerical_summary": numerical_summary,
                "categorical_summary": categorical_summary,
                "data_quality": {
                    "completeness_score": float(round((1 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))) * 100, 1)),
                    "unique_ratio": {col: float(round(df[col].nunique() / len(df), 3)) for col in df.columns}
                }
            },
            "detective_report": detective_report,
            "constraints": {
                "max_rows_exposed": int(len(exposed_samples)),
                "total_dataset_rows": int(len(df)),
                "exposure_percentage": float(round((len(exposed_samples) / len(df)) * 100, 3)),
                "chunks_used": chunks_per_sample,
                "privacy_level": "medium"
            }
        }
        
        logger.info(f"Generated smart context with {len(exposed_samples)} samples")
        return context
        
    except Exception as e:
        logger.error(f"Error generating smart context: {str(e)}", exc_info=True)
        return {"error": str(e)}

def get_multiple_chunk_samples(df: pd.DataFrame, max_samples: int = 15, chunks_per_sample: int = 3) -> List[Dict]:
    """Get multiple random samples from different chunks of the dataset."""
    samples = []
    if len(df) == 0: return samples
    
    actual_samples = min(max_samples, len(df))
    chunk_size = max(10, len(df) // 20)
    
    for sample_num in range(actual_samples):
        chunk_samples = []
        for chunk_idx in range(chunks_per_sample):
            if len(df) > chunk_size:
                start_idx = random.randint(0, len(df) - chunk_size)
                sample_idx = random.randint(start_idx, min(start_idx + chunk_size - 1, len(df) - 1))
            else:
                sample_idx = random.randint(0, len(df) - 1)
            
            # Convert to dict and force python types
            row = df.iloc[sample_idx].to_dict()
            clean_row = {}
            for k, v in row.items():
                if isinstance(v, (np.integer, np.int64)): clean_row[k] = int(v)
                elif isinstance(v, (np.floating, np.float64)): clean_row[k] = float(v)
                else: clean_row[k] = v
            chunk_samples.append(clean_row)
        
        if chunk_samples:
            combined_sample = chunk_samples[0].copy()
            combined_sample['_sample_info'] = f"sample_{sample_num+1}"
            samples.append(combined_sample)
    
    return samples

def get_statistical_samples(df: pd.DataFrame, max_samples: int = 5) -> List[Dict]:
    samples = []
    numerical_cols = df.select_dtypes(include=[np.number]).columns
    if len(numerical_cols) == 0: return samples
    
    for col in numerical_cols[:max_samples]:
        try:
            if df[col].isna().all(): continue
            
            # Helper to safely convert row to dict
            def safe_to_dict(idx, type_label):
                row = df.loc[idx].to_dict()
                clean_row = {}
                for k, v in row.items():
                    if isinstance(v, (np.integer, np.int64)): clean_row[k] = int(v)
                    elif isinstance(v, (np.floating, np.float64)): clean_row[k] = float(v)
                    else: clean_row[k] = v
                clean_row['_stat_type'] = type_label
                return clean_row

            # Min
            min_idx = df[col].idxmin()
            if pd.notna(min_idx): samples.append(safe_to_dict(min_idx, f"min_{col}"))
            
            # Max
            max_idx = df[col].idxmax()
            if pd.notna(max_idx): samples.append(safe_to_dict(max_idx, f"max_{col}"))
            
            # Median
            median_val = df[col].median()
            closest_idx = (df[col] - median_val).abs().idxmin()
            if pd.notna(closest_idx): samples.append(safe_to_dict(closest_idx, f"median_{col}"))
                
        except Exception as e:
            continue
    return samples[:max_samples * 3]

def get_category_samples(df: pd.DataFrame, max_categories: int = 3) -> List[Dict]:
    samples = []
    categorical_cols = df.select_dtypes(include=['object']).columns
    if len(categorical_cols) == 0: return samples
    
    for col in categorical_cols[:max_categories]:
        try:
            value_counts = df[col].value_counts()
            for i, (category, _) in enumerate(value_counts.head(2).items()):
                category_rows = df[df[col] == category]
                if len(category_rows) > 0:
                    # Safe Convert
                    row = category_rows.iloc[0].to_dict()
                    clean_row = {}
                    for k, v in row.items():
                        if isinstance(v, (np.integer, np.int64)): clean_row[k] = int(v)
                        elif isinstance(v, (np.floating, np.float64)): clean_row[k] = float(v)
                        else: clean_row[k] = v
                    clean_row['_category_type'] = f"top_{i+1}_{col}"
                    samples.append(clean_row)
        except Exception:
            continue
    return samples

def get_numerical_summary(df: pd.DataFrame) -> Dict:
    numerical_cols = df.select_dtypes(include=[np.number]).columns
    summary = {}
    for col in numerical_cols:
        if df[col].isna().all(): continue
        col_data = df[col].dropna()
        summary[col] = {
            "count": int(len(col_data)),
            "mean": float(col_data.mean()),
            "std": float(col_data.std()),
            "min": float(col_data.min()),
            "max": float(col_data.max()),
            "skewness": float(col_data.skew()),
            "outliers": detect_outliers(col_data)
        }
    return summary

def get_categorical_summary(df: pd.DataFrame) -> Dict:
    categorical_cols = df.select_dtypes(include=['object']).columns
    summary = {}
    for col in categorical_cols:
        value_counts = df[col].value_counts()
        summary[col] = {
            "unique_count": int(value_counts.nunique()),
            "most_frequent": {
                "value": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                "count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0
            },
            "entropy": calculate_entropy(value_counts)
        }
    return summary

def detect_outliers(series: pd.Series) -> Dict:
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = series[(series < lower_bound) | (series > upper_bound)]
    
    return {
        "count": int(len(outliers)),
        "percentage": float(round((len(outliers) / len(series)) * 100, 2)),
        "bounds": {"lower": float(lower_bound), "upper": float(upper_bound)}
    }

def calculate_entropy(value_counts: pd.Series) -> float:
    probabilities = value_counts / value_counts.sum()
    entropy = -np.sum(probabilities * np.log2(probabilities))
    return float(entropy)

# --- FIXED DETECTIVE ENGINE (Type Safe) ---

def run_insight_engine(df: pd.DataFrame) -> Dict[str, Any]:
    """
    The 'Detective' that hunts for hidden patterns.
    Includes strict type casting to avoid JSON serialization errors.
    """
    report = {
        "correlations": [],
        "anomalies": [],
        "dominance": []
    }
    
    # 1. Detect Correlations (Numerical)
    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) > 1:
        corr_matrix = numeric_df.corr()
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                col1 = corr_matrix.columns[i]
                col2 = corr_matrix.columns[j]
                val = corr_matrix.iloc[i, j]
                
                if abs(val) > 0.7:
                    report["correlations"].append({
                        "pair": [str(col1), str(col2)],
                        "strength": float(round(val, 2)), # FORCE FLOAT
                        "type": "Positive" if val > 0 else "Negative"
                    })
    
    # 2. Detect Anomalies
    for col in numeric_df.columns:
        col_data = numeric_df[col].dropna()
        if len(col_data) < 10: continue
        
        mean = col_data.mean()
        std = col_data.std()
        if std == 0: continue
        
        anomalies = col_data[((col_data - mean).abs() / std) > 3]
        
        if not anomalies.empty:
            # Convert numpy values to python types
            example_vals = []
            for x in anomalies.head(3).values:
                if isinstance(x, (np.floating, float)):
                    example_vals.append(float(x))
                elif isinstance(x, (np.integer, int)):
                    example_vals.append(int(x))
                else:
                    example_vals.append(str(x))

            report["anomalies"].append({
                "column": str(col),
                "count": int(len(anomalies)), # FORCE INT
                "percent": float(round(len(anomalies)/len(col_data)*100, 1)), # FORCE FLOAT
                "example_values": example_vals
            })

    # 3. Detect Dominance
    cat_df = df.select_dtypes(include=['object'])
    for col in cat_df.columns:
        counts = cat_df[col].value_counts(normalize=True)
        if not counts.empty and counts.iloc[0] > 0.80:
            report["dominance"].append({
                "column": str(col),
                "value": str(counts.index[0]),
                "percent": float(round(counts.iloc[0]*100, 1)) # FORCE FLOAT
            })
            
    return report