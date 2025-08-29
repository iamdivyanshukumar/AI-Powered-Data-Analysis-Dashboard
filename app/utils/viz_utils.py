# app/utils/viz_utils.py - UPDATED
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64
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
        Base64 encoded image string of the generated visualization
    """
    # Validate input data
    if df.empty or x_col not in df.columns:
        return _generate_error_image("Invalid data or columns")
    
    if y_col and y_col not in df.columns:
        return _generate_error_image(f"Y-axis column '{y_col}' not found in data")

    try:
        # Create the appropriate visualization
        fig = _create_figure(df, graph_type, x_col, y_col)
        
        # Convert to base64 for HTML embedding
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        return f"data:image/png;base64,{image_base64}"
    
    except Exception as e:
        logger.error(f"Error generating visualization: {str(e)}", exc_info=True)
        return _generate_error_image(f"Error generating visualization: {str(e)}")

def _create_figure(df: pd.DataFrame, graph_type: str, x_col: str, y_col: Optional[str]) -> plt.Figure:
    """Create the appropriate figure based on graph type."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    if graph_type == 'scatter' and y_col:
        ax.scatter(df[x_col], df[y_col])
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f"{y_col} vs {x_col}")
    elif graph_type == 'line' and y_col:
        ax.plot(df[x_col], df[y_col])
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f"{y_col} over {x_col}")
    elif graph_type == 'bar' and y_col:
        # For bar charts, we might need to aggregate if there are too many unique values
        if df[x_col].nunique() > 20:
            # Sample or bin the data
            sample_df = df.groupby(x_col)[y_col].mean().reset_index().head(20)
            ax.bar(sample_df[x_col].astype(str), sample_df[y_col])
        else:
            ax.bar(df[x_col].astype(str), df[y_col])
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f"{y_col} by {x_col}")
        plt.xticks(rotation=45)
    elif graph_type == 'histogram':
        ax.hist(df[x_col].dropna(), bins=20)
        ax.set_xlabel(x_col)
        ax.set_ylabel('Frequency')
        ax.set_title(f"Distribution of {x_col}")
    elif graph_type == 'box' and y_col:
        # For box plots, we might need to limit categories
        if df[x_col].nunique() > 10:
            # Get top 10 categories by count
            top_categories = df[x_col].value_counts().head(10).index
            filtered_df = df[df[x_col].isin(top_categories)]
            filtered_df.boxplot(column=y_col, by=x_col, ax=ax)
        else:
            df.boxplot(column=y_col, by=x_col, ax=ax)
        ax.set_title(f"Distribution of {y_col} by {x_col}")
        plt.xticks(rotation=45)
    else:
        # Default to histogram if graph type not recognized
        ax.hist(df[x_col].dropna(), bins=20)
        ax.set_xlabel(x_col)
        ax.set_ylabel('Frequency')
        ax.set_title(f"Distribution of {x_col}")
    
    return fig

def _generate_error_image(message: str) -> str:
    """Generate an error image with the given message."""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.text(0.5, 0.5, message, 
            horizontalalignment='center', 
            verticalalignment='center', 
            transform=ax.transAxes,
            fontsize=16,
            color='red')
    ax.set_axis_off()
    
    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    
    return f"data:image/png;base64,{image_base64}"