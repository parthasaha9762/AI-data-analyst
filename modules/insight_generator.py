import os
import re
import json
import warnings
import pandas as pd
from google import genai
from google.genai import types

warnings.filterwarnings("ignore")

# Module-level cache to remember discovered Pro models
_CACHED_PRO_MODELS = None
_WORKING_PRO_MODEL = None


def prepare_statistical_context(df: pd.DataFrame)-> dict:
    """
    Computes mathematical summary statistics and extracts sample data 
    from the SQL result DataFrame to ground the LLM's business analysis.
    """

    if df is None or df.empty:
        return {"error": "DataFrame is empty"}
    
    summary = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "numeric_summary": {},
        "sample_rows": df.head(5).to_dict(orient= "records")
    }

    # Analyze numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        # 1. Use describe() for standard statistical distribution
        desc = df[numeric_cols].describe().round(2).to_dict()

        # 2. Add the missing 'sum' for each numeric column
        for col in numeric_cols:
            desc[col]["sum"] = round(float(df[col].sum()), 2)

        summary["numeric_summary"] = desc

    return summary


def get_sorted_pro_models(client)-> list:
    """
    Dynamically discovers all available models from Gemini API,
    prioritizes 'Pro' deep reasoning models first, and keeps Flash models 
    as reliable fallbacks. Caches the result across calls.
    """
    global _CACHED_PRO_MODELS, _WORKING_PRO_MODEL

    # 1. If we already found a verified working model in this session, prioritize it immediately
    if _WORKING_PRO_MODEL:
        return [_WORKING_PRO_MODEL] + [backup_pro_model for backup_pro_model in (_CACHED_PRO_MODELS or []) if backup_pro_model != _WORKING_PRO_MODEL]

    # 2. If models were already discovered and cached, return them directly
    if _CACHED_PRO_MODELS:
        return _CACHED_PRO_MODELS

    # 3. Discover models from the API
    try:
        all_models = list(client.models.list())
        pro_models = []
        flash_models = []
        for m in all_models:
            name = m.name.replace("models/", "")
            # Skip audio, TTS, image generation, or embedding models
            if any(skip in name.lower() for skip in ["tts", "audio", "image", "embedding"]):
                continue
            # Separate Pro models and Flash models
            if "pro" in name.lower():
                pro_models.append(name)
            elif "flash" in name.lower():
                flash_models.append(name)
        # Combine: Pro models first for deep reasoning, Flash models as backup
        _CACHED_PRO_MODELS = pro_models + flash_models
        # Safety default if list is empty
        if not _CACHED_PRO_MODELS:
            _CACHED_PRO_MODELS = ["gemini-2.5-pro", "gemini-1.5-pro", "gemini-2.5-flash"]
    except Exception:
        # Fallback in case of network or API error
        _CACHED_PRO_MODELS = ["gemini-2.5-pro", "gemini-1.5-pro", "gemini-2.5-flash"]
        
    return _CACHED_PRO_MODELS



def generate_business_insights(
    user_question: str,
    df: pd.DataFrame,
    chart_config: dict = None,
    generated_sql: str = None
) -> str:
    """
    PURPOSE:
    Generates consulting-grade business insights, root-cause diagnostics,
    and strategic recommendations using Google Gemini Pro.

    INPUTS:
    - user_question (str): The business question asked by the user.
    - df (pd.DataFrame): The SQL query result DataFrame.
    - chart_config (dict, optional): The chart configuration dictionary from chart_selector.
    - generated_sql (str, optional): The executed SQL query.

    OUTPUTS:
    - str: A formatted markdown report with executive business insights.
    """
    global _WORKING_PRO_MODEL

    # Safety Check: Return fallback if DataFrame is missing or empty
    if df is None or df.empty:
        return "⚠️ No data available to generate business insights. The query returned 0 rows."

    # Fetch API Key from environment
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing! Please set it before running.")

    client = genai.Client(api_key=api_key)

    # 1. Format statistical profile and chart metadata into clean JSON strings
    stats_context = json.dumps(prepare_statistical_context(df), indent=2)
    chart_metadata = json.dumps(chart_config or {}, indent=2)

    # 2. Build User Prompt with rich multi-modal context
    prompt = f"""
    USER BUSINESS QUESTION:
    "{user_question}"

    EXECUTED SQL QUERY:
    {generated_sql or "N/A"}

    DATA SUMMARY & SAMPLE RECORDS (JSON):
    {stats_context}

    VISUALIZATION CHART CONTEXT (JSON):
    {chart_metadata}

    TASK:
    Perform a deep, strategic business analysis of the data provided above to directly answer the user's question.
    """

    # 3. System instructions defining the consulting analytical framework
    system_instruction_prompt = (
        "You are a Principal Business Strategist and Chief Data Analytics Consultant.\n"
        "Your mission is to provide deep, analytical, and actionable business insights grounded STRICTLY in the provided data.\n\n"
        "ANALYTICAL GUIDELINES:\n"
        "1. DO NOT simply restate the raw table data. Synthesize what the numbers MEAN for the business.\n"
        "2. Identify dominant drivers, concentration risks, performance gaps, or growth anomalies.\n"
        "3. Provide realistic, quantified projections for future improvements (e.g. 'If underperforming segments reach median performance, revenue could improve by X%').\n"
        "4. Provide realistic strategic recommendations divided into immediate tactical actions and strategic growth initiatives.\n\n"
        "STRUCTURE YOUR OUTPUT EXACTLY AS FOLLOWS (in Markdown):\n\n"
        "### 📊 Executive Summary\n"
        "[2-3 sentence high-level executive answer directly addressing the question]\n\n"
        "### 🔍 Diagnostic Findings & Trend Analysis\n"
        "- **Primary Performance Driver:** [Key finding with exact metric & %]\n"
        "- **Key Disparity / Gap:** [Comparison between top and low performers]\n"
        "- **Pattern / Anomaly:** [Trend or distribution pattern]\n\n"
        "### 📈 Future Impact & Improvement Potential\n"
        "- **Estimated Upside:** [Realistic projection/improvement potential based on data]\n"
        "- **Risk Factor / Vulnerability:** [Key business risk to monitor]\n\n"
        "### 🎯 Strategic Action Plan\n"
        "1. **Quick Win (0–30 Days):** [Immediate tactical step]\n"
        "2. **Medium-Term Strategy (30–90 Days):** [Strategic operational or marketing action]\n"
    )

    # 4. Model iteration with automatic fallback
    models_to_try = get_sorted_pro_models(client)
    response = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction_prompt,
                    temperature=0.25,  # Balanced for strategic depth and consistency
                ),
            )

            if response and response.text:
                _WORKING_PRO_MODEL = model_name
                break
        except Exception:
            continue

    if not response or not response.text:
        return "⚠️ Business insights could not be generated due to temporary API unavailability. Please try again."

    return response.text.strip()



# Quick Standalone Test
if __name__ == "__main__":
    test_df = pd.DataFrame({
        "Category": ["Electronics", "Clothing", "Home & Kitchen", "Books"],
        "Total_Sales": [150000, 85000, 42000, 12000],
        "Profit_Margin": [0.22, 0.35, 0.18, 0.10]
    })

    test_question = "What are our best performing categories and how can we optimize sales?"
    test_sql = "SELECT Category, SUM(Sales) AS Total_Sales, AVG(Margin) AS Profit_Margin FROM sales GROUP BY Category ORDER BY Total_Sales DESC;"

    print("=== TESTING BUSINESS INSIGHT GENERATOR ===")
    try:
        result = generate_business_insights(
            user_question=test_question,
            df=test_df,
            generated_sql=test_sql
        )
        print(result)
    except Exception as e:
        print(f"Error: {e}")
