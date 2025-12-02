import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.core.logger import AgentLogger
from .base_agent import BaseAgent, AgentConfig

class NotebookAgent(BaseAgent):
    """
    Notebook Agent - Generates interactive notebooks and processes notebook instructions using OpenAI.
    """

    def __init__(self, session_id=None):
        super().__init__(
            name="NotebookAgent",
            description="Generates and modifies notebooks using AI",
            config=AgentConfig(model="gpt-4o", temperature=0.2),
            session_id=session_id
        )

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute agent's main functionality.
        For NotebookAgent, this routes to either generation or instruction processing.
        """
        action = input_data.get('action')
        
        if action == 'generate_notebook':
            return await self.generate_initial_notebook(
                filename=input_data.get('filename'),
                analysis_type=input_data.get('analysis_type', 'comprehensive_eda'),
                dataframe_stats=input_data.get('dataframe_stats')
            )
        elif action == 'process_instruction':
            return await self.process_instruction(
                instruction=input_data.get('instruction'),
                dataframe_context=context
            )
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def _create_code_cell(self, source_lines):
        """Helper to create a standard code cell object."""
        # Ensure every line ends with a newline character for valid ipynb format
        formatted_source = [line if line.endswith('\n') else line + '\n' for line in source_lines]
        # Remove the newline from the very last line to be clean
        if formatted_source:
            formatted_source[-1] = formatted_source[-1].rstrip('\n')

        return {
            "id": str(uuid.uuid4()),
            "cell_type": "code",
            "source": formatted_source,
            "metadata": {},
            "outputs": []
        }

    def _create_markdown_cell(self, source_lines):
        """Helper to create a standard markdown cell object."""
        formatted_source = [line if line.endswith('\n') else line + '\n' for line in source_lines]
        return {
            "id": str(uuid.uuid4()),
            "cell_type": "markdown",
            "source": formatted_source,
            "metadata": {}
        }

    async def generate_initial_notebook(self, filename, analysis_type="comprehensive_eda", dataframe_stats=None):
        """
        Generates the starting notebook structure using LLM.
        """
        try:
            # Construct prompt for LLM
            prompt = f"""
            You are an expert Data Scientist. Generate a JSON structure for a Jupyter Notebook to perform a {analysis_type.replace('_', ' ')} on the dataset '{filename}'.
            
            The dataset has the following characteristics:
            {json.dumps(dataframe_stats, indent=2) if dataframe_stats else "No stats available"}
            
            Requirements:
            1. Create a logical flow: Introduction -> Setup -> Data Loading -> Basic Inspection -> Initial Visualizations.
            2. Use 'pandas', 'numpy', and 'plotly.express' for visualizations.
            3. The output MUST be a valid JSON object with a 'cells' key containing a list of cell objects.
            4. Each cell object must have 'cell_type' ('code' or 'markdown') and 'source' (list of strings).
            5. Do NOT include 'outputs' or 'execution_count' in the response.
            6. The dataframe is ALREADY LOADED as variable 'df'. Do NOT generate code to read the CSV file.
            7. Add comments in code cells to explain the steps.
            
            Response Format:
            {{
                "cells": [
                    {{ "cell_type": "markdown", "source": ["# Title", "Description"] }},
                    {{ "cell_type": "code", "source": ["import pandas as pd", "import plotly.express as px", "df.head()"] }}
                ]
            }}
            """

            # Call LLM
            response_text = await self.call_llm(prompt, system_prompt="You are a helpful AI data analysis assistant. Output ONLY valid JSON.")
            
            # Parse response
            try:
                # Clean markdown code blocks if present
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                    
                response_data = json.loads(response_text)
                cells_data = response_data.get('cells', [])
            except json.JSONDecodeError:
                self.logger.log_error("json_parse_error", "Failed to parse LLM response", {"response": response_text})
                # Fallback to basic template if parsing fails
                return self._generate_fallback_notebook(filename, analysis_type)

            # Convert to internal cell format (adding IDs, formatting source)
            final_cells = []
            for cell in cells_data:
                if cell['cell_type'] == 'code':
                    final_cells.append(self._create_code_cell(cell['source']))
                elif cell['cell_type'] == 'markdown':
                    final_cells.append(self._create_markdown_cell(cell['source']))

            # Construct Final Notebook Object
            notebook_structure = {
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3"
                    },
                    "language_info": {
                        "codemirror_mode": {"name": "ipython", "version": 3},
                        "file_extension": ".py",
                        "mimetype": "text/x-python",
                        "name": "python",
                        "nbconvert_exporter": "python",
                        "pygments_lexer": "ipython3",
                        "version": "3.8.5"
                    },
                    "analysis_type": analysis_type,
                    "generated_at": datetime.now().isoformat()
                },
                "nbformat": 4,
                "nbformat_minor": 4,
                "cells": final_cells
            }

            return {
                "success": True,
                "data": {
                    "notebook": notebook_structure,
                    "summary": {
                        "title": f"Analysis of {filename}",
                        "cell_count": len(final_cells)
                    }
                }
            }

        except Exception as e:
            self.logger.log_error("notebook_generation_error", str(e))
            return {"success": False, "error": str(e)}

    async def process_instruction(self, instruction, dataframe_context=None):
        """
        Generates code cells based on a natural language instruction and dataframe context.
        """
        try:
            prompt = f"""
            You are an expert Data Scientist. The user wants to perform the following action on their dataset:
            "{instruction}"
            
            Context about the dataset (Text Twin):
            {json.dumps(dataframe_context, indent=2) if dataframe_context else "No context available"}
            
            Requirements:
            1. Generate Python code using 'pandas' (assumed as 'df') and 'plotly.express' (assumed as 'px') to fulfill the request.
            2. If a visualization is requested, use Plotly.
            3. Provide a brief explanation of what the code does.
            4. Return a JSON object containing a list of 'proposed_code' blocks.
            
            Response Format:
            {{
                "proposed_code": [
                    {{
                        "code": "df.groupby('col').mean()",
                        "explanation": "Grouping by col and calculating mean.",
                        "confidence": 0.9
                    }}
                ]
            }}
            """
            
            response_text = await self.call_llm(prompt, system_prompt="You are a helpful AI data analysis assistant. Output ONLY valid JSON.")
            
            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                    
                response_data = json.loads(response_text)
                return {"success": True, "data": response_data}
            except json.JSONDecodeError:
                 return {"success": False, "error": "Failed to parse AI response"}

        except Exception as e:
            self.logger.log_error("instruction_processing_error", str(e))
            return {"success": False, "error": str(e)}

    def _generate_fallback_notebook(self, filename, analysis_type):
        """Fallback to template if LLM fails"""
        cells = []
        cells.append(self._create_markdown_cell([f"# {analysis_type}", f"Dataset: {filename}"]))
        cells.append(self._create_code_cell(["import pandas as pd", "import plotly.express as px", "# Dataframe is already loaded as 'df'", "df.head()"]))
        
        return {
            "success": True,
            "data": {
                "notebook": {
                    "cells": cells,
                    "metadata": {},
                    "nbformat": 4,
                    "nbformat_minor": 4
                }
            }
        }