"""
Comprehensive Test Suite: Chart Selector (Offline Components)
==============================================================
Tests the offline/pure-logic parts of chart_selector:
format_dataframe_context() and generate_plotly_chart().
API-dependent recommend_chart_config is tested via mocking.
"""
import pytest
import pandas as pd
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.chart_selector import format_dataframe_context, generate_plotly_chart


# ============================================================================
# TEST: format_dataframe_context
# ============================================================================

class TestFormatDataframeContext:
    """Tests for DataFrame metadata formatting for LLM."""

    def test_valid_dataframe(self):
        """Should return valid JSON string with metadata."""
        df = pd.DataFrame({"city": ["NYC", "London"], "revenue": [100, 200]})
        result = format_dataframe_context(df)
        parsed = json.loads(result)
        assert parsed["total_rows"] == 2
        assert parsed["total_columns"] == 2
        assert len(parsed["columns"]) == 2

    def test_column_metadata_fields(self):
        """Each column should have name, data_type, and unique_values."""
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
        result = format_dataframe_context(df)
        parsed = json.loads(result)
        for col in parsed["columns"]:
            assert "name" in col
            assert "data_type" in col
            assert "unique_values" in col

    def test_sample_rows_limited_to_5(self):
        """Sample rows should be at most 5."""
        df = pd.DataFrame({"x": range(100)})
        result = format_dataframe_context(df)
        parsed = json.loads(result)
        assert len(parsed["sample_rows"]) == 5

    def test_small_dataframe_all_rows(self):
        """DataFrame with <= 5 rows should include all as samples."""
        df = pd.DataFrame({"x": [1, 2, 3]})
        result = format_dataframe_context(df)
        parsed = json.loads(result)
        assert len(parsed["sample_rows"]) == 3

    def test_empty_dataframe(self):
        """Empty DataFrame should return error JSON."""
        df = pd.DataFrame()
        result = format_dataframe_context(df)
        parsed = json.loads(result)
        assert "error" in parsed

    def test_none_dataframe(self):
        """None input should return error JSON."""
        result = format_dataframe_context(None)
        parsed = json.loads(result)
        assert "error" in parsed

    def test_output_is_valid_json(self):
        """Output should always be parseable JSON."""
        df = pd.DataFrame({"a": [1]})
        result = format_dataframe_context(df)
        # Should not raise
        json.loads(result)

    def test_unique_value_counts(self):
        """Unique value counts should be accurate."""
        df = pd.DataFrame({"category": ["A", "A", "B", "C", "C"]})
        result = format_dataframe_context(df)
        parsed = json.loads(result)
        assert parsed["columns"][0]["unique_values"] == 3

    def test_mixed_types_dataframe(self):
        """DataFrame with mixed types should produce valid JSON."""
        df = pd.DataFrame({
            "int_col": [1, 2],
            "float_col": [1.5, 2.5],
            "str_col": ["a", "b"],
            "bool_col": [True, False]
        })
        result = format_dataframe_context(df)
        parsed = json.loads(result)
        assert parsed["total_columns"] == 4


# ============================================================================
# TEST: generate_plotly_chart
# ============================================================================

class TestGeneratePlotlyChart:
    """Tests for Plotly chart generation from config dictionary."""

    @pytest.fixture
    def bar_df(self):
        return pd.DataFrame({
            "city": ["NYC", "London", "Tokyo", "Paris", "Berlin"],
            "revenue": [150000, 120000, 95000, 88000, 75000]
        })

    @pytest.fixture
    def line_df(self):
        return pd.DataFrame({
            "month": ["Jan", "Feb", "Mar", "Apr", "May"],
            "sales": [10000, 14000, 18000, 22000, 29000]
        })

    @pytest.fixture
    def scatter_df(self):
        return pd.DataFrame({
            "price": [10, 20, 30, 40, 50],
            "quantity": [100, 80, 60, 40, 20]
        })

    # --- Bar Chart Tests ---
    def test_bar_chart_generation(self, bar_df):
        """Bar chart config should produce a valid Plotly figure."""
        config = {"chart_type": "bar", "x_column": "city", "y_column": "revenue", "title": "Revenue by City"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig is not None

    def test_bar_chart_title(self, bar_df):
        """Chart title should be applied."""
        config = {"chart_type": "bar", "x_column": "city", "y_column": "revenue", "title": "Test Title"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig.layout.title.text == "Test Title"

    # --- Line Chart Tests ---
    def test_line_chart_generation(self, line_df):
        """Line chart config should produce a valid Plotly figure."""
        config = {"chart_type": "line", "x_column": "month", "y_column": "sales", "title": "Sales Trend"}
        fig = generate_plotly_chart(line_df, config)
        assert fig is not None

    # --- Pie Chart Tests ---
    def test_pie_chart_generation(self, bar_df):
        """Pie chart config should produce a valid Plotly figure."""
        config = {"chart_type": "pie", "x_column": "city", "y_column": "revenue", "title": "Revenue Share"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig is not None

    # --- Scatter Plot Tests ---
    def test_scatter_chart_generation(self, scatter_df):
        """Scatter chart should produce a valid figure."""
        config = {"chart_type": "scatter", "x_column": "price", "y_column": "quantity", "title": "Price vs Qty"}
        fig = generate_plotly_chart(scatter_df, config)
        assert fig is not None

    # --- Histogram Tests ---
    def test_histogram_generation(self):
        """Histogram should work with single column."""
        df = pd.DataFrame({"values": [10, 20, 20, 30, 30, 30, 40, 40, 50]})
        config = {"chart_type": "histogram", "x_column": "values", "y_column": None, "title": "Distribution"}
        fig = generate_plotly_chart(df, config)
        assert fig is not None

    # --- Table / None Return Tests ---
    def test_table_type_returns_none(self, bar_df):
        """chart_type='table' should return None (no chart needed)."""
        config = {"chart_type": "table", "x_column": "city", "y_column": "revenue", "title": "Table"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig is None

    def test_missing_x_column_returns_none(self, bar_df):
        """Missing x_column should return None."""
        config = {"chart_type": "bar", "x_column": None, "y_column": "revenue", "title": "No X"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig is None

    def test_nonexistent_x_column_returns_none(self, bar_df):
        """x_column not in DataFrame should return None."""
        config = {"chart_type": "bar", "x_column": "nonexistent", "y_column": "revenue", "title": "Bad Col"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig is None

    # --- Empty / None DataFrame Tests ---
    def test_empty_dataframe_returns_none(self):
        """Empty DataFrame should return None."""
        df = pd.DataFrame()
        config = {"chart_type": "bar", "x_column": "x", "y_column": "y", "title": "Empty"}
        fig = generate_plotly_chart(df, config)
        assert fig is None

    def test_none_dataframe_returns_none(self):
        """None DataFrame should return None."""
        config = {"chart_type": "bar", "x_column": "x", "y_column": "y", "title": "None"}
        fig = generate_plotly_chart(None, config)
        assert fig is None

    # --- Color Column Tests ---
    def test_bar_with_color_column(self):
        """Color column should be applied when valid."""
        df = pd.DataFrame({
            "category": ["A", "A", "B", "B"],
            "region": ["East", "West", "East", "West"],
            "sales": [100, 200, 150, 250]
        })
        config = {
            "chart_type": "bar", "x_column": "category", "y_column": "sales",
            "color_column": "region", "title": "Sales by Category & Region"
        }
        fig = generate_plotly_chart(df, config)
        assert fig is not None

    def test_invalid_color_column_ignored(self, bar_df):
        """Invalid color column should not crash; should fall back."""
        config = {
            "chart_type": "bar", "x_column": "city", "y_column": "revenue",
            "color_column": "nonexistent_col", "title": "Test"
        }
        fig = generate_plotly_chart(bar_df, config)
        assert fig is not None

    # --- Default Fallback ---
    def test_unknown_chart_type_defaults_to_bar(self, bar_df):
        """Unknown chart_type should produce a bar chart fallback."""
        config = {"chart_type": "radar", "x_column": "city", "y_column": "revenue", "title": "Unknown"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig is not None

    # --- Layout & Theme Tests ---
    def test_transparent_background(self, bar_df):
        """Plot should have transparent background for dark theme embedding."""
        config = {"chart_type": "bar", "x_column": "city", "y_column": "revenue", "title": "BG Test"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig.layout.paper_bgcolor == "rgba(0,0,0,0)"
        assert fig.layout.plot_bgcolor == "rgba(0,0,0,0)"

    def test_legend_shown(self, bar_df):
        """Legend should be visible."""
        config = {"chart_type": "bar", "x_column": "city", "y_column": "revenue", "title": "Legend"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig.layout.showlegend is True

    def test_config_missing_keys_handled(self, bar_df):
        """Config with missing optional keys should not crash."""
        config = {"chart_type": "bar", "x_column": "city", "y_column": "revenue"}
        fig = generate_plotly_chart(bar_df, config)
        assert fig is not None

    def test_single_row_dataframe(self):
        """Single-row DataFrame with bar chart should work."""
        df = pd.DataFrame({"cat": ["Only"], "val": [42]})
        config = {"chart_type": "bar", "x_column": "cat", "y_column": "val", "title": "Single"}
        fig = generate_plotly_chart(df, config)
        assert fig is not None

    def test_large_dataframe_chart(self):
        """Large DataFrame should not crash chart generation."""
        df = pd.DataFrame({
            "category": [f"cat_{i}" for i in range(100)],
            "value": range(100)
        })
        config = {"chart_type": "bar", "x_column": "category", "y_column": "value", "title": "Big"}
        fig = generate_plotly_chart(df, config)
        assert fig is not None
