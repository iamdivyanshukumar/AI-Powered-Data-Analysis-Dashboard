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
        return self._get_ai_response(prompt, max_tokens=150)
    
    def _build_suggestion_prompt(self, columns: List[Dict[str, str]]) -> str:
        """Build the prompt for visualization suggestions."""
        columns_json = json.dumps({"columns": columns}, indent=2)
        return f"""
You are an expert data analyst.

Given the following column names and their types from a CSV file:

{columns_json}

Suggest the top 3 most interesting visualizations. For each, provide:
- Graph type (e.g., bar, scatter, line, pie, histogram)
- Columns used (x and y)
- Reason why it's insightful

Respond in this format:
[
  {{
    "type": "scatter",
    "x": "age",
    "y": "salary",
    "reason": "To see if age correlates with income."
  }},
  ...
]
"""
    
    def _build_summary_prompt(self, graph_type: str, x_col: str, y_col: str, data_sample: str) -> str:
        """Build the prompt for graph summary generation."""
        return f"""
You are a data scientist. Below is a {graph_type} plot of '{x_col}' {'vs ' + y_col if y_col else ''}. 
Provide an insightful natural language summary in 2-4 lines that explains the patterns, 
correlations, or anomalies.

Data summary: 
{data_sample}
"""
    
    def _get_ai_response(self, prompt: str, max_tokens: int = 300) -> str:
        """Get response from OpenAI API using the new client interface."""
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful data analysis assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    
    def _parse_ai_response(self, response: str) -> List[Dict]:
        """Parse the AI response into a structured format."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback to handle cases where response isn't perfect JSON
            cleaned = response.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)