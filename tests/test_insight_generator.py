"""
Comprehensive Test Suite: Insight Generator (Offline Components)
================================================================
Tests the offline/pure-logic parts of insight_generator:
prepare_statistical_context() for DataFrame profiling.
"""
import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.insight_generator import prepare_statistical_context


# ============================================================================
# TEST: prepare_statistical_context
# ============================================================================

class TestPrepareStatisticalContext:
    """Tests for statistical context preparation from DataFrames."""

    def test_basic_context_structure(self):
        """Should return dict with required top-level keys."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        result = prepare_statistical_context(df)
        assert "total_rows" in result
        assert "columns" in result
        assert "numeric_summary" in result
        assert "sample_rows" in result

    def test_row_count_correct(self):
        """total_rows should match DataFrame length."""
        df = pd.DataFrame({"x": range(50)})
        result = prepare_statistical_context(df)
        assert result["total_rows"] == 50

    def test_columns_list(self):
        """columns should list all column names."""
        df = pd.DataFrame({"city": ["A"], "revenue": [100], "profit": [50]})
        result = prepare_statistical_context(df)
        assert result["columns"] == ["city", "revenue", "profit"]

    def test_sample_rows_limited(self):
        """sample_rows should contain at most 5 records."""
        df = pd.DataFrame({"x": range(100)})
        result = prepare_statistical_context(df)
        assert len(result["sample_rows"]) == 5

    def test_sample_rows_small_df(self):
        """DataFrame with <= 5 rows should include all."""
        df = pd.DataFrame({"x": [1, 2, 3]})
        result = prepare_statistical_context(df)
        assert len(result["sample_rows"]) == 3

    def test_numeric_summary_present(self):
        """Numeric columns should have describe() stats."""
        df = pd.DataFrame({"val": [10, 20, 30, 40, 50]})
        result = prepare_statistical_context(df)
        assert "val" in result["numeric_summary"]
        stats = result["numeric_summary"]["val"]
        assert "mean" in stats
        assert "min" in stats
        assert "max" in stats

    def test_numeric_summary_includes_sum(self):
        """Should add 'sum' to each numeric column's stats."""
        df = pd.DataFrame({"val": [10, 20, 30]})
        result = prepare_statistical_context(df)
        assert "sum" in result["numeric_summary"]["val"]
        assert result["numeric_summary"]["val"]["sum"] == 60.0

    def test_no_numeric_columns(self):
        """DataFrame with only string columns should have empty numeric_summary."""
        df = pd.DataFrame({"name": ["Alice", "Bob"], "city": ["NYC", "London"]})
        result = prepare_statistical_context(df)
        assert result["numeric_summary"] == {}

    def test_mixed_types(self):
        """Mixed DataFrame should only profile numeric columns."""
        df = pd.DataFrame({
            "name": ["A", "B", "C"],
            "score": [90, 80, 70],
            "grade": ["A", "B", "C"]
        })
        result = prepare_statistical_context(df)
        assert "score" in result["numeric_summary"]
        assert "name" not in result["numeric_summary"]
        assert "grade" not in result["numeric_summary"]

    def test_empty_dataframe(self):
        """Empty DataFrame should return error dict."""
        df = pd.DataFrame()
        result = prepare_statistical_context(df)
        assert "error" in result

    def test_none_dataframe(self):
        """None input should return error dict."""
        result = prepare_statistical_context(None)
        assert "error" in result

    def test_single_row_dataframe(self):
        """Single-row DataFrame should work without errors."""
        df = pd.DataFrame({"a": [42], "b": [99.9]})
        result = prepare_statistical_context(df)
        assert result["total_rows"] == 1
        assert len(result["sample_rows"]) == 1

    def test_large_dataframe_performance(self):
        """Large DataFrame should compute stats without errors."""
        import numpy as np
        df = pd.DataFrame({
            "id": range(100000),
            "value": np.random.randn(100000),
            "category": ["cat_" + str(i % 10) for i in range(100000)]
        })
        result = prepare_statistical_context(df)
        assert result["total_rows"] == 100000
        assert len(result["sample_rows"]) == 5
        assert "value" in result["numeric_summary"]

    def test_dataframe_with_nulls(self):
        """DataFrame with nulls should compute stats on non-null values."""
        df = pd.DataFrame({"val": [10, None, 30, None, 50]})
        result = prepare_statistical_context(df)
        # describe() should handle NaN automatically
        assert "val" in result["numeric_summary"]

    def test_multiple_numeric_columns(self):
        """All numeric columns should be profiled."""
        df = pd.DataFrame({
            "revenue": [100, 200, 300],
            "cost": [80, 150, 250],
            "profit": [20, 50, 50]
        })
        result = prepare_statistical_context(df)
        for col in ["revenue", "cost", "profit"]:
            assert col in result["numeric_summary"]
            assert "sum" in result["numeric_summary"][col]

    def test_sum_accuracy(self):
        """Sum values should be mathematically correct."""
        df = pd.DataFrame({"amount": [10.5, 20.3, 30.2]})
        result = prepare_statistical_context(df)
        assert result["numeric_summary"]["amount"]["sum"] == 61.0

    def test_return_type(self):
        """Should always return a dictionary."""
        df = pd.DataFrame({"x": [1]})
        result = prepare_statistical_context(df)
        assert isinstance(result, dict)
