"""
SQL Explainer Module
--------------------
Uses Google Gemini API to generate a concise, human-friendly explanation 
of WHY a specific SQL query was created for a given user question.
"""

import os 
from google import genai
from google.genai import types

try:
    from modules.security_manager import get_gemini_api_key
except ImportError:
    from security_manager import get_gemini_api_key

import warnings
warnings.filterwarnings("ignore")

def explain_SQL_query(schema_context: str, user_question: str, generated_sql: str)-> str:
    """
    Generates a plain-English explanation of why and how an SQL query was built.
    """

    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing! Please configure it in your .env file or Streamlit secrets.")

    client = genai.Client(api_key=api_key)

    # Build user prompt
    prompt = f"""
    DATABASE SCHEMA:
    {schema_context}

    USER QUESTION:
    {user_question}

    GENERATED SQL QUERY:
    {generated_sql}

    Explain the SQL query in simple, plain English, suitable for business users as well as for normal people so that they also can understand it easily.
    Explain:
    - Which tables were used
    - Which columns were selected
    - Why joins were used (if any)
    - How conditions in WHERE clause were determined
    - How aggregations or groupings work (if any)
    - Why LIMIT was used (if any)

    Keep the explanation concise but thorough (3-6 sentences).
    """

    # Set system instruction
    system_instruction_prompt = (
        "You are an advanced Data Analytics Instructor.\n"
        "Your task is to explain WHY and HOW a specific SQL query answers the user's question.\n\n"
        "GUIDELINES:\n"
        "1. Explain in simple, clear, and non-technical language.\n"
        "2. Use 2 to 4 bullet points (e.g. Tables chosen, Filters applied, Aggregations/Sorting).\n"
        "3. Explain WHY specific tables and columns were selected based on the user question.\n"
        "4. Keep it short, concise, and easy to read."
    )

    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"]
    response = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction_prompt,
                    temperature=0.3,  # Moderate temperature for natural language explanation
                ),
            )
            if response and response.text:
                break
        except Exception:
            continue

    if not response or not response.text:
        return "Explanation currently unavailable."

    
    return response.text.strip()

# Quick standalone test
if __name__ == "__main__":
    test_schema = "TABLE: users\n Columns:\n- id: INTEGER\n- name: VARCHAR"
    test_question = "Show all users"
    test_sql = "SELECT * FROM users;"
    try:
        print("=== TESTING SQL EXPLAINER ===")
        print(explain_SQL_query(test_schema, test_question, test_sql))
    except Exception as e:
        print(e)