"""
Chart Selector Module
---------------------
This module handles intelligent, automated data visualization for the AI Data Analyst application.
It analyzes the user's analytical question alongside the structure and metadata of the SQL query 
results, leveraging Google Gemini to determine the most effective chart type (such as Bar, Line, 
Pie, Scatter, Histogram, or Table) and axis configurations.

Key Capabilities:
1. DataFrame Context Formatting: Extracts column schemas, data types, cardinality, and sample rows from query results.
2. AI-Powered Recommendation: Uses Gemini LLM to choose optimal chart types, axis mappings (X, Y, Color), executive titles, visual reasoning, and key takeaways.
3. Interactive Plotly Rendering: Generates publication-ready, interactive Plotly visualizations with styled themes, custom color palettes, formatted tooltips, and data labels.
"""

import re
import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from google.genai import types

# Core Module Components:
# 1. format_dataframe_context(df): Formats SQL results & metadata as structured JSON for the LLM
# 2. get_sorted_flash_models(client): Dynamically discovers & caches available Gemini Flash models
# 3. recommend_chart_config(user_question, df): Uses Gemini to determine chart type, axes & executive takeaways
# 4. generate_plotly_chart(df, chart_config): Renders publication-grade interactive Plotly figures

# Module-level cache to remember discovered models across calls
_CACHED_MODELS = None
_WORKING_MODEL = None


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


def get_sorted_flash_models(client)-> list:
    """
    Dynamically discovers all available models from Gemini API,
    filters for fast Flash/Flash-Lite models, and sorts them by version 
    descending (newest first). Caches the result so it only queries once.
    """
    global _CACHED_MODELS, _WORKING_MODEL

    # If we already found a verified working model in this session, prioritize it immediately and return the working model with the backup models if in case working model got a temporary spike
    if _WORKING_MODEL:
        return [_WORKING_MODEL] + [backup_model for backup_model in (_CACHED_MODELS or []) if backup_model != _WORKING_MODEL]

    # If already cached, return the cached list without calling the API again
    if _CACHED_MODELS:
        return _CACHED_MODELS

    # First try to find a working model, prioritize Flash models (fast, cheap)
    try:
        all_models = list(client.models.list())
        extracted = []

        for m in all_models:
            name = m.name.replace("models/", "")

            # Filter: only look for flash text models, skipping audio, tts, image, or embedding models
            if "flash" in name.lower() and not any(skip in name.lower() for skip in ["tts", "audio", "image", "embedding"]):
                # Extract numeric version: e.g. "3.6", "3.5", "3.1", "2.5"
                version_match = re.search(r"(\d+(?:\.\d+)?)", name)
                version = float(version_match.group(1)) if version_match else 0.0

                is_lite = "lite" in name.lower()
                is_stable = "preview" not in name.lower()

                # Score: (Model Name, Version Number, Is Lite, Is Stable)
                extracted.append((name, version, is_lite, is_stable))

        # Sort: Lite models first -> Newest version first -> Stable over Preview
        extracted.sort(
            key=lambda x: (x[2], x[1], x[3]),
            reverse=True # sorts descending by (version_number, is_lite, is_stable). Since False < True, Stable comes before Preview.
        )
        _CACHED_MODELS = [item[0] for item in extracted]        

    except Exception:
        # Safe fallback if network is unreachable
        _CACHED_MODELS = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite"]

    return _CACHED_MODELS



def recommend_chart_config(user_question: str, df: pd.DataFrame)->dict:
    global _WORKING_MODEL

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
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing!")

    client = genai.Client(api_key=api_key)

    # Format the DataFrame context and sample rows as a structured JSON string
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
    "reasoning": "2-3 sentence explanation of why this chart was selected",
    "conclusion": "A single, high-impact sentence summarizing the #1 fact shown in the chart (e.g., 'Home & Kitchen leads all categories with $833.6K in revenue (21.27%), followed closely by Sports at 20.25%.')"
    }}
    """


    system_instruction_prompt = (
        "You are an expert Data Visualization Architect.\n"
        "GUIDELINES FOR REASONING:\n"
        "1. Explain in simple, plain English why this chart type fits the user question intent.\n"
        "2. Explain how the X and Y columns map to the chart.\n"
        "3. Keep the reasoning friendly, educational, and easy to read for any non-technical user.\n\n"
        "GUIDELINES FOR CONCLUSION:\n"
        "1. Write a single, sharp sentence summarizing the #1 fact or top performer shown in the chart.\n"
        "2. Include the leading category/city name and its percentage or dollar lead.\n\n"
        "Output ONLY raw valid JSON with NO markdown code fences (like ```json)."
    )

    # 1. Fetch dynamically sorted models (newest & fastest first)
    models_to_try = get_sorted_flash_models(client)
    response = None

    # 2. Loop until a working model is found (Model Retry Logic)
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

                # Save this model for future requests
                _WORKING_MODEL = model_name
                break
        except Exception:
            continue
    
    if not response or not response.text:
        return {"chart_type": "table", "reasoning": "Gemini API unavailable."}


    # Clean raw output text and parse into a Python dictionary
    raw_text = response.text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]

    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]

    return json.loads(raw_text.strip())



def generate_plotly_chart(df: pd.DataFrame, chart_config: dict)-> go.Figure:
    """
    PURPOSE:
    Renders an interactive Plotly figure object based on the chart configuration 
    recommended by the LLM (chart_type, x_column, y_column, title).
    WHY PLOTLY IS USED:
    Plotly produces interactive web charts (hover tooltips, zoom, legend toggles) 
    that render seamlessly inside Streamlit using st.plotly_chart().
    """
    # Safety Check: Return None if DataFrame is missing or empty
    if df is None or df.empty:
        return None

    # Extract chart parameters from the LLM configuration dictionary
    chart_type = chart_config.get("chart_type", "table").lower()
    x_col = chart_config.get("x_column")
    y_col = chart_config.get("y_column")
    color_col = chart_config.get("color_column")
    title = chart_config.get("title", "Data Visualization")

    # If LLM recommended table view or if x_column doesn't exist in DataFrame, return None
    if chart_type == "table" or not x_col or x_col not in df.columns:
        return None

    # Sleek luxury modern color palette for Plotly charts (Electric Indigo, Cyan, Emerald, Amber, Rose, Violet)
    custom_color_sequence = [
        "#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#EC4899", 
        "#8B5CF6", "#3B82F6", "#14B8A6", "#F97316", "#A855F7"
    ]

    try:
        # 1. BAR CHART: Best for categorical rankings or comparisons (multi-colored per category)
        if chart_type == "bar":
            bar_color = color_col if (color_col and color_col in df.columns) else x_col
            fig = px.bar(
                df, 
                x=x_col, 
                y=y_col, 
                color=bar_color,
                title=title,
                text_auto=True if len(df) <= 15 else False, # Automatically display numeric labels on bars
                color_discrete_sequence=custom_color_sequence
            )
            fig.update_traces(
                marker_line_width=0, 
                opacity=0.92,
                textfont=dict(family="Inter, sans-serif", size=11),
                textposition="outside" if len(df) <= 12 else "inside"
            )
            fig.update_layout(
                xaxis_title=x_col, 
                yaxis_title=y_col
            )

        # 2. LINE CHART: Best for time-series trends (dates, months, growth)
        elif chart_type == "line":
            fig = px.line(
                df, 
                x=x_col, 
                y=y_col, 
                color=color_col if (color_col and color_col in df.columns) else None,
                title=title,
                markers=True, # Show data point dots on line
                color_discrete_sequence=custom_color_sequence
            )
            fig.update_traces(
                line=dict(width=3.2, shape="spline"),
                marker=dict(size=8, symbol="circle", line=dict(width=2, color="#FFFFFF"))
            )
            fig.update_layout(xaxis_title=x_col, yaxis_title=y_col)

        # 3. PIE CHART: Best for percentage/share of total (<= 5 categories)
        elif chart_type == "pie":
            fig = px.pie(
                df, 
                names=x_col, 
                values=y_col if y_col in df.columns else None,
                title=title,
                hole=0.42, # Modern donut-style hole in center
                color_discrete_sequence=custom_color_sequence
            )
            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                marker=dict(line=dict(color="#FFFFFF", width=2))
            )

        # 4. SCATTER PLOT: Best for correlation between two numeric columns
        elif chart_type == "scatter":
            scatter_color = color_col if (color_col and color_col in df.columns) else x_col
            fig = px.scatter(
                df, 
                x=x_col, 
                y=y_col, 
                color=scatter_color,
                title=title,
                color_discrete_sequence=custom_color_sequence
            )
            fig.update_traces(
                marker=dict(size=10, opacity=0.85, line=dict(width=1.5, color="#FFFFFF"))
            )
            fig.update_layout(xaxis_title=x_col, yaxis_title=y_col)

        # 5. HISTOGRAM: Best for numeric distributions
        elif chart_type == "histogram":
            hist_color = color_col if (color_col and color_col in df.columns) else x_col
            fig = px.histogram(
                df, 
                x=x_col, 
                color=hist_color,
                title=title,
                color_discrete_sequence=custom_color_sequence
            )
            fig.update_traces(
                marker_line_width=0.5,
                marker_line_color="#FFFFFF",
                opacity=0.9
            )

        # Default Fallback: Bar chart
        else:
            bar_color = color_col if (color_col and color_col in df.columns) else x_col
            fig = px.bar(df, x=x_col, y=y_col, color=bar_color, title=title, color_discrete_sequence=custom_color_sequence)

        # Apply high-end, responsive modern layout with custom typography, visible legends, and clean gridlines
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            font=dict(family="Plus Jakarta Sans, Inter, -apple-system, sans-serif", size=13),
            title=dict(
                font=dict(size=18, family="Plus Jakarta Sans, Inter, sans-serif"),
                x=0.01,
                y=0.96
            ),
            xaxis=dict(
                gridcolor="rgba(148, 163, 184, 0.18)",
                zerolinecolor="rgba(148, 163, 184, 0.25)",
                tickfont=dict(family="Inter, sans-serif", size=11)
            ),
            yaxis=dict(
                gridcolor="rgba(148, 163, 184, 0.18)",
                zerolinecolor="rgba(148, 163, 184, 0.25)",
                tickfont=dict(family="Inter, sans-serif", size=11)
            ),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                font=dict(family="Inter, sans-serif", size=10.5),
                itemsizing="constant",
                tracegroupgap=2
            ),
            hoverlabel=dict(
                bgcolor="#0F172A",
                font_color="#FFFFFF",
                font_size=12,
                font_family="Inter, sans-serif",
                bordercolor="#6366F1"
            ),
            margin=dict(l=30, r=40, t=65, b=35)
        )
        return fig

    except Exception as e:
        print(f"Error generating Plotly chart: {e}")
        return None


# ------------------------------------------------------------------------------
# STANDALONE TESTING BLOCK
# ------------------------------------------------------------------------------
# Running `python modules/chart_selector.py` directly executes this block
# to verify chart recommendation logic on test questions and sample DataFrames.
if __name__ == "__main__":
    print("==========================================")
    print("=== RUNNING STANDALONE CHART SELECTOR TEST ===")
    print("==========================================")

    # Test Scenario 1: Top Cities by Revenue (Categorical comparison -> Expect Bar Chart)
    test_df_1 = pd.DataFrame({
        "city": ["Kolkata", "Delhi", "Mumbai", "Chennai", "Bangalore"],
        "total_revenue": [125000, 110000, 95000, 82000, 78000]
    })
    test_q_1 = "Which 5 cities generated the highest revenue?"

    print(f"\n--- TEST 1: {test_q_1} ---")
    print("Generated Context JSON:")
    print(format_dataframe_context(test_df_1))

    try:
        config_1 = recommend_chart_config(test_q_1, test_df_1)
        print("\nAI Recommended Config:")
        print(json.dumps(config_1, indent=2))

        fig_1 = generate_plotly_chart(test_df_1, config_1)
        print(f"Plotly Figure Generated Successfully: {fig_1 is not None}")
    except Exception as e:
        print(f"Test 1 Failed: {e}")

    # Test Scenario 2: Monthly Sales Growth (Time-series trend -> Expect Line Chart)
    test_df_2 = pd.DataFrame({
        "month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "sales_growth": [10000, 14000, 18000, 22000, 29000, 35000]
    })
    test_q_2 = "Show me monthly sales growth trends over time."

    print(f"\n--- TEST 2: {test_q_2} ---")
    try:
        config_2 = recommend_chart_config(test_q_2, test_df_2)
        print("\nAI Recommended Config:")
        print(json.dumps(config_2, indent=2))

        fig_2 = generate_plotly_chart(test_df_2, config_2)
        print(f"Plotly Figure Generated Successfully: {fig_2 is not None}")
    except Exception as e:
        print(f"Test 2 Failed: {e}")
