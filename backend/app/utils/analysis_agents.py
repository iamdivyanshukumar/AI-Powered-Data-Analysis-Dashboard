import pandas as pd
import numpy as np
import json
import logging
import re
from openai import OpenAI
from app.config import Config

logger = logging.getLogger(__name__)

class SafeExecEnvironment:
    """
    A STRICT sandboxed environment.
    Ensures AI uses ONLY pre-installed, guaranteed dependencies (Pandas, Numpy, Re).
    """
    # We block 'import' entirely. The AI must use the libraries we give it.
    FORBIDDEN_TERMS = [
        'import ', 'from ', # Block all imports
        'open(', 'exec(', 'eval(', '__import__', 
        '.system(', '.popen(', 'delete', 'remove', 'rmdir'
    ]
    
    @staticmethod
    def validate_code(code: str) -> bool:
        """Check if code contains forbidden operations."""
        for term in SafeExecEnvironment.FORBIDDEN_TERMS:
            if term in code:
                logger.warning(f"Security Block: AI tried to use forbidden term '{term}'")
                return False
        return True

    @staticmethod
    def execute_transformation(df: pd.DataFrame, code: str) -> pd.DataFrame:
        """
        Executes code on a COPY.
        Pre-loads 'pd', 'np', and 're' so the AI doesn't need to import them.
        """
        if not SafeExecEnvironment.validate_code(code):
            return df 
            
        # PRE-LOAD DEPENDENCIES
        # The AI has access to these variable names automatically.
        local_vars = {
            'df': df.copy(deep=True), 
            'pd': pd, 
            'np': np, 
            're': re  # Regex is standard python, safe to include
        }
        
        try:
            # Wrap code to ensure it runs
            exec(code, {}, local_vars)
            
            # Get the modified dataframe
            df_new = local_vars['df']
            
            # Sanity check: Did we lose all rows/cols?
            if df_new.empty and not df.empty: return df
            if len(df_new.columns) == 0: return df
            
            return df_new
        except Exception as e:
            logger.error(f"Error executing AI Feature Engineering: {str(e)}")
            return df

class FeatureEngineerAgent:
    """
    Agent 1: Feature Engineering with Strict Dependency Control.
    """
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
        col_info = []
        for col in df.columns[:15]: 
            sample = str(df[col].dropna().iloc[0]) if not df[col].dropna().empty else "None"
            col_info.append(f"{col} ({df[col].dtype}): Sample='{sample}'")
            
        prompt = f"""
        You are a Python Data Engineer.
        DataFrame 'df' columns:
        {json.dumps(col_info, indent=2)}

        Task: Write Pandas code to clean data or create features.
        
        STRICT PRODUCTION RULES:
        1. DO NOT write any 'import' statements.
        2. You ALREADY have access to: 'pd' (pandas), 'np' (numpy), 're' (regex). USE THEM.
        3. Clean text columns (remove 'mi', '$', ',') using `df['col'].str.replace(...)`.
        4. Convert types using `astype(float)` or `pd.to_numeric`.
        5. If using regex inside apply, use `re.search` directly.
        6. Output ONLY code.

        Example of VALID code:
        df['price_clean'] = df['price'].str.replace('$', '').astype(float)
        df['year'] = pd.to_datetime(df['date']).dt.year
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "You are a python coding assistant. Write only code."}, 
                          {"role": "user", "content": prompt}],
                temperature=0.1 # Low temp = more reliable code
            )
            code = response.choices[0].message.content.strip()
            
            # Clean markdown wrappers
            code = code.replace("```python", "").replace("```", "").strip()
            
            if not code: return df, []

            logger.info(f"AI Feature Engineering Code:\n{code}")
            
            # Execute
            df_enriched = SafeExecEnvironment.execute_transformation(df, code)
            new_cols = list(set(df_enriched.columns) - set(df.columns))
            return df_enriched, new_cols
            
        except Exception as e:
            logger.error(f"Feature Engineering Failed: {e}")
            return df, []

class DynamicVisualizerAgent:
    """
    Agent 2: Dynamic Visualization (No Code Execution, Just Config).
    """
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_plots(self, df: pd.DataFrame) -> list[dict]:
        columns = list(df.columns)
        # Strict Type Checking for AI Context
        dtypes = {}
        for k, v in df.dtypes.items():
            if pd.api.types.is_numeric_dtype(v):
                dtypes[k] = "Numeric (Safe for Math)"
            else:
                dtypes[k] = "String/Categorical (No Math)"
        
        prompt = f"""
        You are a Data Visualization Configurator.
        Columns: {columns}
        Types: {json.dumps(dtypes, indent=2)}

        Task: Generate 4 Plotly Express configurations.
        
        CRITICAL RULES:
        1. SCATTER/BOX plots: Y-axis MUST be 'Numeric'. Never use 'String' for Y.
        2. BAR plots: X can be String, Y must be Numeric (or null for counts).
        3. Prioritize using any NEW columns created (usually at end of list).
        
        JSON Format:
        [
            {{
                "type": "scatter",
                "x": "mileage_numeric",
                "y": "price",
                "reason": "Correlation check"
            }}
        ]
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            content = response.choices[0].message.content.strip()
            if "```json" in content: content = content.split("```json")[1].split("```")[0]
            elif "```" in content: content = content.split("```")[1].split("```")[0]
            
            configs = json.loads(content)
            
            # Apply Critic Logic
            refined_configs = []
            for config in configs:
                refined = self._critique_and_refine(config, df)
                if refined:
                    refined_configs.append(refined)
            
            return refined_configs
            
        except Exception as e:
            logger.error(f"Dynamic Plotting Failed: {e}")
            return []

    def _critique_and_refine(self, config, df):
        try:
            x_col = config.get('x')
            y_col = config.get('y')
            g_type = config.get('type')
            
            if x_col not in df.columns: return None
            if y_col and y_col not in df.columns: return None
            
            # Rule: Numeric Safety
            if g_type in ['scatter', 'box', 'line', 'histogram']:
                if y_col and not pd.api.types.is_numeric_dtype(df[y_col]):
                    logger.warning(f"Critic Rejected: {y_col} is not numeric")
                    return None
                # Histogram X must be numeric usually
                if g_type == 'histogram' and not pd.api.types.is_numeric_dtype(df[x_col]):
                     return None

            # Rule: Bar Chart Limits
            if g_type == 'bar':
                if df[x_col].nunique() > 15:
                    config['modifier'] = 'top_10'
            
            # Rule: Scatter Limits
            if g_type == 'scatter' and len(df) > 2000:
                config['modifier'] = 'sample_1000'
            
            return config
        except Exception:
            return config