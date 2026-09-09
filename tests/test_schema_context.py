"""
Comprehensive Test Suite: Schema Context Generator
===================================================
Tests LLM-ready schema context formatting, SQL dtype mapping, 
relationship inclusion, deduplication, and edge cases.
"""
import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.schema_context import generate_schema_context, map_dtype_to_sql


# ============================================================================
# TEST: map_dtype_to_sql
# ============================================================================

class TestMapDtypeToSql:
    """Tests for Pandas dtype -> SQL type mapping."""

    def test_int_mapping(self):
        """int64 should map to INTEGER."""
        assert map_dtype_to_sql(pd.Series([1]).dtype) == "INTEGER"

    def test_float_mapping(self):
        """float64 should map to REAL."""
        assert map_dtype_to_sql(pd.Series([1.0]).dtype) == "REAL"

    def test_object_mapping(self):
        """object (string) should map to VARCHAR."""
        assert map_dtype_to_sql(pd.Series(["text"]).dtype) == "VARCHAR"

    def test_bool_mapping(self):
        """bool should map to BOOLEAN."""
        assert map_dtype_to_sql(pd.Series([True]).dtype) == "BOOLEAN"

    def test_datetime_mapping(self):
        """datetime64 should map to TIMESTAMP."""
        assert map_dtype_to_sql(pd.Series(pd.to_datetime(["2024-01-01"])).dtype) == "TIMESTAMP"

    def test_python_int_type(self):
        """Python built-in int should map to INTEGER."""
        assert map_dtype_to_sql(int) == "INTEGER"

    def test_python_float_type(self):
        """Python built-in float should map to REAL."""
        assert map_dtype_to_sql(float) == "REAL"

    def test_python_bool_type(self):
        """Python built-in bool should map to BOOLEAN."""
        assert map_dtype_to_sql(bool) == "BOOLEAN"

    def test_unknown_type_defaults_varchar(self):
        """Unknown types should default to VARCHAR."""
        assert map_dtype_to_sql("some_unknown_type") == "VARCHAR"

    def test_int32_mapping(self):
        """int32 should also map to INTEGER."""
        dtype = pd.Series([1], dtype="int32").dtype
        assert map_dtype_to_sql(dtype) == "INTEGER"

    def test_float32_mapping(self):
        """float32 should also map to REAL."""
        dtype = pd.Series([1.0], dtype="float32").dtype
        assert map_dtype_to_sql(dtype) == "REAL"


# ============================================================================
# TEST: generate_schema_context
# ============================================================================

class TestGenerateSchemaContext:
    """Tests for LLM-ready schema context text generation."""

    def test_empty_datasets(self):
        """Empty datasets should return 'NO TABLES FOUND' message."""
        result = generate_schema_context({})
        assert "NO TABLES FOUND" in result

    def test_single_table_structure(self):
        """Single table should include table name and columns."""
        datasets = {"orders": pd.DataFrame({"order_id": [1], "amount": [100]})}
        result = generate_schema_context(datasets)
        assert "TABLE: orders" in result
        assert "order_id" in result
        assert "amount" in result

    def test_single_table_no_relationships(self):
        """Single table should show 'None (Single table dataset)' for relationships."""
        datasets = {"orders": pd.DataFrame({"id": [1]})}
        result = generate_schema_context(datasets)
        assert "None (Single table dataset)" in result

    def test_multiple_tables_listed(self):
        """Multiple tables should all appear in the output."""
        datasets = {
            "customers": pd.DataFrame({"customer_id": [1], "name": ["Alice"]}),
            "orders": pd.DataFrame({"order_id": [1], "customer_id": [1]})
        }
        result = generate_schema_context(datasets)
        assert "TABLE: customers" in result
        assert "TABLE: orders" in result

    def test_relationships_section_present(self):
        """Multi-table schema should have RELATIONSHIPS section."""
        datasets = {
            "customers": pd.DataFrame({"customer_id": [1, 2, 3]}),
            "orders": pd.DataFrame({"order_id": [1], "customer_id": [1]})
        }
        result = generate_schema_context(datasets)
        assert "RELATIONSHIPS:" in result

    def test_sql_types_in_output(self):
        """Schema context should contain SQL type names."""
        datasets = {
            "data": pd.DataFrame({
                "id": [1],
                "name": ["test"],
                "score": [99.5]
            })
        }
        result = generate_schema_context(datasets)
        assert "INTEGER" in result
        assert "VARCHAR" in result
        assert "REAL" in result

    def test_relationship_detection_automatic(self):
        """When relationships=None, detector should run automatically."""
        datasets = {
            "customers": pd.DataFrame({"customer_id": [1, 2, 3]}),
            "orders": pd.DataFrame({"order_id": [101, 102], "customer_id": [1, 2]})
        }
        result = generate_schema_context(datasets)
        # Should detect customer_id relationship
        assert "customer_id" in result

    def test_pre_supplied_relationships(self):
        """Custom relationships should be used when provided."""
        datasets = {
            "a": pd.DataFrame({"x": [1]}),
            "b": pd.DataFrame({"y": [1]})
        }
        custom_rels = [{
            "source_table": "a",
            "source_column": "x",
            "target_table": "b",
            "target_column": "y",
            "confidence_score": 90,
            "confidence_level": "HIGH"
        }]
        result = generate_schema_context(datasets, relationships=custom_rels)
        assert "a.x -> b.y" in result

    def test_deduplication_of_bidirectional_relationships(self):
        """Bidirectional relationships should be deduplicated."""
        datasets = {
            "t1": pd.DataFrame({"shared_id": [1, 2, 3]}),
            "t2": pd.DataFrame({"shared_id": [1, 2, 3]})
        }
        result = generate_schema_context(datasets)
        # Count how many times shared_id appears in relationship lines
        rel_lines = [l for l in result.split("\n") if "shared_id" in l and "->" in l]
        # Should be deduplicated to 1 direction
        assert len(rel_lines) <= 1

    def test_header_present(self):
        """Output should start with DATABASE SCHEMA header."""
        datasets = {"t": pd.DataFrame({"id": [1]})}
        result = generate_schema_context(datasets)
        assert result.startswith("DATABASE SCHEMA")

    def test_output_is_string(self):
        """Output should always be a string."""
        datasets = {"t": pd.DataFrame({"x": [1]})}
        result = generate_schema_context(datasets)
        assert isinstance(result, str)

    def test_large_multi_table_schema(self):
        """5 tables should all appear correctly."""
        datasets = {f"table_{i}": pd.DataFrame({f"col_{i}": range(10)}) for i in range(5)}
        result = generate_schema_context(datasets)
        for i in range(5):
            assert f"TABLE: table_{i}" in result

    def test_column_with_spaces_in_name(self):
        """Column names with spaces should be included."""
        datasets = {"t": pd.DataFrame({"Full Name": ["Alice"], "Order Date": ["2024-01-01"]})}
        result = generate_schema_context(datasets)
        assert "Full Name" in result
        assert "Order Date" in result
