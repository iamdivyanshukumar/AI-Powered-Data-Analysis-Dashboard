from typing import Dict, Any, List, Optional
import json
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

from .base_agent import BaseAgent, AgentConfig
from app.core.logger import log_agent_operation

class StorytellerAgent(BaseAgent):
    """
    Storyteller Agent - Creates narrative insights from data analysis
    """
    
    def __init__(self, 
                 config: AgentConfig = None,
                 session_id: str = None):
        """
        Initialize Storyteller Agent
        
        Args:
            config: Agent configuration
            session_id: Session identifier
        """
        super().__init__(
            name="Storyteller",
            description="Creates narrative insights and business stories from data",
            config=config or AgentConfig(model="gpt-4", temperature=0.3),
            session_id=session_id
        )
        
        # Narrative templates
        self.narrative_templates = {
            'executive_summary': self._create_executive_summary,
            'business_insights': self._create_business_insights,
            'data_story': self._create_data_story,
            'recommendations': self._create_recommendations
        }
        
        logger.info("Storyteller agent initialized")
    
    @log_agent_operation
    async def execute(self, 
                     input_data: Dict[str, Any],
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create narrative insights from data
        
        Args:
            input_data: Must contain 'dataframe_twin'
            context: Additional context
            
        Returns:
            Narrative insights
        """
        # Validate input
        if not self.validate_input(input_data, ['dataframe_twin']):
            return self.create_response(
                success=False,
                error="Missing required 'dataframe_twin' in input"
            )
        
        text_twin = input_data['dataframe_twin']
        narrative_type = input_data.get('narrative_type', 'executive_summary')
        user_context = input_data.get('user_context', '')
        audience = input_data.get('audience', 'business_stakeholders')
        
        # Check if narrative type is supported
        if narrative_type not in self.narrative_templates:
            return self.create_response(
                success=False,
                error=f"Unsupported narrative type: {narrative_type}. "
                      f"Supported: {list(self.narrative_templates.keys())}"
            )
        
        try:
            # Extract key information from twin
            metadata = text_twin.get('metadata', {})
            statistics = text_twin.get('statistics', {})
            insights = text_twin.get('insights', [])
            
            # Create narrative context
            narrative_context = self._create_narrative_context(
                metadata, statistics, insights, user_context, audience
            )
            
            # Generate narrative
            narrative_func = self.narrative_templates[narrative_type]
            narrative = await narrative_func(narrative_context)
            
            # Format based on audience
            formatted_narrative = self._format_for_audience(narrative, audience)
            
            # Prepare response
            result = {
                'narrative': formatted_narrative,
                'metadata': {
                    'narrative_type': narrative_type,
                    'audience': audience,
                    'dataframe_shape': metadata.get('shape', []),
                    'timestamp': datetime.now().isoformat()
                },
                'key_points': self._extract_key_points(formatted_narrative),
                'actionable_items': self._extract_actionable_items(formatted_narrative)
            }
            
            return self.create_response(
                success=True,
                data=result
            )
            
        except Exception as e:
            self.logger.log_error(
                error_type="storytelling",
                error_message=str(e),
                context={'narrative_type': narrative_type, 'audience': audience}
            )
            
            return self.create_response(
                success=False,
                error=f"Storytelling failed: {str(e)}"
            )
    
    async def _create_executive_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create executive summary narrative"""
        prompt = self._build_executive_summary_prompt(context)
        
        try:
            response = await self.call_llm(
                prompt=prompt,
                system_prompt="You are a data storytelling expert creating executive summaries for business leaders."
            )
            
            # Parse structured response
            narrative = self._parse_llm_response(response)
            
            return {
                'title': 'Executive Summary',
                'content': narrative,
                'sections': ['Overview', 'Key Findings', 'Implications', 'Next Steps'],
                'tone': 'professional',
                'length': 'brief'
            }
            
        except Exception as e:
            return self._create_fallback_summary(context)
    
    async def _create_business_insights(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create business insights narrative"""
        prompt = self._build_business_insights_prompt(context)
        
        try:
            response = await self.call_llm(
                prompt=prompt,
                system_prompt="You are a business analyst extracting actionable insights from data."
            )
            
            narrative = self._parse_llm_response(response)
            
            return {
                'title': 'Business Insights',
                'content': narrative,
                'sections': ['Market Insights', 'Customer Insights', 'Operational Insights', 'Financial Insights'],
                'tone': 'analytical',
                'length': 'detailed'
            }
            
        except Exception as e:
            return self._create_fallback_insights(context)
    
    async def _create_data_story(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create data story narrative"""
        prompt = self._build_data_story_prompt(context)
        
        try:
            response = await self.call_llm(
                prompt=prompt,
                system_prompt="You are a data journalist telling compelling stories from data.",
                temperature=0.7  # More creative
            )
            
            narrative = self._parse_llm_response(response)
            
            return {
                'title': 'Data Story',
                'content': narrative,
                'sections': ['Introduction', 'The Journey', 'Discoveries', 'Conclusion'],
                'tone': 'narrative',
                'length': 'medium'
            }
            
        except Exception as e:
            return self._create_fallback_story(context)
    
    async def _create_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create recommendations narrative"""
        prompt = self._build_recommendations_prompt(context)
        
        try:
            response = await self.call_llm(
                prompt=prompt,
                system_prompt="You are a strategic consultant providing data-driven recommendations."
            )
            
            narrative = self._parse_llm_response(response)
            
            return {
                'title': 'Strategic Recommendations',
                'content': narrative,
                'sections': ['Immediate Actions', 'Short-term Initiatives', 'Long-term Strategy', 'Risk Considerations'],
                'tone': 'prescriptive',
                'length': 'actionable'
            }
            
        except Exception as e:
            return self._create_fallback_recommendations(context)
    
    def _create_narrative_context(self,
                                 metadata: Dict[str, Any],
                                 statistics: Dict[str, Any],
                                 insights: List[str],
                                 user_context: str,
                                 audience: str) -> Dict[str, Any]:
        """Create context for narrative generation"""
        # Extract key statistics
        basic_stats = statistics.get('basic', {})
        numerical_stats = statistics.get('numerical', {})
        categorical_stats = statistics.get('categorical', {})
        
        # Identify notable patterns
        notable_patterns = []
        
        # Check correlations
        correlations = statistics.get('correlations', [])
        strong_corrs = [c for c in correlations if abs(c.get('correlation', 0)) > 0.7]
        if strong_corrs:
            notable_patterns.append({
                'type': 'strong_correlation',
                'count': len(strong_corrs),
                'example': strong_corrs[0] if strong_corrs else None
            })
        
        # Check data quality
        missing_pct = basic_stats.get('missing_percentage', 0)
        if missing_pct > 5:
            notable_patterns.append({
                'type': 'missing_data',
                'percentage': missing_pct,
                'severity': 'high' if missing_pct > 20 else 'medium'
            })
        
        # Check distributions
        for col, stats in numerical_stats.items():
            skewness = stats.get('skewness', 0)
            if abs(skewness) > 1:
                notable_patterns.append({
                    'type': 'skewed_distribution',
                    'column': col,
                    'skewness': skewness,
                    'direction': 'right' if skewness > 0 else 'left'
                })
        
        context = {
            'dataset_info': {
                'name': metadata.get('filename', 'Dataset'),
                'size': f"{metadata.get('shape', [0, 0])[0]:,} rows × {metadata.get('shape', [0, 0])[1]} columns",
                'columns': metadata.get('columns', []),
                'numerical_columns': len(metadata.get('numerical_cols', [])),
                'categorical_columns': len(metadata.get('categorical_cols', []))
            },
            'key_statistics': {
                'missing_data': f"{missing_pct:.1f}%",
                'duplicate_rows': f"{basic_stats.get('duplicate_percentage', 0):.1f}%",
                'memory_usage': f"{basic_stats.get('memory_usage_mb', 0):.1f} MB",
                'data_completeness': f"{100 - missing_pct:.1f}%"
            },
            'notable_patterns': notable_patterns,
            'auto_insights': insights,
            'user_context': user_context,
            'audience': audience,
            'timestamp': datetime.now().strftime('%B %d, %Y')
        }
        
        return context
    
    def _build_executive_summary_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for executive summary"""
        dataset_info = context['dataset_info']
        key_stats = context['key_statistics']
        notable_patterns = context['notable_patterns']
        user_context = context['user_context']
        
        prompt = f"""
        Create an executive summary for business leaders based on this data analysis:
        
        DATASET: {dataset_info['name']}
        SIZE: {dataset_info['size']}
        COLUMNS: {len(dataset_info['columns'])} total ({dataset_info['numerical_columns']} numerical, {dataset_info['categorical_columns']} categorical)
        
        KEY STATISTICS:
        - Data Completeness: {key_stats['data_completeness']}
        - Missing Data: {key_stats['missing_data']}
        - Duplicate Rows: {key_stats['duplicate_rows']}
        
        NOTABLE PATTERNS:
        {json.dumps(notable_patterns, indent=2)}
        
        USER CONTEXT: {user_context if user_context else 'General analysis requested'}
        
        Create a concise executive summary (3-4 paragraphs) with:
        1. Overview of what the data represents
        2. Most significant findings
        3. Business implications
        4. Recommended next steps
        
        Write in professional, non-technical language suitable for C-level executives.
        Focus on business impact rather than technical details.
        """
        
        return prompt
    
    def _build_business_insights_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for business insights"""
        dataset_info = context['dataset_info']
        notable_patterns = context['notable_patterns']
        auto_insights = context['auto_insights']
        user_context = context['user_context']
        
        prompt = f"""
        Extract business insights from this data analysis:
        
        DATASET: {dataset_info['name']}
        SIZE: {dataset_info['size']}
        
        AUTO-GENERATED INSIGHTS:
        {chr(10).join(f'- {insight}' for insight in auto_insights)}
        
        NOTABLE DATA PATTERNS:
        {json.dumps(notable_patterns, indent=2)}
        
        USER CONTEXT: {user_context if user_context else 'General business analysis'}
        
        Provide business insights in these categories:
        
        1. MARKET INSIGHTS: What does this data reveal about the market or industry?
        2. CUSTOMER INSIGHTS: What patterns relate to customers or users?
        3. OPERATIONAL INSIGHTS: What efficiencies or inefficiencies are apparent?
        4. FINANCIAL INSIGHTS: What monetary implications or opportunities exist?
        5. RISK INSIGHTS: What risks or challenges are indicated?
        
        For each insight, include:
        - The observation (what the data shows)
        - The implication (why it matters)
        - Potential action (what could be done)
        
        Focus on actionable, data-driven insights.
        """
        
        return prompt
    
    def _build_data_story_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for data story"""
        dataset_info = context['dataset_info']
        notable_patterns = context['notable_patterns']
        user_context = context['user_context']
        
        prompt = f"""
        Tell a compelling story based on this data analysis:
        
        DATASET: {dataset_info['name']}
        STORY CONTEXT: {user_context if user_context else 'Discovering patterns in the data'}
        
        KEY ELEMENTS:
        - Dataset size: {dataset_info['size']}
        - Column types: {dataset_info['numerical_columns']} numerical, {dataset_info['categorical_columns']} categorical
        - Notable patterns: {len(notable_patterns)} significant findings
        
        Create a narrative that includes:
        
        1. INTRODUCTION: Set the scene - what journey are we about to take?
        2. THE QUEST: Describe the exploration process
        3. DISCOVERIES: Reveal the key findings as plot points
        4. TWISTS: Highlight surprising or counterintuitive patterns
        5. RESOLUTION: What does it all mean?
        6. EPILOGUE: What questions remain or what comes next?
        
        Write in an engaging, narrative style. Use metaphors and storytelling techniques.
        Make the data come alive as characters in a story.
        """
        
        return prompt
    
    def _build_recommendations_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for recommendations"""
        dataset_info = context['dataset_info']
        key_stats = context['key_statistics']
        notable_patterns = context['notable_patterns']
        user_context = context['user_context']
        
        prompt = f"""
        Provide strategic recommendations based on this data analysis:
        
        DATASET: {dataset_info['name']}
        ANALYSIS CONTEXT: {user_context if user_context else 'Comprehensive data analysis'}
        
        CURRENT STATE:
        - Data Quality: {key_stats['data_completeness']} completeness
        - Issues: {key_stats['missing_data']} missing data, {key_stats['duplicate_rows']} duplicates
        
        KEY FINDINGS:
        {json.dumps(notable_patterns, indent=2)}
        
        Create strategic recommendations in these timeframes:
        
        IMMEDIATE ACTIONS (Next 30 days):
        - Data quality improvements
        - Quick wins or fixes
        - Critical issues to address
        
        SHORT-TERM INITIATIVES (Next 3-6 months):
        - Process improvements
        - Additional analysis needed
        - Team or resource recommendations
        
        LONG-TERM STRATEGY (6+ months):
        - Strategic opportunities
        - System or process changes
        - Innovation possibilities
        
        RISK CONSIDERATIONS:
        - Data-related risks
        - Implementation risks
        - Opportunity costs
        
        For each recommendation, include:
        - The recommendation
        - Rationale (why it's important)
        - Expected impact
        - Resources needed
        - Success metrics
        
        Prioritize recommendations based on impact and feasibility.
        """
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        try:
            # Try to parse as JSON first
            if response.strip().startswith('{') or response.strip().startswith('['):
                return json.loads(response)
            
            # Otherwise, structure as narrative
            sections = response.split('\n\n')
            structured = {}
            
            current_section = None
            for section in sections:
                if section.strip() and ':' in section and len(section) < 100:
                    # This might be a section header
                    current_section = section.split(':')[0].strip().lower().replace(' ', '_')
                    structured[current_section] = section.split(':', 1)[1].strip()
                elif current_section:
                    # Add to current section
                    structured[current_section] += '\n\n' + section
                else:
                    # Default section
                    structured['content'] = section
            
            return structured
            
        except json.JSONDecodeError:
            # Return as plain text
            return {'narrative': response}
    
    def _format_for_audience(self, narrative: Dict[str, Any], audience: str) -> Dict[str, Any]:
        """Format narrative for specific audience"""
        formatted = narrative.copy()
        
        if audience == 'executive':
            # Simplify and focus on business impact
            if 'content' in formatted:
                # Summarize if too long
                content = formatted['content']
                if len(content) > 1000:
                    sentences = content.split('. ')
                    formatted['content'] = '. '.join(sentences[:5]) + '.'
            
            formatted['tone'] = 'strategic'
            formatted['detail_level'] = 'high-level'
            
        elif audience == 'technical':
            # Add technical details
            formatted['tone'] = 'analytical'
            formatted['detail_level'] = 'detailed'
            if 'technical_notes' not in formatted:
                formatted['technical_notes'] = 'Analysis based on statistical patterns and data quality assessment.'
            
        elif audience == 'general':
            # Simplify language
            formatted['tone'] = 'accessible'
            formatted['detail_level'] = 'simplified'
            # Could add glossary or explanations
            
        return formatted
    
    def _extract_key_points(self, narrative: Dict[str, Any]) -> List[str]:
        """Extract key points from narrative"""
        key_points = []
        
        # Extract from content
        if 'content' in narrative:
            content = narrative['content']
            sentences = [s.strip() for s in content.split('. ') if s.strip()]
            # Take first 3-5 meaningful sentences
            key_points.extend(sentences[:5])
        
        # Extract from sections
        for key, value in narrative.items():
            if key not in ['content', 'title', 'tone', 'length'] and isinstance(value, str):
                if len(value) < 200:  # Short enough to be a key point
                    key_points.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return key_points[:10]  # Limit to 10 key points
    
    def _extract_actionable_items(self, narrative: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract actionable items from narrative"""
        actionable_items = []
        
        # Look for action-oriented language
        action_verbs = ['recommend', 'suggest', 'should', 'must', 'need to', 'consider', 'implement', 'create', 'develop']
        
        content = narrative.get('content', '') + ' ' + ' '.join(str(v) for v in narrative.values() if isinstance(v, str))
        
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        
        for sentence in sentences:
            if any(verb in sentence.lower() for verb in action_verbs):
                # Extract the action
                actionable_items.append({
                    'action': sentence,
                    'priority': 'medium',  # Could be enhanced with priority detection
                    'category': self._categorize_action(sentence)
                })
        
        return actionable_items[:5]  # Limit to 5 actionable items
    
    def _categorize_action(self, sentence: str) -> str:
        """Categorize actionable item"""
        sentence_lower = sentence.lower()
        
        if any(word in sentence_lower for word in ['data', 'analysis', 'model', 'algorithm']):
            return 'data_analysis'
        elif any(word in sentence_lower for word in ['business', 'strategy', 'market', 'customer']):
            return 'business_strategy'
        elif any(word in sentence_lower for word in ['process', 'operation', 'efficiency', 'workflow']):
            return 'operations'
        elif any(word in sentence_lower for word in ['risk', 'security', 'compliance', 'audit']):
            return 'risk_management'
        else:
            return 'general'
    
    # Fallback methods in case LLM fails
    def _create_fallback_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback executive summary"""
        dataset_info = context['dataset_info']
        key_stats = context['key_statistics']
        
        return {
            'title': 'Executive Summary',
            'content': f"""
            This analysis of the {dataset_info['name']} dataset ({dataset_info['size']}) reveals important patterns and insights. 
            The data shows {key_stats['data_completeness']} completeness with {key_stats['missing_data']} missing values.
            
            Key findings indicate several notable patterns in the data that warrant further investigation. 
            The analysis provides a foundation for data-driven decision making.
            
            Recommended next steps include addressing data quality issues and exploring the identified patterns in depth.
            """,
            'sections': ['Overview', 'Findings', 'Recommendations'],
            'tone': 'professional',
            'length': 'brief'
        }
    
    def _create_fallback_insights(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback business insights"""
        return {
            'title': 'Business Insights',
            'content': """
            1. MARKET INSIGHTS: The data reveals patterns that could indicate market trends or opportunities.
            2. CUSTOMER INSIGHTS: Customer behavior patterns suggest areas for engagement improvement.
            3. OPERATIONAL INSIGHTS: Efficiency opportunities exist in current processes.
            4. FINANCIAL INSIGHTS: Data patterns may indicate revenue opportunities or cost savings.
            """,
            'sections': ['Market', 'Customer', 'Operations', 'Financial'],
            'tone': 'analytical',
            'length': 'medium'
        }
    
    def _create_fallback_story(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback data story"""
        return {
            'title': 'The Data Journey',
            'content': """
            Our journey through this dataset began with curiosity about what patterns might emerge.
            As we explored, we discovered unexpected relationships and surprising distributions.
            
            Each finding told part of a larger story about the underlying processes and relationships.
            The data revealed both expected patterns and surprising anomalies.
            
            This story continues as we apply these insights to drive better decisions and outcomes.
            """,
            'sections': ['Beginning', 'Discovery', 'Revelation', 'Continuation'],
            'tone': 'narrative',
            'length': 'medium'
        }
    
    def _create_fallback_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback recommendations"""
        return {
            'title': 'Strategic Recommendations',
            'content': """
            IMMEDIATE ACTIONS:
            1. Address data quality issues identified in the analysis
            2. Share key findings with relevant stakeholders
            
            SHORT-TERM INITIATIVES:
            1. Conduct deeper analysis on the most significant patterns
            2. Implement monitoring for key data quality metrics
            
            LONG-TERM STRATEGY:
            1. Establish regular data review processes
            2. Integrate insights into decision-making frameworks
            """,
            'sections': ['Immediate', 'Short-term', 'Long-term'],
            'tone': 'prescriptive',
            'length': 'actionable'
        }