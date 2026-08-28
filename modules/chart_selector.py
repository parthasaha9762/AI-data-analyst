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


def recommend_chart_config(user_question: str, df: pd.DataFrame)->dict:
    """
    PURPOSE:
    Queries Google Gemini LLM to analyze the User Question intent AND 
    the SQL Result DataFrame structure, then returns the recommended chart type,
    X/Y column assignments, and plain-English reasoning as a Python dictionary.
    """
    # Safety Check: Return fallback if DataFrame is empty
    if df is None or df.empty:
        return {
            "chart_type":"table",
            "x_column": None,
            "y_column": None,
            "color_column": None,
            "title": "No Data available",
            "reasoning": "The DataFrame is empty (0 rows). So, no chart can be rendered."
        }

    # Fetch API Key from environment
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("EMINI_API_KEY environment variable is missing!")

    client = genai.Client(api_key=api_key)

    # Call Step 1 helper function to format the DataFrame as a JSON string
    df_context_json = format_dataframe_context(df)

    # Construct the LLM prompt with strict rules for chart selection
    prompt = f"""
    USER ORIGINAL QUESTION:
    "{user_question}"
    DATAFRAME METADATA & SAMPLE RESULT (JSON):
    {df_context_json}
    TASK:
    Analyze the user question intent AND the DataFrame metadata above, then determine the best visualization chart type.
    CHART SELECTION RULES:
    1. LINE CHART ("line"): Choose if user question mentions time, dates, months, growth, trends, over time.
    2. BAR CHART ("bar"): Choose if comparing discrete categories, top N rankings, or comparing metrics across groups.
    3. PIE CHART ("pie"): Choose if user question asks for proportion/percentage of total AND category column has 5 or FEWER unique values.
    4. SCATTER PLOT ("scatter"): Choose if analyzing correlation between two numeric variables.
    5. HISTOGRAM ("histogram"): Choose if analyzing distribution of a single numeric column.
    6. TABLE ("table"): Choose if data has 1 row or scalar count result.
    Respond ONLY with a JSON object matching this schema:
    {{
    "chart_type": "bar | line | pie | scatter | histogram | table",
    "x_column": "Exact column name from DataFrame for X-axis",
    "y_column": "Exact column name from DataFrame for Y-axis",
    "color_column": null,
    "title": "A clean, executive chart title",
    "reasoning": "2-3 sentence explanation of why this chart was selected"
    }}
    """


    system_instruction_prompt = (
        "You are an expert Data Visualization Architect.\n"
        "Output ONLY raw valid JSON with NO markdown code fences (like ```json)."
    )


    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash"]
    response = None
    
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction_prompt,
                    temperature = 0.2,  # Low temperature for precise, deterministic decisions
                    response_mime_type = "application/json", # STRICTLY enforce JSON output
                ),
            )
            
            if response and response.text:
                break
        except Exception:
            continue
    
    if response or not response.text:
        return {"chart_type": "table", "reasoning": "Gemini API unavailable."}


    # Clean raw output text and parse into a Python dictionary
    raw_text = response.text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]

    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]

    return json.loads(raw_text.strip())