import pandas as pd
from typing import List, Dict

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

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Basic data cleaning for the uploaded CSV."""
    # Drop duplicate rows
    df = df.drop_duplicates()
    
    # Convert object columns to categorical if they have low cardinality
    for col in df.select_dtypes(include=['object']):
        if len(df[col].unique()) < 50:
            df[col] = df[col].astype('category')
    
    # Convert datetime strings if possible
    for col in df.select_dtypes(include=['object']):
        try:
            df[col] = pd.to_datetime(df[col])
        except (ValueError, TypeError):
            pass
    
    return df