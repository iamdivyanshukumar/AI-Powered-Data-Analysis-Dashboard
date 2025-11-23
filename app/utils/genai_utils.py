from openai import OpenAI
import json
from typing import List, Dict, Any
from app.config import Config
import logging
import re

logger = logging.getLogger(__name__)

class GenAIAnalyzer:
    """Enhanced GenAI analyzer with better readability and more context."""
    
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def get_visualization_suggestions(self, smart_context: Dict[str, Any]) -> List[Dict]:
        """Get AI-powered visualization suggestions using enhanced context."""
        prompt = self._build_smart_suggestion_prompt(smart_context)
        response = self._get_ai_response(prompt, max_tokens=400)
        return self._parse_ai_response(response, smart_context)
    
    def get_comprehensive_analysis(self, smart_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive AI analysis with better formatting."""
        prompt = self._build_comprehensive_analysis_prompt(smart_context)
        response = self._get_ai_response(prompt, max_tokens=800) # Increased tokens for deeper analysis
        return self._parse_comprehensive_analysis(response)
    
    def get_graph_summary(self, graph_type: str, x_col: str, y_col: str, 
                         graph_description: str, data_stats: Dict = None) -> str:
        """Generate concise natural language summary for a generated graph."""
        prompt = self._build_summary_prompt(graph_type, x_col, y_col, graph_description, data_stats)
        return self._get_ai_response(prompt, max_tokens=200)
    
    def get_data_quality_insights(self, smart_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get automated data quality assessment."""
        prompt = self._build_data_quality_prompt(smart_context)
        response = self._get_ai_response(prompt, max_tokens=400)
        return self._parse_data_quality_analysis(response)
    
    def _build_smart_suggestion_prompt(self, smart_context: Dict[str, Any]) -> str:
        # (Same as before, simplified for brevity in this partner response)
        # ... [Keep your existing _build_smart_suggestion_prompt code] ...
        metadata = smart_context.get('metadata', {})
        exposed_samples = smart_context.get('exposed_samples', {})
        summary_stats = smart_context.get('summary_statistics', {})
        
        context_desc = f"""
DATASET OVERVIEW:
- Total Rows: {metadata.get('total_rows', 'N/A')} | Columns: {metadata.get('total_columns', 'N/A')}
- Numerical Columns: {len(metadata.get('numerical_cols', []))}
- Categorical Columns: {len(metadata.get('categorical_cols', []))}
- Missing Values: {metadata.get('missing_values', 0)}

COLUMN SUMMARY:
"""
        for col in metadata.get('columns', [])[:10]:
            context_desc += f"- {col}\n"
        
        context_desc += f"\nEXTENSIVE DATA SAMPLES ({len(exposed_samples.get('all_samples', []))} rows):\n"
        all_samples = exposed_samples.get('all_samples', [])
        for i, sample in enumerate(all_samples[:12]):
            clean_sample = {k: v for k, v in sample.items() if not k.startswith('_')}
            context_desc += f"Sample {i+1}: {clean_sample}\n"
        
        prompt = f"""
As an expert data analyst, analyze this dataset comprehensively and suggest the most valuable visualizations.

{context_desc}

Based on this extensive sample data and statistics, suggest 4-6 visualization types that would provide the most insights.

CRITICAL CONSTRAINTS:
1. NEVER suggest: heatmap, box, scatter, or line plots (these are auto-generated)
2. Focus on patterns visible in the extensive samples provided
3. Consider relationships between columns visible in the data

AVAILABLE VISUALIZATION TYPES:
- histogram: Distribution of single numerical variables
- bar: Comparisons between categories and numerical values  
- pie: Proportional relationships (use sparingly for top categories)
- violin: Detailed distribution analysis across categories
- density: Smooth distribution curves
- count: Frequency of categorical values

RESPONSE FORMAT - JSON array only:
[
  {{
    "type": "histogram",
    "x": "age",
    "y": null,
    "reason": "Analyze age distribution across the population"
  }}
]
Return ONLY valid JSON array.
"""
        return prompt
    
    def _build_comprehensive_analysis_prompt(self, smart_context: Dict[str, Any]) -> str:
        """
        Build enhanced prompt INCLUDING THE DETECTIVE REPORT.
        This is where the 'Text Twin' logic shines.
        """
        
        metadata = smart_context.get('metadata', {})
        exposed_samples = smart_context.get('exposed_samples', {})
        summary_stats = smart_context.get('summary_statistics', {})
        detective_report = smart_context.get('detective_report', {}) # NEW
        
        prompt = f"""
As a Senior Data Scientist, write a high-level Executive Summary for a non-technical stakeholder.
Do NOT just list stats. Tell a story about what the data means.

### 1. THE DETECTIVE REPORT (Mathematically Proven Findings)
Use these facts as the foundation of your analysis. Do not ignore them.
- STRONG CORRELATIONS FOUND: {json.dumps(detective_report.get('correlations', []), indent=2)}
- ANOMALIES DETECTED: {json.dumps(detective_report.get('anomalies', []), indent=2)}
- DOMINANT CATEGORIES: {json.dumps(detective_report.get('dominance', []), indent=2)}

### 2. DATA CONTEXT
- Size: {metadata.get('total_rows', 'N/A')} rows
- Columns: {metadata.get('columns', [])}

### 3. SAMPLES
{json.dumps(exposed_samples.get('all_samples', [])[:5], indent=2)}

Please provide a comprehensive analysis with these clear sections:

1. **EXECUTIVE SUMMARY**: A 3-sentence summary of the most important finding (likely from the Detective Report).
2. **KEY DRIVERS & PATTERNS**: Explain the correlations found. For example, if 'A' correlates with 'B', explain what that implies for the business/data.
3. **ANOMALIES & RISKS**: Discuss the outliers found in the Detective Report. Are they errors or interesting outliers?
4. **RECOMMENDATIONS**: What should the user do next based on this?

Format your response with clear section headers and bullet points.
"""
        return prompt
    
    def _build_data_quality_prompt(self, smart_context: Dict[str, Any]) -> str:
        """Build enhanced data quality prompt."""
        metadata = smart_context.get('metadata', {})
        summary_stats = smart_context.get('summary_statistics', {})
        
        prompt = f"""
As a data quality specialist, provide a detailed assessment of this dataset's quality.

DATASET CHARACTERISTICS:
- Dimensions: {metadata.get('shape', 'N/A')}
- Columns: {metadata.get('columns', [])}
- Missing Values: {metadata.get('missing_values', 0)} total
- Data Types: {len(metadata.get('numerical_cols', []))} numerical, {len(metadata.get('categorical_cols', []))} categorical

STATISTICAL PROFILE:
{json.dumps(summary_stats, indent=2)}

Please assess these quality dimensions with specific observations:

1. COMPLETENESS
   - Missing data patterns and impact
   - Column-level completeness scores

2. CONSISTENCY  
   - Data type consistency
   - Value range appropriateness
   - Categorical value patterns

3. VALIDITY
   - Reasonableness of numerical ranges
   - Categorical value validity
   - Outlier presence and impact

4. UNIQUENESS
   - Duplicate data indicators
   - Identifier column quality

5. OVERALL QUALITY SCORE & RECOMMENDATIONS
   - Overall assessment (Excellent/Good/Fair/Poor)
   - Specific improvement recommendations

Provide clear, actionable insights with confidence levels for each dimension.
"""
        return prompt
    
    def _build_summary_prompt(self, graph_type: str, x_col: str, y_col: str, 
                             graph_description: str, data_stats: Dict = None) -> str:
        """Build enhanced graph summary prompts."""
        
        # (Same templates as before)
        prompt_templates = {
            'histogram': """
Analyze this histogram visualization in detail:
CHART TYPE: Histogram
VARIABLE: {x}
{stats}
Please provide a comprehensive analysis covering:
• Distribution shape and characteristics
• Central tendency and spread
• Notable peaks, gaps, or patterns
""",
            'bar': """
Analyze this bar chart visualization in detail:
CHART TYPE: Bar Chart
CATEGORIES: {x}
VALUES: {y}
{stats}
Please provide a comprehensive analysis covering:
• Comparison between different categories
• Highest and lowest values
• Overall patterns or trends
"""
        }
        
        template = prompt_templates.get(graph_type, """
Analyze this visualization in detail:
CHART TYPE: {type}
VARIABLES: {x}{y}
{stats}
Please provide a comprehensive analysis covering the main patterns, trends, and insights visible in the chart.
""")
        
        stats_text = ""
        if data_stats:
            if 'x_stats' in data_stats:
                stats_text += f"STATISTICS: {data_stats['x_stats']}\n"
            if 'y_stats' in data_stats:
                stats_text += f"COMPARISON STATS: {data_stats['y_stats']}\n"
        
        return template.format(
            type=graph_type,
            x=x_col,
            y=f" vs {y_col}" if y_col else "",
            desc=graph_description,
            stats=stats_text
        )
    
    def _get_ai_response(self, prompt: str, max_tokens: int = 300) -> str:
        """Get response from OpenAI API with enhanced error handling."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise data analyst providing clear, structured, and factual insights. Use bullet points and clear section headers for readability."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.4
            )
            result = response.choices[0].message.content.strip()
            
            if len(result) < 25:
                return "Insufficient data for detailed analysis based on the provided samples."
            
            return result
            
        except Exception as e:
            logger.error(f"AI API error: {str(e)}")
            return f"Analysis temporarily unavailable. Error: {str(e)}"
    
    def _parse_ai_response(self, response: str, smart_context: Dict[str, Any]) -> List[Dict]:
        """Parse AI response with robust error handling."""
        try:
            logger.info(f"Raw AI response length: {len(response)}")
            
            cleaned_response = response.strip()
            if "```json" in cleaned_response:
                cleaned_response = cleaned_response.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_response:
                cleaned_response = cleaned_response.split("```")[1].split("```")[0].strip()
            
            start_idx = cleaned_response.find('[')
            end_idx = cleaned_response.rfind(']') + 1
            
            if start_idx != -1 and end_idx != 0:
                cleaned_response = cleaned_response[start_idx:end_idx]
            
            suggestions = json.loads(cleaned_response)
            
            if not isinstance(suggestions, list):
                return self._generate_fallback_suggestions(smart_context)
            
            valid_columns = smart_context.get('metadata', {}).get('columns', [])
            valid_suggestions = []
            
            for suggestion in suggestions:
                if not isinstance(suggestion, dict): continue
                if 'type' not in suggestion or 'x' not in suggestion: continue
                if suggestion.get('type') in ['heatmap', 'box', 'scatter', 'line']: continue
                if suggestion.get('x') not in valid_columns: continue
                if suggestion.get('y') and suggestion.get('y') not in valid_columns: continue
                valid_suggestions.append(suggestion)
            
            return valid_suggestions[:6]
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._generate_fallback_suggestions(smart_context)
    
    def _parse_comprehensive_analysis(self, response: str) -> Dict[str, Any]:
        try:
            cleaned_response = response.strip()
            sections = self._extract_analysis_sections(cleaned_response)
            return {"analysis": cleaned_response, "sections": sections, "formatted": True}
        except Exception as e:
            return {"analysis": response, "sections": ["full_analysis"], "formatted": False, "error": str(e)}
    
    def _parse_data_quality_analysis(self, response: str) -> Dict[str, Any]:
        try:
            return {
                "quality_report": response.strip(),
                "summary": self._extract_quality_summary(response),
                "formatted": True
            }
        except Exception as e:
            return {
                "quality_report": response,
                "summary": "Data quality assessment completed",
                "formatted": False
            }
    
    def _extract_analysis_sections(self, response: str) -> List[str]:
        sections = []
        lines = response.split('\n')
        current_section = ""
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Heuristics to find section headers (ALL CAPS, Numbered, etc.)
            if (line.endswith(':') or 
                re.match(r'^\d+\.\s+\*\*[A-Z]', line) or  # Matches "1. **HEADER"
                re.match(r'^\d+\.\s+[A-Z]', line) or      # Matches "1. HEADER"
                re.match(r'^\*\*[A-Z\s]+\*\*$', line) or  # Matches "**HEADER**"
                any(keyword in line.upper() for keyword in ['OVERVIEW', 'PATTERNS', 'INSIGHTS', 'RECOMMENDATIONS', 'QUALITY'])):
                
                if current_section:
                    sections.append(current_section)
                current_section = line
            elif current_section:
                current_section += "\n" + line
        
        if current_section:
            sections.append(current_section)
        
        return sections if sections else [response]
    
    def _extract_quality_summary(self, response: str) -> str:
        lines = response.split('\n')
        for line in lines[:8]:
            line = line.strip()
            if line and any(word in line.lower() for word in ['excellent', 'good', 'fair', 'poor', 'quality score', 'overall']):
                return line
        return "Comprehensive data quality assessment completed"
    
    def _generate_fallback_suggestions(self, smart_context: Dict[str, Any]) -> List[Dict]:
        # (Same as before)
        metadata = smart_context.get('metadata', {})
        numerical_cols = metadata.get('numerical_cols', [])
        categorical_cols = metadata.get('categorical_cols', [])
        suggestions = []
        for col in numerical_cols[:3]:
            suggestions.append({"type": "histogram", "x": col, "y": None, "reason": f"Analyze distribution of {col}"})
        return suggestions[:6]