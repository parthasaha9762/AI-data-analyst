"""
Query Validator Module
----------------------
Provides fast local heuristic checks to detect gibberish, keyboard mashing, 
repetitive character spam, or non-analytical noise before triggering LLM calls.
"""

import re

def is_meaningful_query(question: str) -> tuple[bool, str]:
    """
    Validates whether a user's question is a meaningful prompt or gibberish.
    
    Returns:
        (is_valid: bool, warning_message: str)
    """
    if not question or not question.strip():
        return False, "Question is empty. Please enter a valid data question."

    q = question.strip()

    # Rule 1: Minimum length check for meaningful query
    if len(q) < 3:
        return False, "Your question is too short. Please ask a specific question about your data (e.g., 'Show total sales')."

    # Rule 2: Check if prompt consists purely of non-alphanumeric special characters or numbers
    letters_only = re.sub(r'[^a-zA-Z]', '', q)
    if len(letters_only) == 0:
        return False, "Your query contains no readable words. Please enter a natural language question about your dataset."

    # Rule 3: Repetitive character spam detection (e.g. "aaaaaa", "asdfasdfasdf")
    if re.search(r'(.)\1{4,}', q):
        return False, "Your input appears to be repeated character spam. Please ask a natural language question about your data."

    words = [w.lower() for w in re.findall(r'[a-zA-Z]+', q)]

    # Rule 4: Keyboard mashing / Low Vowel Ratio check for longer single words or continuous tokens
    # English words typically have at least 20-30% vowels ('a', 'e', 'i', 'o', 'u', 'y')
    vowels = set("aeiouy")
    
    for word in words:
        if len(word) >= 5:
            vowel_count = sum(1 for char in word if char in vowels)
            vowel_ratio = vowel_count / len(word)

            # If a word longer than 5 chars has less than 15% vowels (e.g. "asdfghjk", "qwrtpsdf"), flag as gibberish
            if vowel_ratio < 0.15:
                return False, f"The word '{word}' looks like random letters. Please enter a clear question about your data (e.g. 'Show total sales by category')."

    # Rule 5: Check for common keyboard mashing sequences (e.g. "asdfgh", "dfghjk", "qwerty", "zxcvbn")
    keyboard_patterns = ["asdfgh", "dfghjk", "qwerty", "zxcvbn", "hjkl;", "123456", "asdfasdf"]
    q_lower = q.lower()
    for pattern in keyboard_patterns:
        if pattern in q_lower:
            return False, "Your question contains random keyboard mashing. Please ask a specific data analysis question."

    return True, ""


# Quick standalone test
if __name__ == "__main__":
    test_cases = [
        "What are the top 5 sales by category?",
        "asdfghjkl",
        "qwerty12345",
        "aaaaaaa",
        "123456789",
        "Show total revenue for 2024",
        "dfghjkl;"
    ]

    print("=== TESTING QUERY VALIDATOR ===")
    for test in test_cases:
        valid, msg = is_meaningful_query(test)
        status = "VALID" if valid else f"INVALID ({msg})"
        print(f"Query: '{test}' -> {status}")
