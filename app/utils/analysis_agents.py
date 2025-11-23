import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import logging
from openai import OpenAI
from app.config import Config

logger = logging.getLogger(__name__)

class SafeExecEnvironment:
    """
    A sandboxed environment to execute AI-generated Python code safely.
    """
    FORBIDDEN_TERMS = ['import os', 'import sys', 'subprocess', 'open(', '.read(', '.write(', 'drop(', 'delete']
    
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
        Executes pandas transformation code on a COPY of the dataframe.
        Expects code to modify 'df' in place.
        """
        if not SafeExecEnvironment.validate_code(code):
            return df # Return original if unsafe
            
        local_vars = {'df': df.copy(deep=True), 'pd': pd, 'np': np}
        
        try:
            # Wrap code to ensure it runs
            exec(code, {}, local_vars)
            
            # Get the modified dataframe
            df_new = local_vars['df']
            
            # Basic sanity check: Did we lose all data?
            if df_new.empty and not df.empty:
                logger.error("AI Code wiped the dataframe. Reverting.")
                return df
                
            return df_new
        except Exception as e:
            logger.error(f"Error executing AI Feature Engineering: {str(e)}")
            return df

class FeatureEngineerAgent:
    """
    Agent 1: Looks at data and writes code to create NEW features.
    """
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
        """
        Analyzes DF, writes pandas code to add features, executes it.
        Returns: (Enriched DataFrame, List of changes made)
        """
        # 1. Describe columns to LLM
        col_info = []
        for col in df.columns[:15]: # Limit to 15 cols to save tokens
            sample = str(df[col].dropna().iloc[0]) if not df[col].dropna().empty else "None"
            col_info.append(f"{col} ({df[col].dtype}): Sample='{sample}'")
            
        prompt = f"""
        You are a Senior Data Engineer.
        I have a Pandas DataFrame 'df' with these columns:
        {json.dumps(col_info, indent=2)}

        Your task: Write Python Pandas code to create 2-3 NEW useful features (columns) that would aid analysis.
        
        Rules:
        1. Use ONLY 'df['new_col'] = ...' syntax.
        2. Handle Datetimes: If a column looks like a date, extract Month/Year/Day.
        3. Handle Categorical: If low cardinality, maybe group smaller ones.
        4. Handle Numerical: Calculate Ratios (e.g., 'Revenue' / 'Units').
        5. DO NOT delete rows. DO NOT print anything.
        6. Return ONLY the python code. No markdown backticks.

        Example Output:
        df['Date'] = pd.to_datetime(df['Date'])
        df['Month'] = df['Date'].dt.month_name()
        df['Total_Cost'] = df['Quantity'] * df['Unit_Price']
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "You are a python coding assistant."}, 
                          {"role": "user", "content": prompt}],
                temperature=0.2
            )
            code = response.choices[0].message.content.strip()
            
            # Clean code blocks if present
            code = code.replace("```python", "").replace("```", "").strip()
            
            logger.info(f"AI Feature Engineering Code:\n{code}")
            
            # Execute safely
            df_enriched = SafeExecEnvironment.execute_transformation(df, code)
            
            # Detect what changed
            new_cols = list(set(df_enriched.columns) - set(df.columns))
            return df_enriched, new_cols
            
        except Exception as e:
            logger.error(f"Feature Engineering Failed: {e}")
            return df, []

class DynamicVisualizerAgent:
    """
    Agent 2: Decides the BEST plots and generates Plotly JSON directly.
    """
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_plots(self, df: pd.DataFrame, context: str = "") -> list[dict]:
        """
        Asks LLM to generate Plotly code for the dataset.
        Returns a list of visualization dictionaries.
        """
        # 1. Prepare metadata
        columns = list(df.columns)
        dtypes = {k: str(v) for k,v in df.dtypes.items()}
        
        prompt = f"""
        You are a Data Visualization Expert.
        Dataset Columns: {columns}
        Data Types: {dtypes}
        Context: {context}

        Task: Create 3 insightful visualizations using Plotly Express (`px`).
        
        Requirements:
        1. Choose the best graph type (Scatter, Bar, Box, Histogram, Line) based on the data.
        2. Use aggregation if necessary (e.g., sum sales by month).
        3. The output must be a JSON list of configurations, NOT python code.
        
        JSON Format expected:
        [
            {{
                "type": "bar",
                "x": "ColumnName",
                "y": "ColumnName",
                "color": "OptionalColumn",
                "title": "A descriptive title",
                "reason": "Why this graph is interesting"
            }}
        ]
        
        Make sure column names match EXACTLY.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            content = response.choices[0].message.content.strip()
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            
            configs = json.loads(content)
            return configs
            
        except Exception as e:
            logger.error(f"Dynamic Plotting Failed: {e}")
            return [] # Fallback will happen in routes