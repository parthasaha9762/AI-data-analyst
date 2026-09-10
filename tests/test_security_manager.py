

"""
Comprehensive Test Suite: Security & PII Protection Engine
===========================================================
Tests SQL sandboxing, dangerous command blocking, SQL injection prevention,
PII column detection, and sensitive data masking for enterprise privacy.
"""
import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.security_manager import (
    is_safe_sql_query,
    detect_pii_columns,
    mask_value,
    mask_sensitive_dataframe,
    get_gemini_api_key
)


# ============================================================================
# TEST: is_safe_sql_query - Permitted Read-Only Queries
# ============================================================================

class TestSafeSqlQueryPermitted:
    """Tests for legitimate read-only analytical queries."""

    def test_simple_select(self):
        is_safe, reason = is_safe_sql_query("SELECT * FROM customers")
        assert is_safe is True

    def test_select_with_where_and_order(self):
        is_safe, _ = is_safe_sql_query("SELECT id, name FROM users WHERE age > 21 ORDER BY name DESC LIMIT 10")
        assert is_safe is True

    def test_select_with_aggregates(self):
        is_safe, _ = is_safe_sql_query("SELECT city, COUNT(*), AVG(revenue) FROM orders GROUP BY city")
        assert is_safe is True

    def test_select_with_joins(self):
        query = """
        SELECT c.customer_name, SUM(o.total_amount) as total
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_name
        """
        is_safe, _ = is_safe_sql_query(query)
        assert is_safe is True

    def test_with_cte_query(self):
        query = """
        WITH regional_sales AS (
            SELECT region, SUM(amount) as total FROM sales GROUP BY region
        )
        SELECT * FROM regional_sales WHERE total > 10000;
        """
        is_safe, _ = is_safe_sql_query(query)
        assert is_safe is True

    def test_select_with_subquery(self):
        query = "SELECT * FROM products WHERE price > (SELECT AVG(price) FROM products)"
        is_safe, _ = is_safe_sql_query(query)
        assert is_safe is True

    def test_select_containing_literal_matching_keyword(self):
        """Query containing a dangerous word inside string literal should NOT be blocked."""
        query = "SELECT * FROM logs WHERE status = 'DROP' OR action = 'DELETE_USER'"
        is_safe, _ = is_safe_sql_query(query)
        assert is_safe is True

    def test_query_with_sql_comments(self):
        query = """
        -- Analytical query to get top spenders
        SELECT customer_id, SUM(amount) 
        FROM orders /* multi-line comment */
        GROUP BY customer_id
        """
        is_safe, _ = is_safe_sql_query(query)
        assert is_safe is True


# ============================================================================
# TEST: is_safe_sql_query - Prohibited Destructive Operations
# ============================================================================

class TestSafeSqlQueryProhibited:
    """Tests for blocked destructive/modifying operations."""

    def test_drop_table(self):
        is_safe, reason = is_safe_sql_query("DROP TABLE customers")
        assert is_safe is False
        assert "prohibited" in reason.lower() or "violation" in reason.lower()

    def test_delete_from(self):
        is_safe, reason = is_safe_sql_query("DELETE FROM orders WHERE amount < 10")
        assert is_safe is False

    def test_insert_into(self):
        is_safe, reason = is_safe_sql_query("INSERT INTO customers (id, name) VALUES (1, 'Hacker')")
        assert is_safe is False

    def test_update_table(self):
        is_safe, reason = is_safe_sql_query("UPDATE users SET role = 'admin'")
        assert is_safe is False

    def test_alter_table(self):
        is_safe, reason = is_safe_sql_query("ALTER TABLE orders ADD COLUMN extra text")
        assert is_safe is False

    def test_attach_database(self):
        is_safe, reason = is_safe_sql_query("ATTACH DATABASE 'malicious.db' AS evil")
        assert is_safe is False

    def test_pragma_command(self):
        is_safe, reason = is_safe_sql_query("PRAGMA database_list")
        assert is_safe is False

    def test_truncate_table(self):
        is_safe, reason = is_safe_sql_query("TRUNCATE TABLE customers")
        assert is_safe is False

    def test_multiple_statements_injection(self):
        """Chained injection queries (e.g. SELECT 1; DROP TABLE users) must be blocked."""
        query = "SELECT * FROM customers; DROP TABLE orders;"
        is_safe, reason = is_safe_sql_query(query)
        assert is_safe is False
        assert "multiple" in reason.lower()

    def test_empty_query(self):
        is_safe, _ = is_safe_sql_query("")
        assert is_safe is False

    def test_none_query(self):
        is_safe, _ = is_safe_sql_query(None)
        assert is_safe is False

    def test_whitespace_only(self):
        is_safe, _ = is_safe_sql_query("   \n\t  ")
        assert is_safe is False


# ============================================================================
# TEST: detect_pii_columns
# ============================================================================

class TestDetectPiiColumns:
    """Tests for identifying PII columns in DataFrames."""

    def test_detects_email_column(self):
        df = pd.DataFrame({"user_id": [1, 2], "email": ["alice@test.com", "bob@test.com"]})
        pii = detect_pii_columns(df)
        assert "email" in pii

    def test_detects_phone_column(self):
        df = pd.DataFrame({"id": [1], "contact_phone": ["555-123-4567"]})
        pii = detect_pii_columns(df)
        assert "contact_phone" in pii

    def test_detects_ssn_column(self):
        df = pd.DataFrame({"id": [1], "ssn": ["123-45-6789"]})
        pii = detect_pii_columns(df)
        assert "ssn" in pii

    def test_detects_credit_card_column(self):
        df = pd.DataFrame({"id": [1], "credit_card_num": ["4111111111111111"]})
        pii = detect_pii_columns(df)
        assert "credit_card_num" in pii

    def test_detects_salary_column(self):
        df = pd.DataFrame({"emp_id": [1], "annual_salary": [120000]})
        pii = detect_pii_columns(df)
        assert "annual_salary" in pii

    def test_no_pii_in_generic_dataset(self):
        df = pd.DataFrame({"product_id": [101, 102], "category": ["Electronics", "Books"], "price": [29.99, 15.00]})
        pii = detect_pii_columns(df)
        assert len(pii) == 0

    def test_empty_dataframe(self):
        assert detect_pii_columns(pd.DataFrame()) == []

    def test_none_dataframe(self):
        assert detect_pii_columns(None) == []


# ============================================================================
# TEST: mask_value & mask_sensitive_dataframe
# ============================================================================

class TestMaskingFunctions:
    """Tests for PII value and DataFrame masking."""

    def test_mask_email_value(self):
        masked = mask_value("laura.miller@company.com", col_name="email")
        assert "laura.miller" not in masked
        assert "@company.com" in masked

    def test_mask_phone_value(self):
        masked = mask_value("555-867-5309", col_name="phone")
        assert "***-***-****" in masked

    def test_mask_ssn_value(self):
        masked = mask_value("123-45-6789", col_name="ssn")
        assert "***-**-****" in masked

    def test_mask_credit_card_value(self):
        masked = mask_value("4111222233334444", col_name="card_num")
        assert "4111" not in masked
        assert masked.endswith("4444")

    def test_mask_secret_token(self):
        masked = mask_value("sk-123456789abcdef", col_name="api_key")
        assert masked == "[REDACTED_SECRET]"

    def test_mask_dataframe_replaces_emails(self):
        df = pd.DataFrame({
            "name": ["Alice", "Bob"],
            "email": ["alice@enterprise.org", "bob@enterprise.org"],
            "score": [95, 88]
        })
        sanitized = mask_sensitive_dataframe(df)
        assert "alice@enterprise.org" not in sanitized["email"].values
        # Non-PII columns must remain intact
        assert list(sanitized["score"]) == [95, 88]

    def test_mask_dataframe_preserves_shape(self):
        df = pd.DataFrame({"email": ["a@b.com", "c@d.com"], "val": [1, 2]})
        sanitized = mask_sensitive_dataframe(df)
        assert sanitized.shape == df.shape

    def test_mask_empty_dataframe(self):
        df = pd.DataFrame()
        assert mask_sensitive_dataframe(df).empty

    def test_mask_none_dataframe(self):
        assert mask_sensitive_dataframe(None) is None


# ============================================================================
# TEST: get_gemini_api_key - API Key Resolution & Protection
# ============================================================================

class TestGetGeminiApiKey:
    """Tests secure API key resolution from environment and Streamlit secrets."""

    def test_key_from_environ(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyTestApiKey12345")
        key = get_gemini_api_key()
        assert key == "AIzaSyTestApiKey12345"

    def test_ignores_template_placeholder(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key_here")
        key = get_gemini_api_key()
        assert key == ""

    def test_returns_empty_when_unset(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        key = get_gemini_api_key()
        assert key == ""

    def test_strips_surrounding_whitespace(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "  AIzaSyCleanKey999  \n")
        key = get_gemini_api_key()
        assert key == "AIzaSyCleanKey999"

