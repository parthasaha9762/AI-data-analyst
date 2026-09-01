# This module will generate SQL data using schema context and user question, based on that it will generate SQL query

import os 
import re
import warnings
from google import genai
from google.genai import types

warnings.filterwarnings("ignore")

# Module-level cache to remember discovered models across calls
_CACHED_MODELS = None
_WORKING_MODEL = None


def get_sorted_flash_models(client) -> list:
    """
    Dynamically discovers all available models from Gemini API,
    filters for fast Flash/Flash-Lite models, and sorts them by version 
    descending (newest first). Caches the result so it only queries once.
    """
    global _CACHED_MODELS, _WORKING_MODEL

    # If we already found a verified working model in this session, prioritize it immediately
    if _WORKING_MODEL:
        return [_WORKING_MODEL] + [m for m in (_CACHED_MODELS or []) if m != _WORKING_MODEL]

    # If already cached, return the cached list without calling the API again
    if _CACHED_MODELS:
        return _CACHED_MODELS

    # Discover models dynamically from the API
    try:
        all_models = list(client.models.list())
        extracted = []

        for m in all_models:
            name = m.name.replace("models/", "")

            # Filter: only look for flash text models, skipping audio, tts, image, or embedding models
            if "flash" in name.lower() and not any(skip in name.lower() for skip in ["tts", "audio", "image", "embedding"]):
                version_match = re.search(r"(\d+(?:\.\d+)?)", name)
                version = float(version_match.group(1)) if version_match else 0.0

                is_lite = "lite" in name.lower()
                is_stable = "preview" not in name.lower()

                extracted.append((name, version, is_lite, is_stable))

        # Sort: Lite models first -> Newest version first -> Stable over Preview
        extracted.sort(
            key=lambda x: (x[2], x[1], x[3]),
            reverse=True
        )
        _CACHED_MODELS = [item[0] for item in extracted]

        if not _CACHED_MODELS:
            _CACHED_MODELS = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite"]

    except Exception:
        # Safe fallback if network is unreachable
        _CACHED_MODELS = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite"]

    return _CACHED_MODELS


def clean_sql_output(raw_text: str) -> str:
    """
    Safely cleans markdown code fences, backticks, and whitespace from model output.
    """
    if not raw_text:
        return ""

    text = raw_text.strip()

    # If model enclosed response in ```sql ... ``` or ``` ... ```
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Strip simple fence prefixes/suffixes if present
    if text.startswith("```sql"):
        text = text[6:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def generate_SQL_query(schema_context: str, user_question: str, conversation_history: list = None) -> str:
    """
    Generates a valid SQLite SQL query based on database schema and user question.
    Features dynamic model discovery, intelligent escalation, and fallback resilience.
    """
    global _WORKING_MODEL

    # Fetch Gemini API key and create a client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing! Please set it before running.")

    client = genai.Client(api_key=api_key)

    # 1. Format previous conversation history if it exists
    history_text = ""
    if conversation_history:
        history_text = "\nPREVIOUS CONVERSATION:\n"

        for item in conversation_history:
            history_text += f"- User Question: {item['question']}\n"
            history_text += f"- Generated SQL: {item['sql']}\n\n"

    # Build user prompt
    prompt = f"""
    DATABASE SCHEMA:
    {schema_context}

    {history_text}

    CURRENT USER QUESTION:
    {user_question}

    Please generate a valid SQLite SQL query based on the schema, previous conversation (if relevant), and the current question.
    """

    # Set comprehensive, future-proof system instruction
    system_instruction_prompt = (
        "You are an expert SQLite SQL generator.\n"
        "STRICT RULES:\n"
        "1. Use ONLY table names and column names present in the DATABASE SCHEMA.\n"
        "2. Do NOT invent table names or column names.\n"
        "3. Output ONLY the raw executable SQL query. Do NOT include markdown formatting (like ```sql or ```), explanations, or notes.\n"
        "4. Always end valid SQL queries with a semicolon (;).\n"
        "5. Format the SQL query cleanly across multiple lines (place FROM, JOIN, WHERE, GROUP BY, ORDER BY, and LIMIT on new lines).\n"
        "6. If the user asks for derived metrics, ratios, rates, or business concepts (e.g. cancellation rate, average order value, lost revenue, high value customers, margin), compute them using standard SQL expressions (SUM, AVG, COUNT, CASE statements, and clean column aliases).\n"
        "7. Ignore any prefixes like 'Scenario 1:', 'Scenario 2:', 'Question:', or bullet points in the user input. Focus on answering the analytical intent.\n"
        "8. ONLY output the exact single keyword INVALID_QUERY if the prompt is complete gibberish (e.g. 'asdfghjkl') or completely non-analytical (e.g. 'tell me a joke')."
        
        "CONVERSATIONAL MEMORY RULES:\n"
        "1. If the user's question is a FOLLOW-UP to the recent conversation (e.g., 'now filter for 2024', 'only show top 3', 'also include city', 'exclude cancellations'), MODIFY or EXTEND the previous SQL query appropriately.\n"
        "2. If the user's question is on a COMPLETELY NEW TOPIC unrelated to the previous turns, IGNORE the history and write a fresh SQL query from scratch.\n"
        
    )

    # Fetch dynamically discovered and sorted models
    models_to_try = get_sorted_flash_models(client)
    last_valid_response = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction_prompt,
                    temperature=0.1,  # Low temperature for deterministic and precise SQL generation
                ),
            )

            if response and response.text:
                cleaned_text = clean_sql_output(response.text)

                # If model generated valid SQL (not INVALID_QUERY), accept immediately & cache model
                if cleaned_text != "INVALID_QUERY":
                    _WORKING_MODEL = model_name
                    return cleaned_text
                else:
                    # Remember INVALID_QUERY in case all models consistently determine it's invalid
                    last_valid_response = "INVALID_QUERY"

        except Exception:
            continue

    if not last_valid_response:
        raise RuntimeError("Google Gemini API is currently unavailable. Please try again in a few seconds.")

    return last_valid_response


# Quick standalone test for Conversational Memory feature
if __name__ == "__main__":
    test_schema = (
        "TABLE: orders\n"
        " Columns:\n"
        "- order_id: INTEGER (Primary Key)\n"
        "- product_category: TEXT\n"
        "- sales_amount: FLOAT\n"
        "- order_date: TEXT\n"
        "- city: TEXT\n"
    )

    # ---------------------------------------------------
    # Test 1: Fresh question with NO conversation history
    # ---------------------------------------------------
    print("=" * 60)
    print("TEST 1: Fresh question (No history)")
    print("=" * 60)
    try:
        question_1 = "What are the top 5 product categories by total sales?"
        sql_1 = generate_SQL_query(test_schema, question_1)
        print(f"Question: {question_1}")
        print(f"SQL Output:\n{sql_1}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    # ---------------------------------------------------
    # Test 2: Follow-up question WITH conversation history
    # (Should modify the previous query, not start fresh)
    # ---------------------------------------------------
    print("=" * 60)
    print("TEST 2: Follow-up question (With history)")
    print("=" * 60)
    try:
        fake_history = [
            {
                "question": "What are the top 5 product categories by total sales?",
                "sql": "SELECT product_category, SUM(sales_amount) AS total_sales FROM orders GROUP BY product_category ORDER BY total_sales DESC LIMIT 5;"
            }
        ]
        question_2 = "Now filter that for only 2024"
        sql_2 = generate_SQL_query(test_schema, question_2, conversation_history=fake_history)
        print(f"Question: {question_2}")
        print(f"SQL Output:\n{sql_2}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    # ---------------------------------------------------
    # Test 3: Completely NEW topic (should ignore history)
    # ---------------------------------------------------
    print("=" * 60)
    print("TEST 3: New topic (Should ignore history)")
    print("=" * 60)
    try:
        question_3 = "How many orders were placed from each city?"
        sql_3 = generate_SQL_query(test_schema, question_3, conversation_history=fake_history)
        print(f"Question: {question_3}")
        print(f"SQL Output:\n{sql_3}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    

