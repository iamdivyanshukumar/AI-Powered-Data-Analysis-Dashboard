import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io
import base64
import seaborn as sns
from typing import Optional, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

def generate_visualization(df: pd.DataFrame, graph_type: str, x_col: str, y_col: Optional[str] = None) -> Tuple[str, str]:
    """
    Generate visualization based on parameters with robust error handling.
    Returns both image and textual description.
    """
    # Validate input data
    if df.empty:
        return _generate_error_image("Empty dataset"), "Empty dataset - no data to visualize"
    
    # Handle special cases for essential visualizations
    if graph_type == "heatmap" and x_col == "all_numerical":
        return _generate_correlation_heatmap(df)
    elif graph_type == "box" and x_col == "all_numerical":
        return _generate_outlier_boxplots(df)
    
    if x_col not in df.columns and x_col != "all_numerical":
        return _generate_error_image(f"X-axis column '{x_col}' not found"), f"Error: X-axis column '{x_col}' not found in dataset"
    
    if y_col and y_col not in df.columns:
        return _generate_error_image(f"Y-axis column '{y_col}' not found"), f"Error: Y-axis column '{y_col}' not found in dataset"

    try:
        # Create the appropriate visualization
        fig, description = _create_figure_with_description(df, graph_type, x_col, y_col)
        
        # Convert to base64 for HTML embedding
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        return f"data:image/png;base64,{image_base64}", description
    
    except Exception as e:
        logger.error(f"Error generating visualization: {str(e)}", exc_info=True)
        return _generate_error_image(f"Error generating visualization: {str(e)}"), f"Error: {str(e)}"

def _create_figure_with_description(df: pd.DataFrame, graph_type: str, x_col: str, y_col: Optional[str]) -> Tuple[plt.Figure, str]:
    """Create figure and generate detailed textual description."""
    fig, ax = plt.subplots(figsize=(10, 7))
    description = ""
    
    if graph_type == 'histogram':
        ax.hist(df[x_col].dropna(), bins=30, alpha=0.7, edgecolor='black')
        ax.set_xlabel(x_col, fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title(f"Distribution of {x_col}", fontsize=14)
        ax.grid(True, alpha=0.3)
        
        # Histogram description
        stats = df[x_col].describe()
        skew = df[x_col].skew()
        description = f"Histogram of {x_col} with {len(df)} values. Range: {stats['min']:.1f}-{stats['max']:.1f}, "
        description += f"Mean: {stats['mean']:.1f}, Std: {stats['std']:.1f}. Skewness: {skew:.2f}."
        
    elif graph_type == 'bar' and y_col:
        # Bar chart with categorical x and numerical y
        if df[x_col].nunique() > 15:
            # Aggregate for too many categories
            top_categories = df[x_col].value_counts().head(15).index
            plot_df = df[df[x_col].isin(top_categories)]
            bar_data = plot_df.groupby(x_col)[y_col].mean().sort_values(ascending=False)
        else:
            bar_data = df.groupby(x_col)[y_col].mean().sort_values(ascending=False)
        
        ax.bar(range(len(bar_data)), bar_data.values)
        ax.set_xlabel(x_col, fontsize=12)
        ax.set_ylabel(y_col, fontsize=12)
        ax.set_title(f"{y_col} by {x_col}", fontsize=14)
        ax.set_xticks(range(len(bar_data)))
        ax.set_xticklabels(bar_data.index, rotation=45, ha='right')
        ax.grid(True, alpha=0.3)
        
        # Bar chart description
        description = f"Bar chart showing average {y_col} across {len(bar_data)} {x_col} categories. "
        description += f"Values range from {bar_data.min():.1f} to {bar_data.max():.1f}."
        
    elif graph_type == 'line' and y_col:
        # Line chart (assuming x is ordered)
        ax.plot(df[x_col], df[y_col], marker='o', markersize=3, linewidth=2)
        ax.set_xlabel(x_col, fontsize=12)
        ax.set_ylabel(y_col, fontsize=12)
        ax.set_title(f"{y_col} over {x_col}", fontsize=14)
        ax.grid(True, alpha=0.3)
        
        # Line chart description
        description = f"Line chart showing {y_col} across {len(df)} {x_col} values. "
        description += f"Trend from {df[y_col].min():.1f} to {df[y_col].max():.1f}."
        
    elif graph_type == 'pie':
        # Pie chart for categorical data
        value_counts = df[x_col].value_counts().head(8)  # Limit to top 8
        ax.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%')
        ax.set_title(f"Distribution of {x_col}", fontsize=14)
        
        # Pie chart description
        description = f"Pie chart showing distribution of {x_col} across {len(value_counts)} categories. "
        description += f"Largest category: {value_counts.index[0]} ({value_counts.iloc[0]/value_counts.sum()*100:.1f}%)."
    
    elif graph_type == 'violin' and y_col:
        # Violin plot for distribution across categories
        if df[x_col].nunique() > 10:
            top_categories = df[x_col].value_counts().head(10).index
            plot_df = df[df[x_col].isin(top_categories)]
        else:
            plot_df = df
        
        sns.violinplot(x=x_col, y=y_col, data=plot_df, ax=ax)
        ax.set_title(f"Distribution of {y_col} by {x_col}", fontsize=14)
        plt.xticks(rotation=45)
        
        # Violin plot description
        description = f"Violin plot showing distribution of {y_col} across {plot_df[x_col].nunique()} {x_col} categories."
        
    else:
        # Default fallback to histogram
        ax.hist(df[x_col].dropna(), bins=20)
        ax.set_xlabel(x_col, fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title(f"Distribution of {x_col}", fontsize=14)
        description = f"Visualization of {x_col} distribution with {len(df)} data points."
    
    return fig, description

def _generate_correlation_heatmap(df: pd.DataFrame) -> Tuple[str, str]:
    """Generate correlation heatmap for all numerical columns."""
    try:
        # Select only numerical columns
        numerical_cols = df.select_dtypes(include=[np.number]).columns
        if len(numerical_cols) < 2:
            return _generate_error_image("Not enough numerical columns for heatmap"), "Insufficient numerical columns (need at least 2) for correlation analysis"
        
        corr_matrix = df[numerical_cols].corr()
        
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                   square=True, ax=ax, fmt='.2f', cbar_kws={"shrink": .8})
        ax.set_title('Correlation Heatmap', fontsize=14, pad=20)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        
        # Generate concise description
        description = f"Correlation heatmap showing relationships between {len(numerical_cols)} numerical variables. "
        
        # Find strongest correlations
        strong_corrs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    strong_corrs.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_val))
        
        if strong_corrs:
            description += f"Strong correlations found between {min(3, len(strong_corrs))} variable pairs."
        else:
            description += "No strong correlations detected."
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        return f"data:image/png;base64,{image_base64}", description
        
    except Exception as e:
        logger.error(f"Error generating heatmap: {str(e)}")
        return _generate_error_image(f"Heatmap error: {str(e)}"), f"Heatmap generation failed: {str(e)}"

def _generate_outlier_boxplots(df: pd.DataFrame) -> Tuple[str, str]:
    """Generate box plots for outlier detection in numerical columns."""
    try:
        numerical_cols = df.select_dtypes(include=[np.number]).columns
        if len(numerical_cols) == 0:
            return _generate_error_image("No numerical columns for box plots"), "No numerical columns available for outlier analysis"
        
        # Limit to first 6 columns for better visualization
        numerical_cols = numerical_cols[:6]
        
        # Create subplots
        n_cols = min(3, len(numerical_cols))
        n_rows = (len(numerical_cols) + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 4*n_rows))
        fig.suptitle('Outlier Detection - Box Plots', fontsize=14, y=0.98)
        
        # Flatten axes array for easier indexing
        if n_rows > 1 and n_cols > 1:
            axes = axes.flatten()
        elif n_rows == 1:
            axes = [axes] if n_cols == 1 else axes
        
        description = f"Box plots showing outlier detection for {len(numerical_cols)} numerical variables. "
        outlier_counts = {}
        
        for idx, col in enumerate(numerical_cols):
            if idx < len(axes):
                ax = axes[idx]
                df[col].plot(kind='box', ax=ax)
                ax.set_title(col, fontsize=12)
                ax.grid(True, alpha=0.3)
                
                # Count outliers
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers = df[(df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))]
                outlier_counts[col] = len(outliers)
        
        # Remove empty subplots
        for idx in range(len(numerical_cols), len(axes)):
            if idx < len(axes):
                fig.delaxes(axes[idx])
        
        plt.tight_layout()
        
        # Generate concise description
        total_outliers = sum(outlier_counts.values())
        description += f"Total outliers detected: {total_outliers}. "
        if total_outliers > 0:
            top_outliers = sorted(outlier_counts.items(), key=lambda x: x[1], reverse=True)[:2]
            description += f"Most outliers in {top_outliers[0][0]}."
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        return f"data:image/png;base64,{image_base64}", description
        
    except Exception as e:
        logger.error(f"Error generating box plots: {str(e)}")
        return _generate_error_image(f"Box plot error: {str(e)}"), f"Box plot generation failed: {str(e)}"

def _generate_error_image(message: str) -> Tuple[str, str]:
    """Generate an error image with the given message."""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.text(0.5, 0.5, message, 
            horizontalalignment='center', 
            verticalalignment='center', 
            transform=ax.transAxes,
            fontsize=14,
            color='red',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.7))
    ax.set_axis_off()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    
    return f"data:image/png;base64,{image_base64}", message

def get_data_stats_for_insights(df: pd.DataFrame, x_col: str, y_col: str = None) -> Dict:
    """Get statistics for insights generation."""
    stats = {}
    
    if x_col in df.columns:
        x_stats = f"Range: {df[x_col].min():.1f}-{df[x_col].max():.1f}, Mean: {df[x_col].mean():.1f}"
        stats['x_stats'] = x_stats
    
    if y_col and y_col in df.columns:
        y_stats = f"Range: {df[y_col].min():.1f}-{df[y_col].max():.1f}, Mean: {df[y_col].mean():.1f}"
        stats['y_stats'] = y_stats
    
    return stats