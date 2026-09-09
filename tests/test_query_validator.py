"""
Comprehensive Test Suite: Query Validator
==========================================
Tests the is_meaningful_query() heuristic validator with extensive edge cases
including gibberish, keyboard mashing, special characters, short queries,
empty inputs, and valid analytical questions.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.query_validator import is_meaningful_query


# ============================================================================
# TEST: Valid Analytical Queries (Should PASS)
# ============================================================================

class TestValidQueries:
    """Queries that should be classified as meaningful."""

    def test_standard_analytical_question(self):
        is_valid, msg = is_meaningful_query("What are the top 5 sales by category?")
        assert is_valid is True
        assert msg == ""

    def test_revenue_question(self):
        is_valid, _ = is_meaningful_query("Show total revenue for 2024")
        assert is_valid is True

    def test_count_question(self):
        is_valid, _ = is_meaningful_query("How many customers are there?")
        assert is_valid is True

    def test_comparison_question(self):
        is_valid, _ = is_meaningful_query("Compare sales between NYC and London")
        assert is_valid is True

    def test_trend_question(self):
        is_valid, _ = is_meaningful_query("Show monthly sales trends")
        assert is_valid is True

    def test_top_n_question(self):
        is_valid, _ = is_meaningful_query("Top 10 products by profit margin")
        assert is_valid is True

    def test_question_with_numbers(self):
        is_valid, _ = is_meaningful_query("Revenue by category in 2023")
        assert is_valid is True

    def test_short_but_valid(self):
        """3-character minimum should pass for short valid queries."""
        is_valid, _ = is_meaningful_query("sum")
        assert is_valid is True

    def test_question_with_special_chars(self):
        is_valid, _ = is_meaningful_query("What's the avg order value?")
        assert is_valid is True

    def test_question_with_parentheses(self):
        is_valid, _ = is_meaningful_query("Total sales (excluding refunds)")
        assert is_valid is True

    def test_multiword_natural_language(self):
        is_valid, _ = is_meaningful_query("I want to see the total amount spent by each customer grouped by their city")
        assert is_valid is True

    def test_query_with_sql_keywords(self):
        is_valid, _ = is_meaningful_query("SELECT all users WHERE city is Tokyo")
        assert is_valid is True

    def test_follow_up_style(self):
        is_valid, _ = is_meaningful_query("now filter to top 10")
        assert is_valid is True


# ============================================================================
# TEST: Empty / Too Short Inputs (Should FAIL)
# ============================================================================

class TestEmptyAndShortInputs:
    """Empty or extremely short inputs should be rejected."""

    def test_empty_string(self):
        is_valid, msg = is_meaningful_query("")
        assert is_valid is False
        assert "empty" in msg.lower()

    def test_none_input(self):
        is_valid, msg = is_meaningful_query(None)
        assert is_valid is False

    def test_whitespace_only(self):
        is_valid, msg = is_meaningful_query("   ")
        assert is_valid is False

    def test_single_character(self):
        is_valid, msg = is_meaningful_query("a")
        assert is_valid is False
        assert "too short" in msg.lower()

    def test_two_characters(self):
        is_valid, msg = is_meaningful_query("hi")
        assert is_valid is False
        assert "too short" in msg.lower()

    def test_tab_and_newline_only(self):
        is_valid, _ = is_meaningful_query("\t\n")
        assert is_valid is False


# ============================================================================
# TEST: Numbers / Special Characters Only (Should FAIL)
# ============================================================================

class TestNonAlphabeticInputs:
    """Inputs with no alphabetic characters should be rejected."""

    def test_numbers_only(self):
        is_valid, msg = is_meaningful_query("123456789")
        assert is_valid is False
        assert "no readable words" in msg.lower()

    def test_special_chars_only(self):
        is_valid, msg = is_meaningful_query("@#$%^&*()")
        assert is_valid is False

    def test_dots_and_dashes_only(self):
        is_valid, msg = is_meaningful_query("...---...")
        assert is_valid is False

    def test_emoji_only(self):
        """Pure emoji should fail (no letter content)."""
        is_valid, msg = is_meaningful_query("🎉🎊🎈")
        assert is_valid is False


# ============================================================================
# TEST: Repetitive Character Spam (Should FAIL)
# ============================================================================

class TestRepetitiveSpam:
    """Repeated character spam should be detected and rejected."""

    def test_repeated_letters(self):
        is_valid, msg = is_meaningful_query("aaaaaaa")
        assert is_valid is False
        assert "spam" in msg.lower() or "repeated" in msg.lower()

    def test_repeated_pattern(self):
        """Repeated identical characters should be caught."""
        is_valid, msg = is_meaningful_query("zzzzzzzzzzz")
        assert is_valid is False

    def test_long_single_char_spam(self):
        is_valid, _ = is_meaningful_query("xxxxxxxxxxxxxxxxxxxxxx")
        assert is_valid is False

    def test_borderline_repetition(self):
        """4 repetitions should pass (threshold is 5+)."""
        is_valid, _ = is_meaningful_query("ahhh what is the total")
        # 'hhhh' is 4 repetitions — should not trigger the 5+ rule
        # But "ahhh" has 3 h's — should pass
        assert is_valid is True


# ============================================================================
# TEST: Keyboard Mashing / Gibberish (Should FAIL)
# ============================================================================

class TestGibberish:
    """Random keyboard mashing should be detected."""

    def test_asdfghjkl(self):
        is_valid, msg = is_meaningful_query("asdfghjkl")
        assert is_valid is False

    def test_qwerty(self):
        is_valid, msg = is_meaningful_query("qwerty12345")
        assert is_valid is False

    def test_zxcvbn(self):
        is_valid, msg = is_meaningful_query("zxcvbn")
        assert is_valid is False

    def test_dfghjk(self):
        is_valid, msg = is_meaningful_query("dfghjkl;")
        assert is_valid is False

    def test_low_vowel_gibberish(self):
        """Words with <15% vowels should be flagged."""
        is_valid, msg = is_meaningful_query("bcdfghjklmnp")
        assert is_valid is False
        assert "random" in msg.lower() or "looks like" in msg.lower()

    def test_random_consonant_soup(self):
        is_valid, _ = is_meaningful_query("brkwtnfsplvdg")
        assert is_valid is False

    def test_mixed_gibberish_with_numbers(self):
        is_valid, _ = is_meaningful_query("asdfgh 12345")
        assert is_valid is False


# ============================================================================
# TEST: Edge Cases & Boundary Conditions
# ============================================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_exactly_three_characters(self):
        """Minimum length (3) should pass if valid word."""
        is_valid, _ = is_meaningful_query("sum")
        assert is_valid is True

    def test_valid_with_numbers_mixed(self):
        """Valid question with numbers should pass."""
        is_valid, _ = is_meaningful_query("Top 5 cities by revenue in Q3 2024")
        assert is_valid is True

    def test_very_long_valid_question(self):
        """Very long but valid question should pass."""
        long_q = "What are the top 10 product categories by total revenue when we filter by the year 2024 and exclude any cancelled orders from the analysis and also include the average order value for each category?"
        is_valid, _ = is_meaningful_query(long_q)
        assert is_valid is True

    def test_question_with_leading_trailing_spaces(self):
        """Leading/trailing spaces should be stripped before validation."""
        is_valid, _ = is_meaningful_query("   Show total revenue   ")
        assert is_valid is True

    def test_single_valid_word(self):
        """Single meaningful word >= 3 chars should pass."""
        is_valid, _ = is_meaningful_query("revenue")
        assert is_valid is True

    def test_return_type_always_tuple(self):
        """Return value should always be a tuple of (bool, str)."""
        result = is_meaningful_query("test query")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_sentence_with_keyboard_pattern_inside_word(self):
        """A valid sentence containing 'qwerty' substring should fail."""
        is_valid, _ = is_meaningful_query("I typed qwerty on my keyboard")
        assert is_valid is False

    def test_unicode_characters(self):
        """Unicode/non-ASCII characters in a valid question."""
        is_valid, _ = is_meaningful_query("Sales in Zürich and São Paulo")
        assert is_valid is True

    def test_all_caps_question(self):
        """ALL CAPS valid question should pass."""
        is_valid, _ = is_meaningful_query("SHOW TOTAL SALES BY REGION")
        assert is_valid is True
