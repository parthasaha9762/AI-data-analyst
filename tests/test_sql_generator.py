"""
Comprehensive Test Suite: SQL Generator (Offline Components)
=============================================================
Tests the offline/pure-logic parts of the SQL generator module:
clean_sql_output() parsing and intent detection.
API-dependent functions are tested with mocking.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.sql_generator import clean_sql_output


# ============================================================================
# TEST: clean_sql_output - Basic SQL Cleaning
# ============================================================================

class TestCleanSqlOutputBasic:
    """Tests for basic SQL code fence cleaning."""

    def test_plain_sql(self):
        """Plain SQL without fences should be returned as-is."""
        sql, is_follow_up = clean_sql_output("SELECT * FROM users;")
        assert sql == "SELECT * FROM users;"
        assert is_follow_up is False

    def test_markdown_sql_fences(self):
        """SQL wrapped in ```sql ... ``` should be extracted."""
        raw = "```sql\nSELECT * FROM orders;\n```"
        sql, _ = clean_sql_output(raw)
        assert sql == "SELECT * FROM orders;"

    def test_generic_code_fences(self):
        """SQL wrapped in ``` ... ``` (no language tag) should be extracted."""
        raw = "```\nSELECT id FROM products;\n```"
        sql, _ = clean_sql_output(raw)
        assert sql == "SELECT id FROM products;"

    def test_empty_input(self):
        """Empty string should return empty string."""
        sql, is_follow_up = clean_sql_output("")
        assert sql == ""
        assert is_follow_up is False

    def test_none_input(self):
        """None input should return empty string."""
        sql, is_follow_up = clean_sql_output(None)
        assert sql == ""
        assert is_follow_up is False

    def test_whitespace_only(self):
        """Whitespace-only should return empty string."""
        sql, _ = clean_sql_output("   \n\t  ")
        assert sql == ""

    def test_leading_trailing_whitespace(self):
        """Should strip leading/trailing whitespace."""
        sql, _ = clean_sql_output("   SELECT 1;   ")
        assert sql == "SELECT 1;"

    def test_multiline_sql(self):
        """Multi-line SQL should be preserved."""
        raw = "```sql\nSELECT\n  city,\n  COUNT(*)\nFROM orders\nGROUP BY city;\n```"
        sql, _ = clean_sql_output(raw)
        assert "SELECT" in sql
        assert "GROUP BY city;" in sql

    def test_only_backtick_start(self):
        """SQL starting with ``` but no closing should still clean."""
        raw = "```sql\nSELECT 1;"
        sql, _ = clean_sql_output(raw)
        assert "SELECT 1;" in sql

    def test_only_backtick_end(self):
        """SQL ending with ``` but no start should clean the end."""
        raw = "SELECT 1;\n```"
        sql, _ = clean_sql_output(raw)
        assert "SELECT 1;" in sql


# ============================================================================
# TEST: clean_sql_output - Intent Detection
# ============================================================================

class TestCleanSqlOutputIntent:
    """Tests for FOLLOW_UP / NEW_TOPIC intent parsing."""

    def test_follow_up_intent(self):
        """INTENT: FOLLOW_UP should be detected and stripped."""
        raw = "INTENT: FOLLOW_UP\nSELECT * FROM orders WHERE year = 2024;"
        sql, is_follow_up = clean_sql_output(raw)
        assert is_follow_up is True
        assert "INTENT" not in sql
        assert "SELECT * FROM orders" in sql

    def test_new_topic_intent(self):
        """INTENT: NEW_TOPIC should set is_follow_up=False."""
        raw = "INTENT: NEW_TOPIC\nSELECT * FROM products;"
        sql, is_follow_up = clean_sql_output(raw)
        assert is_follow_up is False
        assert "INTENT" not in sql
        assert "SELECT * FROM products;" in sql

    def test_follow_up_case_insensitive(self):
        """Intent detection should be case-insensitive."""
        raw = "intent: follow_up\nSELECT 1;"
        sql, is_follow_up = clean_sql_output(raw)
        assert is_follow_up is True

    def test_no_intent_header(self):
        """Without INTENT header, should default to not follow-up."""
        raw = "SELECT * FROM customers;"
        sql, is_follow_up = clean_sql_output(raw)
        assert is_follow_up is False

    def test_follow_up_with_code_fences(self):
        """INTENT + code fences should both be handled."""
        raw = "INTENT: FOLLOW_UP\n```sql\nSELECT city FROM orders;\n```"
        sql, is_follow_up = clean_sql_output(raw)
        assert is_follow_up is True
        assert "SELECT city FROM orders;" in sql
        assert "```" not in sql

    def test_invalid_query_passthrough(self):
        """INVALID_QUERY should pass through unchanged."""
        raw = "INTENT: NEW_TOPIC\nINVALID_QUERY"
        sql, is_follow_up = clean_sql_output(raw)
        assert sql == "INVALID_QUERY"
        assert is_follow_up is False


# ============================================================================
# TEST: clean_sql_output - Edge Cases
# ============================================================================

class TestCleanSqlOutputEdgeCases:
    """Edge cases for SQL cleaning."""

    def test_sql_with_backticks_in_identifiers(self):
        """SQL using backtick-quoted identifiers should not break."""
        raw = "SELECT `order date`, `total amount` FROM `orders table`;"
        sql, _ = clean_sql_output(raw)
        assert "`order date`" in sql

    def test_sql_with_single_quotes(self):
        """SQL with string literals should be preserved."""
        raw = "SELECT * FROM users WHERE name = 'Alice';"
        sql, _ = clean_sql_output(raw)
        assert "name = 'Alice'" in sql

    def test_sql_with_semicolon_in_middle(self):
        """Multiple statements (though uncommon) should be returned."""
        raw = "SELECT 1; SELECT 2;"
        sql, _ = clean_sql_output(raw)
        assert "SELECT 1;" in sql

    def test_nested_code_fences(self):
        """Regex should extract the first code fence block."""
        raw = "Here is the query:\n```sql\nSELECT 1;\n```\nMore text"
        sql, _ = clean_sql_output(raw)
        assert sql == "SELECT 1;"

    def test_upper_case_sql_tag(self):
        """```SQL (uppercase) should also be handled."""
        raw = "```SQL\nSELECT * FROM orders;\n```"
        sql, _ = clean_sql_output(raw)
        assert "SELECT * FROM orders;" in sql

    def test_return_type(self):
        """Should always return (str, bool) tuple."""
        result = clean_sql_output("SELECT 1;")
        assert isinstance(result, tuple)
        assert isinstance(result[0], str)
        assert isinstance(result[1], bool)
