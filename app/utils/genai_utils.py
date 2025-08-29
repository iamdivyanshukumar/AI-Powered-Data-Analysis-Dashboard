# app/utils/genai_utils.py - UPDATED
from openai import OpenAI
import json
from typing import List, Dict
from app.config import Config

class GenAIAnalyzer:
    """Handles all GenAI interactions for data analysis and visualization suggestions."""
    
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def get_visualization_suggestions(self, columns: List[Dict[str, str]]) -> List[Dict]:
        """
        Get visualization suggestions from GenAI based on column names and types.
        
        Args:
            columns: List of dictionaries with 'name' and 'type' keys
            
        Returns:
            List of visualization suggestions with type, columns, and reasoning
        """
        prompt = self._build_suggestion_prompt(columns)
        response = self._get_ai_response(prompt)
        return self._parse_ai_response(response)
    
    def get_graph_summary(self, graph_type: str, x_col: str, y_col: str, data_sample: str) -> str:
        """
        Generate a natural language summary for a generated graph.
        
        Args:
            graph_type: Type of graph (e.g., 'scatter', 'bar')
            x_col: Name of x-axis column
            y_col: Name of y-axis column (None for single-column graphs)
            data_sample: Sample data from the dataframe
            
        Returns:
            Natural language summary of the graph insights
        """
        prompt = self._build_summary_prompt(graph_type, x_col, y_col, data_sample)
        return self._get_ai_response(prompt, max_tokens=200)
    
    def _build_suggestion_prompt(self, columns: List[Dict[str, str]]) -> str:
        """Build the prompt for visualization suggestions."""
        columns_json = json.dumps({"columns": columns}, indent=2)
        return f"""
You are an expert data analyst. Your task is to suggest the most appropriate and insightful visualizations for the given dataset.

Column information:
{columns_json}

Please suggest 3-5 visualizations that would provide the most insight. For each suggestion, provide:
1. Graph type (choose from: scatter, line, bar, histogram, box, pie)
2. X-axis column
3. Y-axis column (if applicable)
4. A brief reason why this visualization would be insightful

Format your response as a JSON array of objects with these keys: type, x, y, reason.

Example:
[
  {{
    "type": "scatter",
    "x": "age",
    "y": "income",
    "reason": "To examine the relationship between age and income, looking for correlations or patterns."
  }},
  {{
    "type": "histogram",
    "x": "age",
    "reason": "To understand the distribution of ages in the dataset."
  }}
]
"""
    
    def _build_summary_prompt(self, graph_type: str, x_col: str, y_col: str, data_sample: str) -> str:
        """Build the prompt for graph summary generation."""
        return f"""
You are a data scientist analyzing a {graph_type} plot. 

The visualization shows:
- X-axis: {x_col}
- Y-axis: {y_col if y_col else 'N/A (single variable)'}

Here's a sample of the data used:
{data_sample}

Please provide a concise but insightful summary (3-5 sentences) of what this visualization reveals. Focus on:
1. Key patterns, trends, or relationships shown
2. Any notable outliers or anomalies
3. What this might mean in a practical context
4. Any limitations or considerations for interpreting this visualization

Write in clear, professional language suitable for a business audience.
"""
    
    def _get_ai_response(self, prompt: str, max_tokens: int = 300) -> str:
        """Get response from OpenAI API using the new client interface."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using cheaper model
                messages=[
                    {"role": "system", "content": "You are a helpful data analysis assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Unable to generate insights due to an error: {str(e)}"
    
    def _parse_ai_response(self, response: str) -> List[Dict]:
        """Parse the AI response into a structured format."""
        try:
            # Try to extract JSON from the response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: return some default visualizations
            return [
                {"type": "histogram", "x": "age", "reason": "Distribution of ages"},
                {"type": "scatter", "x": "age", "y": "income", "reason": "Relationship between age and income"}
            ]