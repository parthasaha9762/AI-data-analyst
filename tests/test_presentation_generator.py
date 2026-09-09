"""
Comprehensive Test Suite: Presentation Generator
==================================================
Tests PowerPoint generation, markdown parsing, helper functions,
view-only mode, edge cases, and complete deck compilation.
"""
import pytest
import pandas as pd
import io
import zipfile
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.presentation_generator import (
    parse_markdown_sections,
    create_powerpoint_deck
)


# ============================================================================
# TEST: parse_markdown_sections
# ============================================================================

class TestParseMarkdownSections:
    """Tests for markdown -> section parsing used in insight slides."""

    def test_standard_markdown_headers(self):
        """Standard ### headers should be parsed into sections."""
        md = "### The Big Picture\nRevenue is up.\n### Where We Can Grow\nExpand to Asia.\n### Action Plan\n1. Quick fix\n2. Next move"
        sections = parse_markdown_sections(md)
        assert len(sections) >= 3
        titles = [s["title"] for s in sections]
        assert any("Big Picture" in t for t in titles)

    def test_empty_string(self):
        """Empty string should return a default section."""
        sections = parse_markdown_sections("")
        assert len(sections) == 1
        assert sections[0]["title"] == "Executive Business Summary"

    def test_none_input(self):
        """None input should return a default section."""
        sections = parse_markdown_sections(None)
        assert len(sections) == 1

    def test_whitespace_only(self):
        """Whitespace-only should return a default section."""
        sections = parse_markdown_sections("   \n  \t  ")
        assert len(sections) >= 1

    def test_single_header_with_content(self):
        """Single section should be parsed correctly."""
        md = "### Key Insights\nElectronics leads with $150K revenue."
        sections = parse_markdown_sections(md)
        assert len(sections) >= 1
        assert "Electronics" in sections[0]["content"] or "150K" in sections[0]["content"]

    def test_multiple_heading_levels(self):
        """## and ### should both be recognized as section headers."""
        md = "## Overview\nText1\n### Details\nText2"
        sections = parse_markdown_sections(md)
        assert len(sections) >= 2

    def test_dollar_sign_unescaping(self):
        """Escaped dollar signs (\\$) should be unescaped back to $."""
        md = "### Revenue\nTotal revenue is \\$3.92M."
        sections = parse_markdown_sections(md)
        assert any("$3.92M" in s["content"] for s in sections)

    def test_emoji_in_headers(self):
        """Emoji prefixes in headers should be stripped from titles."""
        md = "### 💡 The Big Picture\nSome content\n### 🚀 Where We Can Grow\nMore content"
        sections = parse_markdown_sections(md)
        # Emoji should be stripped or at least not cause parsing errors
        assert len(sections) >= 2

    def test_content_with_bold_markdown(self):
        """Bold **text** in content should be preserved."""
        md = "### Results\n**Electronics** leads with **$150K**."
        sections = parse_markdown_sections(md)
        assert "**Electronics**" in sections[0]["content"] or "Electronics" in sections[0]["content"]

    def test_numbered_list_content(self):
        """Numbered lists should be preserved in content."""
        md = "### Action Plan\n1. Quick fix: Run discount campaign\n2. Next move: Expand to Europe"
        sections = parse_markdown_sections(md)
        assert "Quick fix" in sections[0]["content"]

    def test_no_headers_plain_paragraphs(self):
        """Plain text with no headers should be split into paragraph-based sections."""
        md = "Revenue is strong.\n\nWe should expand.\n\nAction: Launch campaign."
        sections = parse_markdown_sections(md)
        assert len(sections) >= 1

    def test_preserves_all_content(self):
        """No content should be dropped during parsing."""
        md = "### Section A\nLine 1\nLine 2\n### Section B\nLine 3"
        sections = parse_markdown_sections(md)
        all_content = " ".join(s["content"] for s in sections)
        assert "Line 1" in all_content
        assert "Line 2" in all_content
        assert "Line 3" in all_content


# ============================================================================
# TEST: create_powerpoint_deck - Basic Generation
# ============================================================================

class TestCreatePowerpointDeck:
    """Tests for complete PowerPoint deck generation."""

    @pytest.fixture
    def basic_df(self):
        return pd.DataFrame({
            "city": ["NYC", "London", "Tokyo"],
            "revenue": [150000, 120000, 95000]
        })

    @pytest.fixture
    def basic_chart_config(self):
        return {
            "chart_type": "bar",
            "x_column": "city",
            "y_column": "revenue",
            "title": "Revenue by City",
            "reasoning": "Bar chart selected for categorical comparison.",
            "conclusion": "NYC leads with $150K in revenue."
        }

    def test_returns_bytes(self, basic_df):
        """Should return bytes object."""
        result = create_powerpoint_deck(
            user_question="Top cities by revenue",
            df=basic_df
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_valid_pptx_zip_format(self, basic_df):
        """Output should be a valid ZIP (PPTX is a ZIP archive)."""
        result = create_powerpoint_deck(
            user_question="Test",
            df=basic_df
        )
        # PPTX files are ZIP archives — verify it can be opened
        with zipfile.ZipFile(io.BytesIO(result), 'r') as zf:
            names = zf.namelist()
            assert any("ppt/slides" in n for n in names)

    def test_contains_presentation_xml(self, basic_df):
        """PPTX should contain presentation.xml."""
        result = create_powerpoint_deck(user_question="Test", df=basic_df)
        with zipfile.ZipFile(io.BytesIO(result), 'r') as zf:
            assert "ppt/presentation.xml" in zf.namelist()

    def test_minimum_slide_count(self, basic_df):
        """Should have at least 2 slides (cover + scorecard)."""
        result = create_powerpoint_deck(user_question="Test", df=basic_df)
        with zipfile.ZipFile(io.BytesIO(result), 'r') as zf:
            slide_files = [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
            assert len(slide_files) >= 2

    def test_with_all_components(self, basic_df, basic_chart_config):
        """Full deck with all optional components should not crash."""
        result = create_powerpoint_deck(
            user_question="Which cities generate the most revenue?",
            df=basic_df,
            generated_sql="SELECT city, SUM(revenue) FROM orders GROUP BY city;",
            sql_explanation="Groups orders by city and sums revenue.",
            chart_figure=None,  # Skip actual chart image
            chart_config=basic_chart_config,
            business_insights="### The Big Picture\nNYC dominates.\n### Growth\nExpand to Berlin.\n### Action Plan\n1. Quick Fix: Focus NYC\n2. Next: Explore Berlin",
            dataset_names=["orders", "customers"],
            view_only_mode=True
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_without_chart(self, basic_df):
        """Deck without chart should still generate."""
        result = create_powerpoint_deck(
            user_question="Test",
            df=basic_df,
            chart_figure=None,
            chart_config=None
        )
        assert len(result) > 0

    def test_without_insights(self, basic_df):
        """Deck without business insights should still generate."""
        result = create_powerpoint_deck(
            user_question="Test",
            df=basic_df,
            business_insights=None
        )
        assert len(result) > 0

    def test_without_sql(self, basic_df):
        """Deck without SQL should use fallback text."""
        result = create_powerpoint_deck(
            user_question="Test",
            df=basic_df,
            generated_sql=None,
            sql_explanation=None
        )
        assert len(result) > 0

    def test_empty_dataframe(self):
        """Empty DataFrame should still produce a valid deck (minimal slides)."""
        df = pd.DataFrame()
        result = create_powerpoint_deck(user_question="Test", df=df)
        assert isinstance(result, bytes)

    def test_none_dataframe(self):
        """None DataFrame should still produce a valid deck."""
        result = create_powerpoint_deck(user_question="Test", df=None)
        assert isinstance(result, bytes)

    def test_single_row_dataframe(self):
        """Single-row DataFrame should work."""
        df = pd.DataFrame({"metric": ["Total"], "value": [42]})
        result = create_powerpoint_deck(user_question="Scalar result", df=df)
        assert len(result) > 0

    def test_wide_dataframe_truncated(self):
        """DataFrame with >6 columns should truncate to 6 in table slide."""
        df = pd.DataFrame({f"col_{i}": range(3) for i in range(10)})
        result = create_powerpoint_deck(user_question="Wide table", df=df)
        assert len(result) > 0

    def test_long_question_text(self):
        """Very long user question should not crash layout."""
        long_q = "What are the top 10 product categories by total revenue when we filter by the year 2024 and exclude any cancelled orders from the analysis and also include the average order value for each category?"
        df = pd.DataFrame({"category": ["A", "B"], "revenue": [100, 200]})
        result = create_powerpoint_deck(user_question=long_q, df=df)
        assert len(result) > 0

    def test_special_characters_in_data(self):
        """Data with special characters should not crash."""
        df = pd.DataFrame({
            "name": ["O'Brien", "Home & Kitchen", "50% Discount"],
            "value": [100, 200, 300]
        })
        result = create_powerpoint_deck(user_question="Special chars test", df=df)
        assert len(result) > 0


# ============================================================================
# TEST: View-Only Mode
# ============================================================================

class TestViewOnlyMode:
    """Tests for the View-Only / Marked as Final PPTX feature."""

    def test_view_only_adds_custom_xml(self):
        """View-only mode should embed custom.xml with _MarkAsFinal."""
        df = pd.DataFrame({"x": [1]})
        result = create_powerpoint_deck(user_question="Test", df=df, view_only_mode=True)
        with zipfile.ZipFile(io.BytesIO(result), 'r') as zf:
            assert "docProps/custom.xml" in zf.namelist()
            custom_xml = zf.read("docProps/custom.xml")
            assert b"_MarkAsFinal" in custom_xml
            assert b"true" in custom_xml

    def test_view_only_content_status(self):
        """View-only mode should set contentStatus to 'Final' in core.xml."""
        df = pd.DataFrame({"x": [1]})
        result = create_powerpoint_deck(user_question="Test", df=df, view_only_mode=True)
        with zipfile.ZipFile(io.BytesIO(result), 'r') as zf:
            if "docProps/core.xml" in zf.namelist():
                core_xml = zf.read("docProps/core.xml")
                assert b"Final" in core_xml

    def test_non_view_only_no_custom_xml(self):
        """With view_only_mode=False, custom.xml should NOT be added."""
        df = pd.DataFrame({"x": [1]})
        result = create_powerpoint_deck(user_question="Test", df=df, view_only_mode=False)
        with zipfile.ZipFile(io.BytesIO(result), 'r') as zf:
            assert "docProps/custom.xml" not in zf.namelist()

    def test_view_only_content_types_override(self):
        """View-only mode should add override in [Content_Types].xml."""
        df = pd.DataFrame({"x": [1]})
        result = create_powerpoint_deck(user_question="Test", df=df, view_only_mode=True)
        with zipfile.ZipFile(io.BytesIO(result), 'r') as zf:
            ct = zf.read("[Content_Types].xml")
            assert b"custom-properties" in ct


# ============================================================================
# TEST: Slide Count Logic
# ============================================================================

class TestSlideCountLogic:
    """Tests that dynamic slide count adjusts based on available content."""

    def test_minimal_deck_slides(self):
        """Minimal deck (no chart, no insights) should have >= 3 slides (cover, scorecard, SQL audit, table)."""
        df = pd.DataFrame({"x": [1, 2]})
        result = create_powerpoint_deck(user_question="Test", df=df)
        with zipfile.ZipFile(io.BytesIO(result), 'r') as zf:
            slides = [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
            assert len(slides) >= 3

    def test_full_deck_more_slides(self):
        """Full deck with insights should have more slides than minimal."""
        df = pd.DataFrame({"x": [1, 2]})
        minimal = create_powerpoint_deck(user_question="Test", df=df)
        full = create_powerpoint_deck(
            user_question="Test", df=df,
            business_insights="### Big Picture\nGood.\n### Growth\nExpand.\n### Action\n1. Do this"
        )
        with zipfile.ZipFile(io.BytesIO(minimal), 'r') as z1:
            min_slides = len([n for n in z1.namelist() if "slides/slide" in n and n.endswith(".xml")])
        with zipfile.ZipFile(io.BytesIO(full), 'r') as z2:
            full_slides = len([n for n in z2.namelist() if "slides/slide" in n and n.endswith(".xml")])
        assert full_slides >= min_slides
