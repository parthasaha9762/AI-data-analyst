"""
Chart Selector Module - Starter Skeleton
---------------------------------------
Follow along step-by-step to implement the AI-powered Chart Selector!
"""

import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from google.genai import types

# TODO 1: Implement format_dataframe_context(df)
# TODO 2: Implement recommend_chart_config(user_question, df)
# TODO 3: Implement generate_plotly_chart(df, chart_config)


def format_dataframe_context(df: pd.DataFrame)-> str:
    """
    Extracts metadata and sample rows from the SQL Result DataFrame 
    and formats them as a clean JSON string for the LLM.
    """
    
    if df is None or df.empty:
        return json.dumps({"error": "DataFrame is empty(0 rows)"})

    # Build structured metadata dictionary for SQL result dataframe
    metadata = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": [
            {
                "name": col,
                "data_type": str(df[col].dtype),
                "unique_values": int(df[col].nunique())
            }
            for col in df.columns
        ],
         # df.head(5) safely takes up to 5 sample rows (or all rows if total_rows <= 5) to prevent unnecessary token usage of Google API and to save costs and time
         "sample_rows": df.head(5).to_dict(orient = "records")
    }

    # Convert dictionary into a JSON-formatted string
    return json.dumps(metadata, indent=2)

