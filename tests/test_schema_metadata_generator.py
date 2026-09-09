"""
Comprehensive Test Suite: Schema Metadata Generator
====================================================
Tests schema extraction, column metadata analysis, JSON serialization,
multi-table generation, and edge cases for various DataFrame structures.
"""
import pytest
import pandas as pd
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.schema_metadata_generator import (
    generate_table_schema,
    schema_to_Json,
    generate_multiple_schemas
)


# ============================================================================
# TEST: generate_table_schema
# ============================================================================

class TestGenerateTableSchema:
    """Tests for single-table schema metadata generation."""

    def test_basic_schema_structure(self):
        """Verify returned dict has all required top-level keys."""
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        schema = generate_table_schema(df, "test")
        assert "table name" in schema
        assert "row count" in schema
        assert "column count" in schema
        assert "columns" in schema

    def test_table_name_preserved(self):
        """Table name should be exactly as passed."""
        df = pd.DataFrame({"x": [1]})
        schema = generate_table_schema(df, "my_table_123")
        assert schema["table name"] == "my_table_123"

    def test_row_count_correct(self):
        """Row count should match DataFrame length."""
        df = pd.DataFrame({"a": range(100)})
        schema = generate_table_schema(df, "t")
        assert schema["row count"] == 100

    def test_column_count_correct(self):
        """Column count should match number of DataFrame columns."""
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        schema = generate_table_schema(df, "t")
        assert schema["column count"] == 3

    def test_column_metadata_fields(self):
        """Each column metadata should have all required fields."""
        df = pd.DataFrame({"id": [1, 2, 3]})
        schema = generate_table_schema(df, "t")
        col = schema["columns"][0]
        required_fields = ["name", "dtype", "null_count", "null_percentage",
                           "unique_count", "unique_percentage", "candidate_primary_key"]
        for field in required_fields:
            assert field in col, f"Missing field: {field}"

    def test_null_count_detection(self):
        """Null values should be counted correctly."""
        df = pd.DataFrame({"a": [1, None, 3, None, 5]})
        schema = generate_table_schema(df, "t")
        col = schema["columns"][0]
        assert col["null_count"] == 2
        assert col["null_percentage"] == 40.0

    def test_unique_count_detection(self):
        """Unique values should be counted correctly."""
        df = pd.DataFrame({"a": [1, 1, 2, 2, 3]})
        schema = generate_table_schema(df, "t")
        col = schema["columns"][0]
        assert col["unique_count"] == 3
        assert col["unique_percentage"] == 60.0

    def test_candidate_primary_key_true(self):
        """Column with all unique, non-null values should be a candidate PK."""
        df = pd.DataFrame({"id": [1, 2, 3, 4]})
        schema = generate_table_schema(df, "t")
        assert schema["columns"][0]["candidate_primary_key"] is True

    def test_candidate_primary_key_false_duplicates(self):
        """Column with duplicate values should NOT be a candidate PK."""
        df = pd.DataFrame({"id": [1, 1, 2, 3]})
        schema = generate_table_schema(df, "t")
        assert schema["columns"][0]["candidate_primary_key"] is False

    def test_candidate_primary_key_false_nulls(self):
        """Column with null values should NOT be a candidate PK."""
        df = pd.DataFrame({"id": [1, None, 3, 4]})
        schema = generate_table_schema(df, "t")
        assert schema["columns"][0]["candidate_primary_key"] is False

    def test_empty_dataframe(self):
        """Empty DataFrame should return 0 rows, 0 nulls, 0 unique."""
        df = pd.DataFrame({"a": pd.Series(dtype="int64")})
        schema = generate_table_schema(df, "empty")
        assert schema["row count"] == 0
        assert schema["columns"][0]["null_count"] == 0
        assert schema["columns"][0]["null_percentage"] == 0.0
        assert schema["columns"][0]["unique_count"] == 0

    def test_single_row_dataframe(self):
        """Single-row DataFrame should have correct metadata."""
        df = pd.DataFrame({"id": [42], "name": ["Solo"]})
        schema = generate_table_schema(df, "single")
        assert schema["row count"] == 1
        assert schema["columns"][0]["unique_count"] == 1
        assert schema["columns"][0]["candidate_primary_key"] is True

    def test_mixed_types_dataframe(self):
        """DataFrame with int, float, string, boolean columns."""
        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.1, 2.2, 3.3],
            "str_col": ["a", "b", "c"],
            "bool_col": [True, False, True]
        })
        schema = generate_table_schema(df, "mixed")
        assert schema["column count"] == 4
        dtypes = [col["dtype"] for col in schema["columns"]]
        assert any("int" in d for d in dtypes)
        assert any("float" in d for d in dtypes)

    def test_all_nulls_column(self):
        """Column with all nulls should have 100% null percentage."""
        df = pd.DataFrame({"a": [None, None, None]})
        schema = generate_table_schema(df, "t")
        col = schema["columns"][0]
        assert col["null_count"] == 3
        assert col["null_percentage"] == 100.0
        assert col["unique_count"] == 0

    def test_all_identical_values(self):
        """Column where every value is the same."""
        df = pd.DataFrame({"status": ["active", "active", "active"]})
        schema = generate_table_schema(df, "t")
        col = schema["columns"][0]
        assert col["unique_count"] == 1
        assert col["candidate_primary_key"] is False


# ============================================================================
# TEST: schema_to_Json
# ============================================================================

class TestSchemaToJson:
    """Tests for JSON serialization of schema metadata."""

    def test_valid_json_output(self):
        """Output should be valid JSON."""
        schema = {"table name": "t", "row count": 5, "columns": []}
        result = schema_to_Json(schema)
        parsed = json.loads(result)
        assert parsed["table name"] == "t"

    def test_list_input(self):
        """Should handle list of schema dictionaries."""
        schemas = [
            {"table name": "t1", "columns": []},
            {"table name": "t2", "columns": []}
        ]
        result = schema_to_Json(schemas)
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_custom_indent(self):
        """Custom indent should affect formatting."""
        schema = {"key": "value"}
        result_2 = schema_to_Json(schema, indent=2)
        result_8 = schema_to_Json(schema, indent=8)
        assert len(result_8) > len(result_2)

    def test_empty_dict(self):
        """Empty dict should produce valid JSON."""
        result = schema_to_Json({})
        assert json.loads(result) == {}


# ============================================================================
# TEST: generate_multiple_schemas
# ============================================================================

class TestGenerateMultipleSchemas:
    """Tests for multi-table schema generation."""

    def test_multiple_tables(self):
        """Should generate schemas for each table."""
        datasets = {
            "users": pd.DataFrame({"id": [1, 2]}),
            "orders": pd.DataFrame({"oid": [1], "uid": [1], "amt": [99.0]})
        }
        schemas = generate_multiple_schemas(datasets)
        assert len(schemas) == 2
        names = [s["table name"] for s in schemas]
        assert "users" in names
        assert "orders" in names

    def test_empty_datasets_dict(self):
        """Empty datasets dict should return empty list."""
        schemas = generate_multiple_schemas({})
        assert schemas == []

    def test_single_table_in_dict(self):
        """Single table should produce list with 1 schema."""
        datasets = {"solo": pd.DataFrame({"x": [1, 2, 3]})}
        schemas = generate_multiple_schemas(datasets)
        assert len(schemas) == 1
        assert schemas[0]["table name"] == "solo"

    def test_schema_columns_match_dataframe(self):
        """Number of columns in schema should match DataFrame."""
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3], "d": [4]})
        datasets = {"wide": df}
        schemas = generate_multiple_schemas(datasets)
        assert schemas[0]["column count"] == 4
        assert len(schemas[0]["columns"]) == 4
