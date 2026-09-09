import os
import re
import json
import warnings
import pandas as pd
from google import genai
from google.genai import types

try:
    from modules.security_manager import mask_sensitive_dataframe
except ImportError:
    from security_manager import mask_sensitive_dataframe

warnings.filterwarnings("ignore")

# Module-level cache to remember discovered Pro models
_CACHED_PRO_MODELS = None
_WORKING_PRO_MODEL = None


def prepare_statistical_context(df: pd.DataFrame)-> dict:
    """
    Computes mathematical summary statistics and extracts sample data 
    from the SQL result DataFrame to ground the LLM's business analysis.
    Sensitive PII data in sample rows is automatically masked for enterprise privacy.
    """

    if df is None or df.empty:
        return {"error": "DataFrame is empty"}
    
    # Securely mask sample rows to protect confidential customer/business data
    masked_sample_df = mask_sensitive_dataframe(df.head(5))
    
    summary = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "numeric_summary": {},
        "sample_rows": masked_sample_df.to_dict(orient= "records")
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

    # 3. System instructions defining the simplified, executive 3-block framework
    system_instruction_prompt = (
        "You are an expert Executive Business Advisor & Senior Analytics Consultant.\n"
        "Your mission is to deliver crisp, high-impact business insights in plain, simple English that any non-technical business owner or stakeholder can instantly understand and act upon.\n\n"
        "STRICT GUIDELINES:\n"
        "1. Write in plain, everyday business English. Avoid academic or statistical jargon (no 'disparity clustering', 'statistical variance', 'macro cohorts', etc.).\n"
        "2. Keep the entire response strictly concise (around 6 to 10 lines total across all sections).\n"
        "3. Ground all numbers directly in the provided table and chart data.\n"
        "4. Always quantify the upside or money opportunity (e.g. 'Fixing X can add +$Y to revenue').\n"
        "5. ALWAYS format all key metrics, percentages, dollar amounts, and entity names in BOLD markdown (e.g. **$3.92M**, **49.54%**, **+$646K**, **Home & Kitchen**) so the essential numbers pop out immediately.\n\n"
        "STRUCTURE YOUR OUTPUT EXACTLY AS FOLLOWS (in Markdown):\n\n"
        "### 💡 The Big Picture\n"
        "[2-3 simple sentences explaining the core takeaway from the data and chart in plain language, with all key numbers and categories in bold.]\n\n"
        "### 🚀 Where We Can Grow\n"
        "[2-3 sentences explaining the biggest opportunity to increase sales, reduce waste, or capture lost revenue with estimated bolded dollar/percent impact.]\n\n"
        "### 🎯 Action Plan\n"
        "1. **Quick Fix:** 1 clear, immediate tactical step you can do today\n"
        "2. **Next Move:** 1 straightforward growth or operational initiative for the coming weeks\n"
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

    raw_output = response.text.strip()

    # Escape $ signs so Streamlit treats them as currency rather than LaTeX math formulas
    cleaned_output = raw_output.replace("$", r"\$")

    return cleaned_output




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
