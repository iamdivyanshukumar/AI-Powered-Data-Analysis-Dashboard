import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def generate_visualization(df: pd.DataFrame, graph_type: str, x_col: str, y_col: Optional[str] = None) -> str:
    """
    Generate visualization based on parameters with robust error handling.
    
    Args:
        df: Pandas DataFrame
        graph_type: Type of graph to generate
        x_col: Column for x-axis
        y_col: Column for y-axis (optional)
        
    Returns:
        HTML string of the generated visualization
    """
    # Validate input data
    if df.empty or x_col not in df.columns:
        return _generate_error_figure("Invalid data or columns")
    
    if y_col and y_col not in df.columns:
        return _generate_error_figure(f"Y-axis column '{y_col}' not found in data")

    try:
        # Clean data - convert strings to numeric where possible
        df = _clean_data(df, x_col, y_col)
        
        # Generate appropriate visualization
        fig = _create_figure(df, graph_type, x_col, y_col)
        
        # Customize layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=10)
        )
        
        return plot(fig, output_type='div', include_plotlyjs=False)
    
    except Exception as e:
        logger.error(f"Error generating visualization: {str(e)}", exc_info=True)
        return _generate_error_figure(f"Error generating visualization: {str(e)}")

def _clean_data(df: pd.DataFrame, x_col: str, y_col: Optional[str]) -> pd.DataFrame:
    """Clean and prepare data for visualization."""
    # Make a copy to avoid modifying original dataframe
    df = df.copy()
    
    # Convert to numeric if possible
    for col in [x_col, y_col]:
        if col and pd.api.types.is_string_dtype(df[col]):
            try:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except Exception:
                pass
    
    # Drop rows with NaN values in relevant columns
    cols_to_check = [x_col]
    if y_col:
        cols_to_check.append(y_col)
    df = df.dropna(subset=cols_to_check)
    
    return df

def _create_figure(df: pd.DataFrame, graph_type: str, x_col: str, y_col: Optional[str]) -> go.Figure:
    """Create the appropriate figure based on graph type."""
    if graph_type == 'scatter' and y_col:
        return px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
    elif graph_type == 'line' and y_col:
        return px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
    elif graph_type == 'bar' and y_col:
        return px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
    elif graph_type == 'histogram':
        return px.histogram(df, x=x_col, title=f"Distribution of {x_col}")
    elif graph_type == 'pie':
        return px.pie(df, names=x_col, title=f"Proportion of {x_col}")
    elif graph_type == 'box' and y_col:
        return px.box(df, x=x_col, y=y_col, title=f"Distribution of {y_col} by {x_col}")
    else:
        # Default to histogram if graph type not recognized
        return px.histogram(df, x=x_col, title=f"Distribution of {x_col}")

def _generate_error_figure(message: str) -> str:
    """Generate an error figure with the given message."""
    error_fig = go.Figure()
    error_fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="red")
    )
    error_fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    return plot(error_fig, output_type='div', include_plotlyjs=False)