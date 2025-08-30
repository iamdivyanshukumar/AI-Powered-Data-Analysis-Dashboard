from openai import OpenAI
import json
from typing import List, Dict
from app.config import Config
import logging

logger = logging.getLogger(__name__)

class GenAIAnalyzer:
    """Handles all GenAI interactions for data analysis and visualization suggestions."""
    
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def get_visualization_suggestions(self, columns: List[Dict[str, str]], dataset_stats) -> List[Dict]:
        """
        Get balanced visualization suggestions from GenAI based on column types.
        Excludes scatter plots as requested.
        """
        prompt = self._build_suggestion_prompt(columns, dataset_stats)
        response = self._get_ai_response(prompt)
        return self._parse_ai_response(response, columns)
    
    def get_graph_summary(self, graph_type: str, x_col: str, y_col: str, graph_description: str, data_stats: Dict = None) -> str:
        """
        Generate a concise natural language summary for a generated graph.
        """
        prompt = self._build_summary_prompt(graph_type, x_col, y_col, graph_description, data_stats)
        return self._get_ai_response(prompt, max_tokens=150)
    
    def _build_suggestion_prompt(self, columns: List[Dict[str, str]], dataset_stats) -> str:
        """Build balanced prompt for visualization suggestions excluding scatter plots."""
        numerical_cols = [col['name'] for col in columns if col['type'] == 'numerical']
        categorical_cols = [col['name'] for col in columns if col['type'] == 'categorical']
        
        columns_info = f"""
Numerical Columns: {', '.join(numerical_cols) if numerical_cols else 'None'}
Categorical Columns: {', '.join(categorical_cols) if categorical_cols else 'None'}
"""
        
        # Handle both dict and string (JSON) input for dataset_stats
        if isinstance(dataset_stats, str):
            try:
                dataset_stats = json.loads(dataset_stats)
            except (json.JSONDecodeError, TypeError):
                logger.warning("dataset_stats is string but not valid JSON, using empty dict")
                dataset_stats = {}
        elif not isinstance(dataset_stats, dict):
            logger.warning(f"dataset_stats is of type {type(dataset_stats)}, using empty dict")
            dataset_stats = {}
        
        # Safely access dictionary values
        shape = dataset_stats.get('shape', [0, 0])
        rows = shape[0] if isinstance(shape, list) and len(shape) > 0 else 0
        cols = shape[1] if isinstance(shape, list) and len(shape) > 1 else 0
        null_values = dataset_stats.get('total_null_values', 0)
        
        return f"""
You are an expert data analyst. Suggest 3-5 appropriate visualizations for this dataset.

Dataset Info:
- Rows: {rows}
- Columns: {cols}
- Null values: {null_values}
{columns_info}

IMPORTANT: 
1. Do NOT suggest heatmap or box plots as they are automatically generated separately.
2. Do NOT suggest scatter plots under any circumstances.
2. Do NOT suggest line plots under any circumstances.

Consider these visualization types based on data characteristics:

FOR NUMERICAL DATA:
- Histogram: For single numerical variable distribution
- Density plot: For smooth distribution visualization

FOR CATEGORICAL DATA:
- Bar chart: For comparing categories (categorical vs numerical)
- Pie chart: For showing proportions of categories (use sparingly)
- Count plot: For frequency of categories
- Donut chart: Alternative to pie charts

FOR MIXED DATA:
- Box plot: Numerical distribution across categories (already auto-generated)
- Violin plot: Detailed distribution across categories
- Swarm plot: Individual data points across categories

For each suggestion, provide JSON with: type, x, y, reason

Examples:
For numerical analysis: {{"type": "histogram", "x": "age", "reason": "Distribution analysis"}}
For categorical: {{"type": "bar", "x": "category", "y": "sales", "reason": "Comparison across categories"}}

"""
    
    def _build_summary_prompt(self, graph_type: str, x_col: str, y_col: str, graph_description: str, data_stats: Dict = None) -> str:
        """Build graph-specific prompts for accurate insights."""
        
        # Graph-specific prompt templates (scatter removed)
        prompt_templates = {
            'histogram': """
Analyze this histogram showing distribution of {x}.

Visual Description:
{desc}

{stats}

Focus on:
- Shape of distribution (normal, skewed, bimodal)
- Data range and spread
- Peaks and valleys in the distribution
- Any gaps or unusual patterns

Provide 2-3 factual sentences about the data distribution.
""",
            'bar': """
Analyze this bar chart comparing {y} across categories of {x}.

Visual Description:
{desc}

{stats}

Focus on:
- Which categories have highest/lowest values
- Overall pattern across categories
- Any significant differences between bars
- The scale and range of values

Provide 2-3 factual sentences about the comparisons shown.
""",
            'line': """
Analyze this line chart showing {y} over {x}.

Visual Description:
{desc}

{stats}

Focus on:
- Overall trend (increasing, decreasing, fluctuating)
- Any peaks, troughs, or patterns
- Steepness of changes
- Consistency of the trend

Provide 2-3 factual sentences about the trend shown.
""",
            'pie': """
Analyze this pie chart showing distribution of {x}.

Visual Description:
{desc}

{stats}

Focus on:
- Largest and smallest segments
- Overall balance of categories
- Any dominant categories
- The proportion representation

Provide 2-3 factual sentences about the proportional distribution.
""",
            'box': """
Analyze this box plot showing distribution of {x}.

Visual Description:
{desc}

{stats}

Focus on:
- Median position and spread
- Presence of outliers
- Symmetry of the distribution
- Data range and quartiles

Provide 2-3 factual sentences about the distribution characteristics.
""",
            'heatmap': """
Analyze this correlation heatmap.

Visual Description:
{desc}

{stats}

Focus on:
- Strongest positive/negative correlations
- Patterns in the correlation matrix
- Any unexpected correlations
- Overall correlation strength

Provide 2-3 factual sentences about the correlation patterns.
""",
            'violin': """
Analyze this violin plot showing distribution of {y} across {x}.

Visual Description:
{desc}

{stats}

Focus on:
- Distribution shape across categories
- Data density and spread
- Comparison between categories
- Any multimodal distributions

Provide 2-3 factual sentences about the distribution patterns.
"""
        }
        
        # Get the appropriate template or use default
        template = prompt_templates.get(graph_type, """
Analyze this {type} chart showing {x}{y}.

Visual Description:
{desc}

{stats}

Provide 2-3 factual sentences about what the chart displays.
""")
        
        # Prepare data stats
        stats_text = ""
        if data_stats:
            if 'x_stats' in data_stats:
                stats_text += f"X-axis statistics: {data_stats['x_stats']}\n"
            if 'y_stats' in data_stats:
                stats_text += f"Y-axis statistics: {data_stats['y_stats']}\n"
        
        return template.format(
            type=graph_type,
            x=x_col,
            y=f" and {y_col}" if y_col else "",
            desc=graph_description,
            stats=stats_text
        )
    
    def _get_ai_response(self, prompt: str, max_tokens: int = 200) -> str:
        """Get response from OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a data analyst providing accurate, factual insights based only on what the visualization shows. Be specific and avoid generalizations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3  # Low temperature for factual responses
            )
            result = response.choices[0].message.content.strip()
            
            # Validate response
            if len(result) < 20 or "sorry" in result.lower() or "error" in result.lower():
                return self.get_fallback_insights(
                    self._extract_graph_type(prompt),
                    self._extract_column(prompt, 'x'),
                    self._extract_column(prompt, 'y')
                )
            
            return result
            
        except Exception as e:
            return self.get_fallback_insights('chart', 'data', None)
    
    def _extract_graph_type(self, prompt: str) -> str:
        """Extract graph type from prompt."""
        for graph_type in ['histogram', 'bar', 'line', 'pie', 'box', 'heatmap', 'violin']:
            if graph_type in prompt.lower():
                return graph_type
        return 'chart'
    
    def _extract_column(self, prompt: str, axis: str) -> str:
        """Extract column name from prompt."""
        import re
        pattern = f"{axis.upper()}-axis \\(([^)]+)\\)"
        match = re.search(pattern, prompt)
        return match.group(1) if match else 'data'
    
    def _parse_ai_response(self, response: str, columns: List[Dict[str, str]]) -> List[Dict]:
        """Parse the AI response with validation against actual columns."""
        try:
            # Extract JSON from response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            suggestions = json.loads(response)
            
            # Filter out heatmap, box plots, and scatter plots
            filtered_suggestions = [
                s for s in suggestions 
                if s.get('type') not in ['heatmap', 'box', 'scatter']
            ]
            
            # Validate that suggested columns exist in the dataset
            valid_suggestions = []
            column_names = [col['name'] for col in columns]
            
            for suggestion in filtered_suggestions:
                # Check x column exists
                if suggestion.get('x') not in column_names:
                    continue
                
                # Check y column exists if specified
                if suggestion.get('y') and suggestion.get('y') not in column_names:
                    continue
                
                valid_suggestions.append(suggestion)
                
                # Limit to 5 suggestions
                if len(valid_suggestions) >= 5:
                    break
            
            return valid_suggestions
            
        except json.JSONDecodeError:
            # Fallback to reasonable suggestions based on column types (no scatter)
            return self._generate_fallback_suggestions(columns)
    
    def _generate_fallback_suggestions(self, columns: List[Dict[str, str]]) -> List[Dict]:
        """Generate fallback suggestions based on column types (no scatter plots)."""
        numerical_cols = [col['name'] for col in columns if col['type'] == 'numerical']
        categorical_cols = [col['name'] for col in columns if col['type'] == 'categorical']
        
        suggestions = []
        
        # Single Numerical: Histogram
        if numerical_cols:
            suggestions.append({
                "type": "histogram",
                "x": numerical_cols[0],
                "reason": "Distribution of numerical variable"
            })
        
        # Categorical vs Numerical: Bar chart
        if categorical_cols and numerical_cols:
            suggestions.append({
                "type": "bar",
                "x": categorical_cols[0],
                "y": numerical_cols[0],
                "reason": "Comparison across categories"
            })
        
        # Single Categorical: Count plot (as bar chart)
        if categorical_cols:
            suggestions.append({
                "type": "bar",
                "x": categorical_cols[0],
                "reason": "Frequency of categories"
            })
        
        # Line chart for ordered data
        if len(numerical_cols) >= 2:
            suggestions.append({
                "type": "line",
                "x": numerical_cols[0],
                "y": numerical_cols[1],
                "reason": "Trend analysis"
            })
        
        # Additional histogram if multiple numerical columns
        if len(numerical_cols) >= 2:
            suggestions.append({
                "type": "histogram",
                "x": numerical_cols[1],
                "reason": "Additional distribution analysis"
            })
        
        return suggestions[:5]  # Return max 5 suggestions
    
    def get_fallback_insights(self, graph_type: str, x_col: str, y_col: str) -> str:
        """Provide simple, accurate fallback insights."""
        insights = {
            'histogram': f"The histogram displays the distribution of {x_col}. The bars show the frequency of data points within specific value ranges.",
            'bar': f"The bar chart compares values across different categories of {x_col}. The height of each bar represents the measured quantity.",
            'line': f"The line chart shows how the values change across the range of {x_col}. The line connects data points to display trends or patterns.",
            'pie': f"The pie chart shows the proportional distribution of categories in {x_col}. Each segment represents a category's share of the total.",
            'box': f"The box plot displays the statistical distribution of {x_col}, showing median, quartiles, and potential outliers.",
            'heatmap': "The heatmap visualizes correlations between variables, with color intensity representing the strength of relationship.",
            'violin': f"The violin plot shows the distribution of {y_col} across different categories of {x_col}, combining box plot and density plot features."
        }
        
        return insights.get(graph_type, f"This {graph_type} chart displays data visualization for analysis.")