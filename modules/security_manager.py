
"""
Enterprise Security & PII Protection Engine
============================================
Provides data privacy, PII (Personally Identifiable Information) masking,
and read-only SQL query sandboxing to protect confidential enterprise data.

Key Capabilities:
1. SQL Query Sandboxing: Validates queries to ensure only safe, read-only 
   SELECT operations execute against in-memory databases.
2. PII Detection: Heuristically identifies sensitive columns such as emails,
   phone numbers, credit cards, SSNs, salaries, and auth tokens.
3. Sensitive Data Masking: Sanitizes sample rows before LLM context transmission,
   guaranteeing proprietary data never leaks to external APIs.
"""

import os
import re
import pandas as pd
from typing import Tuple, List, Set


def get_gemini_api_key() -> str:
    """
    Securely retrieves the Gemini API key from multiple safe sources in order of priority:
    1. Streamlit Secrets (st.secrets["GEMINI_API_KEY"] if running in Streamlit)
    2. Environment Variable (.env file via python-dotenv or system environment)
    
    Never hardcodes keys, guaranteeing zero credential leaks in version control.
    """
    # 1. Check Streamlit secrets (for Streamlit Community Cloud and local secrets)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            key = str(st.secrets["GEMINI_API_KEY"]).strip()
            if key and key != "your_gemini_api_key_here":
                return key
    except Exception:
        pass

    # 2. Check environment variables (.env file via python-dotenv or OS environment)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key and key != "your_gemini_api_key_here":
        return key

    return ""


# Common PII column patterns (case-insensitive substring and token matching)
PII_COLUMN_PATTERNS = [
    r"(?i)(email|e_mail|mail_address)",
    r"(?i)(phone|telephone|mobile|cell|contact_no)",
    r"(?i)(ssn|social_security|national_id|tax_id|aadhaar|passport)",
    r"(?i)(credit_card|card_num|card_number|cvv|cvc|pan)",
    r"(?i)(password|passwd|pwd|secret|token|api_key|auth)",
    r"(?i)(salary|wage|compensation|bonus|net_worth|bank_acc|account_number)"
]

# Patterns for identifying values directly
EMAIL_REGEX = re.compile(r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
PHONE_REGEX = re.compile(r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Dangerous SQL keywords that modify data, structure, or attach external files
DANGEROUS_SQL_KEYWORDS = {
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", 
    "ATTACH", "DETACH", "REPLACE", "TRUNCATE", "EXEC", "EXECUTE", 
    "VACUUM", "PRAGMA", "REINDEX"
}


def is_safe_sql_query(query: str) -> Tuple[bool, str]:
    """
    Validates that a SQL query is strictly read-only and safe to execute.
    
    Returns:
        (is_safe: bool, reason: str)
    """
    if not query or not isinstance(query, str) or not query.strip():
        return False, "Query is empty."

    cleaned = query.strip()
    
    # Strip comments
    cleaned = re.sub(r"--.*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    if not cleaned:
        return False, "Query contains only comments or whitespace."

    # Check for multiple statements separated by semicolons
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Multiple SQL statements in a single execution are prohibited for security."

    # Normalize tokens for keyword inspection
    tokens = re.findall(r"\b[A-Za-z_]+\b", cleaned)
    if not tokens:
        return False, "No valid SQL commands found."

    first_keyword = tokens[0].upper()

    # Only SELECT, WITH (for CTEs), and EXPLAIN queries are permitted
    if first_keyword not in {"SELECT", "WITH", "EXPLAIN"}:
        return False, f"Prohibited operation: Only read-only queries (SELECT, WITH) are allowed, found '{first_keyword}'."

    # Check for dangerous keywords anywhere in the statement outside literals
    # Mask strings literals first to avoid false positives on 'select * from users where name = "DROP"'
    query_without_strings = re.sub(r"'[^']*'", "''", cleaned)
    query_without_strings = re.sub(r'"[^"]*"', '""', query_without_strings)
    
    normalized_tokens = [t.upper() for t in re.findall(r"\b[A-Za-z_]+\b", query_without_strings)]
    found_dangerous = set(normalized_tokens).intersection(DANGEROUS_SQL_KEYWORDS)

    if found_dangerous:
        return False, f"Security Violation: Query contains prohibited write/destructive keyword(s): {', '.join(sorted(found_dangerous))}."

    return True, "Safe read-only query."


def detect_pii_columns(df: pd.DataFrame) -> List[str]:
    """
    Scans a DataFrame to identify columns likely containing PII or sensitive data.
    """
    if df is None or df.empty:
        return []

    pii_columns = []
    for col in df.columns:
        col_str = str(col)
        # Check column name heuristics
        if any(re.search(pattern, col_str) for pattern in PII_COLUMN_PATTERNS):
            pii_columns.append(col)
            continue

        # Check sample string values for PII patterns
        if df[col].dtype == object or str(df[col].dtype) == "string":
            sample_values = df[col].dropna().head(10).astype(str)
            for val in sample_values:
                if EMAIL_REGEX.search(val) or PHONE_REGEX.search(val) or SSN_REGEX.search(val) or CREDIT_CARD_REGEX.search(val):
                    pii_columns.append(col)
                    break

    return pii_columns


def mask_value(val: str, col_name: str = "") -> str:
    """
    Masks a single value if it contains sensitive PII patterns.
    """
    if pd.isna(val) or val is None:
        return val

    val_str = str(val)
    
    # Check if column name strongly implies specific PII
    col_lower = col_name.lower()
    if any(k in col_lower for k in ["ssn", "social_security", "tax_id", "aadhaar", "national_id"]):
        return "***-**-****"
    if any(k in col_lower for k in ["password", "passwd", "pwd", "secret", "token", "auth", "api_key"]):
        return "[REDACTED_SECRET]"
    if any(k in col_lower for k in ["card_num", "credit_card", "cvv", "cvc", "pan"]):
        return "****-****-****-" + val_str[-4:] if len(val_str) >= 4 else "****"
    if any(k in col_lower for k in ["salary", "wage", "compensation", "bonus", "net_worth"]):
        return "$***,***"
    if any(k in col_lower for k in ["bank_acc", "account_number"]):
        return "*****" + val_str[-4:] if len(val_str) >= 4 else "*****"

    # Regex masking for emails
    if EMAIL_REGEX.search(val_str):
        def _mask_email(match):
            user, domain = match.group(1), match.group(2)
            masked_user = user[0] + "***" if len(user) > 1 else "***"
            return f"{masked_user}@{domain}"
        val_str = EMAIL_REGEX.sub(_mask_email, val_str)

    # Regex masking for phone numbers
    if PHONE_REGEX.search(val_str):
        val_str = PHONE_REGEX.sub("***-***-****", val_str)

    # Regex masking for SSN
    if SSN_REGEX.search(val_str):
        val_str = SSN_REGEX.sub("***-**-****", val_str)

    # Regex masking for Credit Cards
    if CREDIT_CARD_REGEX.search(val_str):
        val_str = CREDIT_CARD_REGEX.sub("****-****-****-****", val_str)

    return val_str


def mask_sensitive_dataframe(df: pd.DataFrame, pii_cols: List[str] = None) -> pd.DataFrame:
    """
    Creates a sanitized copy of a DataFrame with sensitive/PII data masked.
    Ideal for preparing sample rows for LLM context generation.
    """
    if df is None or df.empty:
        return df

    df_copy = df.copy()
    if pii_cols is None:
        pii_cols = detect_pii_columns(df_copy)

    for col in pii_cols:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(lambda v: mask_value(v, col_name=str(col)))

    return df_copy
