import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from sklearn.preprocessing import LabelEncoder
import json
import logging

logger = logging.getLogger(__name__)

def validate_csv(filename: str) -> bool:
    """Validate that the file has a CSV extension."""
    allowed_extensions = {'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_column_info(df: pd.DataFrame) -> List[Dict[str, str]]:
    """
    Extract column names and types from DataFrame.
    
    Args:
        df: Pandas DataFrame
        
    Returns:
        List of dictionaries with 'name' and 'type' for each column
    """
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
    """
    Comprehensive data cleaning for the uploaded CSV.
    
    Returns:
        Tuple of (cleaned DataFrame, encoding mappings)
    """
    # Make a copy to avoid modifying original
    df_clean = df.copy()
    encoding_mappings = {}
    
    # Drop duplicate rows
    df_clean = df_clean.drop_duplicates()
    
    # Fill missing values - fixed to avoid in-place operations on copies
    for col in df_clean.columns:
        if pd.api.types.is_numeric_dtype(df_clean[col]):
            # Fill numerical columns with median
            median_val = df_clean[col].median()
            df_clean[col] = df_clean[col].fillna(median_val)
        else:
            # Fill categorical columns with mode
            mode_val = df_clean[col].mode()
            fill_value = mode_val[0] if not mode_val.empty else "Unknown"
            df_clean[col] = df_clean[col].fillna(fill_value)
    
    # Encode categorical columns using label encoding and store mappings
    le = LabelEncoder()
    categorical_cols = df_clean.select_dtypes(include=['object']).columns
    
    for col in categorical_cols:
        # Store original values before encoding
        df_clean[col] = df_clean[col].astype(str)
        df_clean[col] = le.fit_transform(df_clean[col])
        
        # Create mapping dictionary
        encoding_mappings[col] = {
            int(encoded): str(original) 
            for encoded, original in zip(le.transform(le.classes_), le.classes_)
        }
    
    return df_clean, encoding_mappings

def get_dataset_stats(df: pd.DataFrame) -> Dict:
    """Get comprehensive statistics about the dataset. Always returns a dict."""
    try:
        # Convert DataFrame to JSON-serializable format
        head_data = {}
        for col in df.columns:
            head_data[col] = df[col].head().tolist()
        
        describe_data = {}
        if not df.select_dtypes(include=[np.number]).empty:
            desc = df.describe()
            for stat in desc.index:
                describe_data[stat] = desc.loc[stat].tolist()
        
        stats = {
            'shape': list(df.shape),
            'total_null_values': int(df.isnull().sum().sum()),
            'column_null_values': df.isnull().sum().to_dict(),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'head': head_data,
            'describe': describe_data,
            'info': {
                'columns': list(df.columns),
                'non_null_counts': df.count().to_dict(),
                'memory_usage': int(df.memory_usage(deep=True).sum())
            }
        }
        return stats
        
    except Exception as e:
        logger.error(f"Error generating dataset stats: {str(e)}")
        # Return minimal stats on error
        return {
            'shape': list(df.shape) if hasattr(df, 'shape') else [0, 0],
            'total_null_values': 0,
            'column_null_values': {},
            'dtypes': {},
            'head': {},
            'describe': {},
            'info': {
                'columns': list(df.columns) if hasattr(df, 'columns') else [],
                'non_null_counts': {},
                'memory_usage': 0
            }
        }