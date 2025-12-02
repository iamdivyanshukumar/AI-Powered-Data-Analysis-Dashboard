import pandas as pd
import plotly.express as px
import plotly.io as pio
import os
import uuid
from flask import current_app
import logging
import numpy as np

logger = logging.getLogger(__name__)

def generate_visualization(df: pd.DataFrame, graph_type: str, x_column: str, y_column: str = None, modifier: str = None):
    """
    Generates an Interactive HTML graph using Plotly.
    """
    try:
        plot_df = df.copy()
        
        # --- CRITIC'S REFINEMENT LOGIC ---
        if modifier == 'top_10':
            if y_column and pd.api.types.is_numeric_dtype(plot_df[y_column]):
                plot_df = plot_df.groupby(x_column)[y_column].sum().nlargest(10).reset_index()
            else:
                top_counts = plot_df[x_column].value_counts().nlargest(10).index
                plot_df = plot_df[plot_df[x_column].isin(top_counts)]
        
        if modifier == 'sort_x':
            plot_df = plot_df.sort_values(by=x_column)
            
        if modifier == 'sample_1000' and len(plot_df) > 1000:
            plot_df = plot_df.sample(n=1000, random_state=42)

        # --- PLOTTING LOGIC ---
        fig = None
        description = ""

        if graph_type == 'bar':
            if y_column and pd.api.types.is_numeric_dtype(plot_df[y_column]):
                if not modifier and plot_df.duplicated(subset=[x_column]).any():
                    plot_df = plot_df.groupby(x_column)[y_column].sum().reset_index()
                fig = px.bar(plot_df, x=x_column, y=y_column, title=f"{y_column} by {x_column}")
            else:
                fig = px.histogram(plot_df, x=x_column, title=f"Count of {x_column}")

        elif graph_type == 'histogram':
            fig = px.histogram(plot_df, x=x_column, title=f"Distribution of {x_column}")

        elif graph_type == 'box':
            fig = px.box(plot_df, x=x_column, y=y_column if y_column else None, 
                         title=f"Box Plot of {x_column}")

        elif graph_type == 'scatter':
            if y_column:
                fig = px.scatter(plot_df, x=x_column, y=y_column, 
                               title=f"{x_column} vs {y_column}", trendline="ols" if len(plot_df) > 1 else None)
            else:
                return None, "Scatter plot requires Y column"

        elif graph_type == 'heatmap':
            numeric_df = plot_df.select_dtypes(include=['number'])
            if len(numeric_df.columns) > 1:
                corr = numeric_df.corr()
                fig = px.imshow(corr, text_auto=True, aspect="auto", title="Correlation Heatmap")
            else:
                return None, "Not enough numerical columns for heatmap"
                
        elif graph_type == 'line':
            if plot_df.duplicated(subset=[x_column]).any():
                 plot_df = plot_df.groupby(x_column)[y_column].mean().reset_index()
            fig = px.line(plot_df, x=x_column, y=y_column, title=f"Trend of {y_column} over {x_column}")

        else:
            return None, f"Unsupported graph type: {graph_type}"

        # --- STYLING (Clean & Modern) ---
        fig.update_layout(
            font=dict(family="Inter, sans-serif", size=12, color="#374151"),
            margin=dict(l=40, r=20, t=60, b=40),
            title_font_size=16,
            hoverlabel=dict(bgcolor="white", font_size=12),
            paper_bgcolor="white",
            plot_bgcolor="#f9fafb"
        )

        # --- SAVE AS INTERACTIVE HTML (The Fix) ---
        # We use HTML instead of PNG. This removes the Kaleido dependency completely.
        filename = f"{graph_type}_{uuid.uuid4().hex[:8]}.html"
        save_dir = os.path.join(current_app.root_path, 'static', 'visualizations')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        
        # include_plotlyjs='cdn' keeps the file size small by loading JS from the internet
        fig.write_html(save_path, include_plotlyjs='cdn', full_html=False)
        
        # Return relative path
        return f"static/visualizations/{filename}", f"Interactive {graph_type} chart for {x_column}"

    except Exception as e:
        logger.error(f"Viz Generation Error ({graph_type}): {str(e)}", exc_info=True)
        return None, str(e)