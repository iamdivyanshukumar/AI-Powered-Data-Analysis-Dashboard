from openai import OpenAI
import json
from typing import List, Dict, Any
from app.config import Config
import logging
import re

logger = logging.getLogger(__name__)

class GenAIAnalyzer:
    """
    Enhanced GenAI analyzer acting as a Business Consultant.
    Focuses on 'Why' and 'So What', not just 'What'.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def get_visualization_suggestions(self, smart_context: Dict[str, Any]) -> List[Dict]:
        """Get AI-powered visualization suggestions."""
        prompt = self._build_smart_suggestion_prompt(smart_context)
        response = self._get_ai_response(prompt, max_tokens=400)
        return self._parse_ai_response(response, smart_context)
    
    def get_comprehensive_analysis(self, smart_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive AI analysis (Executive Summary)."""
        prompt = self._build_comprehensive_analysis_prompt(smart_context)
        response = self._get_ai_response(prompt, max_tokens=800)
        return self._parse_comprehensive_analysis(response)
    
    def get_graph_summary(self, graph_type: str, x_col: str, y_col: str, 
                         graph_description: str, data_stats: Dict = None) -> str:
        """Generate a 'Business Insight' summary for a graph."""
        prompt = self._build_summary_prompt(graph_type, x_col, y_col, graph_description, data_stats)
        return self._get_ai_response(prompt, max_tokens=250)
    
    def get_data_quality_insights(self, smart_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get automated data quality assessment."""
        prompt = self._build_data_quality_prompt(smart_context)
        response = self._get_ai_response(prompt, max_tokens=400)
        return self._parse_data_quality_analysis(response)
    
    # --- PROMPT BUILDERS ---

    def _build_summary_prompt(self, graph_type: str, x_col: str, y_col: str, 
                             graph_description: str, data_stats: Dict = None) -> str:
        """
        Builds the 'Translator' prompt.
        Switching persona from 'Analyst' to 'Business Consultant'.
        """
        base_prompt = f"""
        You are a Senior Business Intelligence Consultant presenting to a non-technical Client.
        
        THE VISUALIZATION:
        - Type: {graph_type.title()} Chart
        - Axis: {x_col} {f'vs {y_col}' if y_col else ''}
        - Context: {graph_description}
        
        THE DATA EVIDENCE (The Facts):
        """
        
        if data_stats:
            if 'x_stats' in data_stats:
                base_prompt += f"- {x_col} Stats: {data_stats['x_stats']}\n"
            if 'y_stats' in data_stats:
                base_prompt += f"- {y_col} Stats: {data_stats['y_stats']}\n"
        
        base_prompt += """
        YOUR TASK:
        Write a concise 3-bullet point insight summary.
        
        CRITICAL RULES FOR 'INSIGHTS':
        1. DO NOT just describe the chart (e.g. "The bar is high"). The user has eyes.
        2. EXPLAIN THE IMPLICATION (The "So What?").
           - Bad: "Sales are highest in December."
           - Good: "The December spike indicates strong seasonality, suggesting we should optimize inventory for Q4."
        3. Use simple, professional language. No jargon (like 'heteroscedasticity' or 'kurtosis').
        4. Be concise.
        
        FORMAT:
        • **Observation:** [What is the main pattern?]
        • **Driver:** [What likely caused this? e.g. outliers, dominance, trend]
        • **Action:** [One short recommendation based on this data]
        """
        
        return base_prompt

    def _build_smart_suggestion_prompt(self, smart_context: Dict[str, Any]) -> str:
        metadata = smart_context.get('metadata', {})
        exposed_samples = smart_context.get('exposed_samples', {})
        
        context_desc = f"""
DATASET OVERVIEW:
- Size: {metadata.get('total_rows', 'N/A')} rows
- Columns: {metadata.get('columns', [])}

SAMPLES:
{json.dumps(exposed_samples.get('all_samples', [])[:5], indent=2)}

Based on this data, suggest 4 visualization types that would provide the most BUSINESS insights.
CRITICAL: 
1. NEVER suggest: heatmap, box, scatter, or line plots (these are auto-generated).
2. Focus on 'histogram' or 'bar'.

RESPONSE FORMAT - JSON array only:
[
  {{
    "type": "bar", 
    "x": "CategoryColumn",
    "y": "ValueColumn",
    "reason": "Compare value across categories"
  }}
]
"""
        return context_desc

    def _build_comprehensive_analysis_prompt(self, smart_context: Dict[str, Any]) -> str:
        metadata = smart_context.get('metadata', {})
        detective_report = smart_context.get('detective_report', {})
        
        prompt = f"""
As a Senior Data Scientist, write a high-level Executive Summary for a non-technical stakeholder.

### 1. THE DETECTIVE REPORT (Mathematically Proven Findings)
- STRONG CORRELATIONS: {json.dumps(detective_report.get('correlations', []), indent=2)}
- ANOMALIES: {json.dumps(detective_report.get('anomalies', []), indent=2)}
- DOMINANCE: {json.dumps(detective_report.get('dominance', []), indent=2)}

### 2. DATA CONTEXT
- Size: {metadata.get('total_rows', 'N/A')} rows
- Columns: {metadata.get('columns', [])}

Please provide a comprehensive analysis with these clear sections:

1. **EXECUTIVE SUMMARY**: A 3-sentence summary of the most important finding (likely from the Detective Report).
2. **KEY DRIVERS & PATTERNS**: Explain the correlations found. Explain what that implies for the business.
3. **ANOMALIES & RISKS**: Discuss the outliers found in the Detective Report.
4. **RECOMMENDATIONS**: What should the user do next based on this?

Format your response with clear section headers and bullet points.
"""
        return prompt

    def _build_data_quality_prompt(self, smart_context: Dict[str, Any]) -> str:
        metadata = smart_context.get('metadata', {})
        stats = smart_context.get('summary_statistics', {})
        prompt = f"""
As a Data Quality Specialist, assess this dataset.
Metadata: {metadata}
Stats: {stats}

Provide a Quality Report with:
1. COMPLETENESS (Missing values?)
2. CONSISTENCY
3. VALIDITY
4. OVERALL SCORE (Excellent/Good/Fair/Poor)
"""
        return prompt

    def _get_ai_response(self, prompt: str, max_tokens: int = 300) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful, professional data analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.4
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI API error: {str(e)}")
            return f"Analysis unavailable: {str(e)}"

    def _parse_ai_response(self, response: str, smart_context: Dict[str, Any]) -> List[Dict]:
        try:
            # Clean JSON markdown
            cleaned = response.strip()
            if "```json" in cleaned: cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned: cleaned = cleaned.split("```")[1].split("```")[0]
            
            suggestions = json.loads(cleaned)
            if isinstance(suggestions, list):
                return suggestions[:4]
            return []
        except Exception:
            return []

    def _parse_comprehensive_analysis(self, response: str) -> Dict[str, Any]:
        # Simple passthrough for now, frontend handles markdown conversion
        return {"analysis": response, "formatted": True}

    def _parse_data_quality_analysis(self, response: str) -> Dict[str, Any]:
        return {"quality_report": response, "formatted": True}