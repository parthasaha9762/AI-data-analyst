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


def clean_sql_output(raw_text: str) -> tuple:
    """
    Safely parses intent (FOLLOW_UP vs NEW_TOPIC) and cleans markdown code fences from SQL output.
    Returns a tuple of (cleaned_sql: str, is_follow_up: bool).
    """
    if not raw_text:
        return "", False

    text = raw_text.strip()
    is_follow_up = False

    # Check for intent classification tag from LLM
    if "INTENT: FOLLOW_UP" in text.upper():
        is_follow_up = True
        text = re.sub(r"^INTENT:\s*FOLLOW_UP\s*", "", text, flags=re.IGNORECASE | re.MULTILINE).strip()
    elif "INTENT: NEW_TOPIC" in text.upper():
        is_follow_up = False
        text = re.sub(r"^INTENT:\s*NEW_TOPIC\s*", "", text, flags=re.IGNORECASE | re.MULTILINE).strip()

    # Extract SQL if enclosed in code fences
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    else:
        if text.startswith("```sql"):
            text = text[6:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

    return text.strip(), is_follow_up


def generate_SQL_query(schema_context: str, user_question: str, conversation_history: list = None) -> tuple:
    """
    Generates a valid SQLite SQL query based on database schema and user question.
    Features dynamic model discovery, automatic topic shift detection, and fallback resilience.
    Returns (sql_query: str, is_follow_up: bool).
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

    # Set comprehensive, future-proof system instruction with automatic intent classification & fuzzy matching
    system_instruction_prompt = (
        "You are an expert SQLite SQL generator.\n"
        "STRICT RULES:\n"
        "1. Use ONLY table names and column names present in the DATABASE SCHEMA.\n"
        "2. Do NOT invent table names or column names.\n"
        "3. Always end valid SQL queries with a semicolon (;).\n"
        "4. Format the SQL query cleanly across multiple lines (place FROM, JOIN, WHERE, GROUP BY, ORDER BY, and LIMIT on new lines).\n"
        "5. If the user asks for derived metrics, ratios, rates, or business concepts (e.g. cancellation rate, average order value, lost revenue, high value customers, margin), compute them using standard SQL expressions (SUM, AVG, COUNT, CASE statements, and clean column aliases).\n"
        "6. Ignore any prefixes like 'Scenario 1:', 'Scenario 2:', 'Question:', or bullet points in the user input. Focus on answering the analytical intent.\n"
        "7. ONLY output the exact single keyword INVALID_QUERY if the prompt is complete gibberish (e.g. 'asdfghjkl') or completely non-analytical (e.g. 'tell me a joke').\n\n"
        "TEXT FILTERING & FUZZY MATCHING RULES:\n"
        "1. When filtering text/string columns (e.g., product names, categories, customer names, cities, brands, status), users frequently use colloquial, shortened, or partial terms (e.g., asking for 'air fryer' when the database contains 'Air Fryer v1', or 'dumbbell' for 'Dumbbell Set 5kg', or 'shoes' for 'Running Shoes Pro').\n"
        "2. Always use case-insensitive partial matching with `LIKE '%keyword%'` (or `LOWER(column) LIKE '%keyword%'`) instead of strict equality (`=`), unless an exact ID or explicit exact code is requested.\n"
        "3. For plural terms (e.g., 'air fryers', 'laptops', 'dumbbells', 'orders'), match the singular root term (e.g., `LIKE '%air fryer%'`, `LIKE '%laptop%'`, `LIKE '%dumbbell%'`).\n\n"
        "MISSING VALUE & PLACEHOLDER HANDLING RULES:\n"
        "1. The dataset auto-cleans missing text/categorical data by filling nulls with 'N/A' or 'NA'.\n"
        "2. When grouping by, listing, or analyzing categorical attributes (e.g. GROUP BY city, category, customer_name, region, status), ALWAYS exclude missing placeholder values by adding a filter (e.g., `WHERE column NOT IN ('N/A', 'NA', 'None', '') AND column IS NOT NULL` or `column != 'N/A'`), unless the user explicitly asks to view missing, unknown, or unassigned records.\n\n"
        "CONVERSATIONAL MEMORY & TOPIC SHIFT RULES:\n"
        "1. If PREVIOUS CONVERSATION is present AND the CURRENT USER QUESTION is a follow-up, refinement, or filter on the previous turns (e.g. 'now filter that', 'only top 10', 'also include city', 'exclude cancellations'), output on the very first line:\n"
        "INTENT: FOLLOW_UP\n"
        "and modify/extend the previous SQL query appropriately on subsequent lines.\n"
        "2. If the CURRENT USER QUESTION is on a NEW TOPIC unrelated to the previous turns, or if no previous conversation is provided, output on the very first line:\n"
        "INTENT: NEW_TOPIC\n"
        "and write a fresh SQL query from scratch on subsequent lines.\n"
        "3. Output ONLY the intent header and the raw executable SQL query. Do NOT include markdown code fences (like ```sql or ```), explanations, or notes."
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
                cleaned_sql, is_follow_up = clean_sql_output(response.text)

                # If model generated valid SQL (not INVALID_QUERY), accept immediately & cache model
                if cleaned_sql != "INVALID_QUERY":
                    _WORKING_MODEL = model_name
                    return cleaned_sql, is_follow_up
                else:
                    # Remember INVALID_QUERY in case all models consistently determine it's invalid
                    last_valid_response = ("INVALID_QUERY", False)

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
        sql_1, is_follow_up_1 = generate_SQL_query(test_schema, question_1)
        print(f"Question: {question_1}")
        print(f"Is Follow-Up: {is_follow_up_1}")
        print(f"SQL Output:\n{sql_1}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    # ---------------------------------------------------
    # Test 2: Follow-up question WITH conversation history
    # (Should detect FOLLOW_UP and modify previous query)
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
        sql_2, is_follow_up_2 = generate_SQL_query(test_schema, question_2, conversation_history=fake_history)
        print(f"Question: {question_2}")
        print(f"Is Follow-Up: {is_follow_up_2}")
        print(f"SQL Output:\n{sql_2}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    # ---------------------------------------------------
    # Test 4: Fuzzy / Partial product name matching
    # ---------------------------------------------------
    print("=" * 60)
    print("TEST 4: Fuzzy / Partial text match (e.g. 'air fryers')")
    print("=" * 60)
    try:
        product_schema = (
            "TABLE: products\n"
            " Columns:\n"
            "- product_id: INTEGER\n"
            "- product_name: TEXT (Sample values: 'Air Fryer v1', 'Air Fryer Pro', 'Dumbbell Set 5kg')\n"
            "TABLE: orders\n"
            " Columns:\n"
            "- order_id: INTEGER\n"
            "- product_id: INTEGER\n"
            "- quantity: INTEGER\n"
        )
        question_4 = "How many air fryers have been sold?"
        sql_4, is_follow_up_4 = generate_SQL_query(product_schema, question_4)
        print(f"Question: {question_4}")
        print(f"SQL Output:\n{sql_4}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    

