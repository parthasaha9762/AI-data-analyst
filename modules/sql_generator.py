# This module will generate SQL data using schema context and user question, based on that it will for now, only generate SQL query

import os 
from google import genai
from google.genai import types

import warnings
warnings.filterwarnings("ignore")



def generate_SQL_query(schema_context: str, user_question: str)-> str:
    # Fetch Gemini API key and create a client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing! Please set it before running.")

    client = genai.Client(api_key=api_key)

    # Build user prompt
    prompt = f"""
    DATABASE SCHEMA:
    {schema_context}

    USER QUESTION:
    {user_question}

    Please generate a valid SQLite SQL query based on the schema and the question.
    """

    # Set system instruction
    system_instruction_prompt = (
    "You are an expert SQLite SQL generator.\n"
    "STRICT RULES:\n"
    "1. Use ONLY table names and column names present in the DATABASE SCHEMA.\n"
    "2. Do NOT invent table names or column names.\n"
    "3. Output ONLY the raw executable SQL query. Do NOT include markdown formatting (like ```sql or ```), explanations, or notes.\n"
    "4. Always end the query with a semicolon (;).\n"
    "5. Format the SQL query cleanly across multiple lines (place FROM, JOIN, WHERE, GROUP BY, ORDER BY, and LIMIT on new lines)."
    )

    # Call the Gemini API key latest version
    # Try models with automatic fallback if Google experiences a 503 spike

    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash"]
    response = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model= model_name,
                contents = prompt,
                config= types.GenerateContentConfig(
                    system_instruction = system_instruction_prompt,
                    temperature = 0.1, # Low temperature for precise SQL generation, to avoid creativity and hallucinations and to provide strict 100% execution rate
                ),
            )

            if response and response.text:
                break
            
        except Exception as e:
            continue

    if not response or not response.text:
        raise RuntimeError("Google Gemini API is currently unavailable. Please try again in a few seconds.")

    raw_sql = response.text.strip()
    

    # Clean off any markdown fences
    if raw_sql.startswith("```sql"):
        raw_sql = raw_sql[6:]
    
    elif raw_sql.startswith("```"):
        raw_sql = raw_sql[3:]


    if raw_sql.endswith("```"):
        raw_sql = raw_sql[:-3]

    return raw_sql


# Quick standalone test
if __name__ == "__main__":
    test_schema = "TABLE: users\n Columns:\n- id: INTEGER\n- name: VARCHAR"

    test_question = "show me all users"

    try:
        print(f"Your output: {generate_SQL_query(test_schema, test_question)}")

    except Exception as e:
        print(e)
    

