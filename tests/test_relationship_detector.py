"""
Comprehensive Test Suite: Relationship Detector
================================================
Tests FK/PK detection, scoring rules, data type compatibility checks,
value overlap calculations, confidence levels, and edge cases.
"""
import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.releationship_detector import (
    check_datatype_compatibility,
    check_column_value_overlap,
    detect_table_releationship
)


# ============================================================================
# TEST: check_datatype_compatibility
# ============================================================================

class TestDatatypeCompatibility:
    """Tests for data type compatibility checks."""

    def test_same_int_types(self):
        """Identical int dtypes should be compatible."""
        assert check_datatype_compatibility(pd.Series([1]).dtype, pd.Series([2]).dtype) is True

    def test_same_float_types(self):
        """Identical float dtypes should be compatible."""
        assert check_datatype_compatibility(pd.Series([1.0]).dtype, pd.Series([2.0]).dtype) is True

    def test_int_and_float_compatible(self):
        """int64 and float64 should be compatible (both numeric)."""
        int_dtype = pd.Series([1]).dtype
        float_dtype = pd.Series([1.0]).dtype
        assert check_datatype_compatibility(int_dtype, float_dtype) is True

    def test_same_object_types(self):
        """Both object (string) dtypes should be compatible."""
        obj_dtype = pd.Series(["a"]).dtype
        assert check_datatype_compatibility(obj_dtype, obj_dtype) is True

    def test_int_and_object_incompatible(self):
        """int and object should NOT be compatible."""
        int_dtype = pd.Series([1]).dtype
        obj_dtype = pd.Series(["a"]).dtype
        assert check_datatype_compatibility(int_dtype, obj_dtype) is False

    def test_float_and_object_incompatible(self):
        """float and object should NOT be compatible."""
        float_dtype = pd.Series([1.0]).dtype
        obj_dtype = pd.Series(["a"]).dtype
        assert check_datatype_compatibility(float_dtype, obj_dtype) is False

    def test_bool_and_int_incompatible(self):
        """bool and int should NOT be compatible (different categories)."""
        bool_dtype = pd.Series([True]).dtype
        int_dtype = pd.Series([1]).dtype
        assert check_datatype_compatibility(bool_dtype, int_dtype) is False

    def test_category_and_object_compatible(self):
        """category and object should be compatible (both text-like)."""
        cat_series = pd.Series(pd.Categorical(["a", "b", "c"]))
        obj_series = pd.Series(["a", "b", "c"], dtype="object")
        assert check_datatype_compatibility(cat_series.dtype, obj_series.dtype) is True


# ============================================================================
# TEST: check_column_value_overlap
# ============================================================================

class TestColumnValueOverlap:
    """Tests for value overlap ratio between two columns."""

    def test_full_overlap(self):
        """100% overlap when all source values exist in target."""
        source = pd.Series([1, 2, 3])
        target = pd.Series([1, 2, 3, 4, 5])
        assert check_column_value_overlap(source, target) == 1.0

    def test_no_overlap(self):
        """0% overlap when no values match."""
        source = pd.Series([1, 2, 3])
        target = pd.Series([4, 5, 6])
        assert check_column_value_overlap(source, target) == 0.0

    def test_partial_overlap(self):
        """Partial overlap should return correct ratio."""
        source = pd.Series([1, 2, 3, 4])
        target = pd.Series([1, 2, 5, 6])
        ratio = check_column_value_overlap(source, target)
        assert ratio == 0.5

    def test_empty_source_returns_zero(self):
        """Empty source column should return 0.0 (prevent division by zero)."""
        source = pd.Series([], dtype="int64")
        target = pd.Series([1, 2, 3])
        assert check_column_value_overlap(source, target) == 0.0

    def test_empty_target_returns_zero(self):
        """Empty target should return 0.0 overlap."""
        source = pd.Series([1, 2, 3])
        target = pd.Series([], dtype="int64")
        assert check_column_value_overlap(source, target) == 0.0

    def test_both_empty(self):
        """Both empty should return 0.0."""
        source = pd.Series([], dtype="int64")
        target = pd.Series([], dtype="int64")
        assert check_column_value_overlap(source, target) == 0.0

    def test_with_null_values(self):
        """Null values should be excluded from overlap calculation."""
        source = pd.Series([1, None, 3, None])
        target = pd.Series([1, 3, 5, None])
        ratio = check_column_value_overlap(source, target)
        assert ratio == 1.0  # Both non-null source values (1, 3) exist in target

    def test_string_overlap(self):
        """String value overlap should work correctly."""
        source = pd.Series(["cat", "dog", "fish"])
        target = pd.Series(["cat", "bird", "fish", "snake"])
        ratio = check_column_value_overlap(source, target)
        assert abs(ratio - 2/3) < 0.01

    def test_duplicate_values_handled(self):
        """Duplicates should not inflate the overlap ratio."""
        source = pd.Series([1, 1, 1, 2, 2, 3])
        target = pd.Series([1, 2])
        ratio = check_column_value_overlap(source, target)
        assert abs(ratio - 2/3) < 0.01  # 2 out of 3 unique source values match


# ============================================================================
# TEST: detect_table_releationship
# ============================================================================

class TestDetectTableRelationship:
    """Tests for automated FK/PK relationship detection."""

    @pytest.fixture
    def relational_datasets(self):
        """Standard relational datasets with clear FK->PK patterns."""
        return {
            "customers": pd.DataFrame({
                "customer_id": [1, 2, 3, 4],
                "name": ["Alice", "Bob", "Charlie", "David"],
                "city": ["NYC", "London", "Tokyo", "Paris"]
            }),
            "orders": pd.DataFrame({
                "order_id": [101, 102, 103, 104, 105],
                "customer_id": [1, 2, 1, 3, 2],
                "product_id": [501, 502, 501, 503, 502],
                "amount": [250.5, 99.0, 150.0, 450.0, 120.0]
            }),
            "products": pd.DataFrame({
                "product_id": [501, 502, 503],
                "product_name": ["Laptop", "Phone", "Headphones"],
                "category": ["Electronics", "Electronics", "Accessories"]
            })
        }

    def test_detects_customer_id_relationship(self, relational_datasets):
        """Should detect customer_id FK->PK relationship."""
        results = detect_table_releationship(relational_datasets)
        customer_rels = [
            r for r in results
            if "customer_id" in r["source_column"] and "customer_id" in r["target_column"]
        ]
        assert len(customer_rels) > 0

    def test_detects_product_id_relationship(self, relational_datasets):
        """Should detect product_id FK->PK relationship."""
        results = detect_table_releationship(relational_datasets)
        product_rels = [
            r for r in results
            if "product_id" in r["source_column"] and "product_id" in r["target_column"]
        ]
        assert len(product_rels) > 0

    def test_high_confidence_for_exact_match(self, relational_datasets):
        """customer_id match should have HIGH confidence (score >= 80)."""
        results = detect_table_releationship(relational_datasets)
        customer_rels = [
            r for r in results
            if r["source_column"] == "customer_id" and r["target_column"] == "customer_id"
        ]
        assert any(r["confidence_score"] >= 80 for r in customer_rels)

    def test_results_sorted_by_confidence(self, relational_datasets):
        """Results should be sorted by confidence score (highest first)."""
        results = detect_table_releationship(relational_datasets)
        if len(results) > 1:
            scores = [r["confidence_score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_no_self_comparison(self, relational_datasets):
        """No relationship should compare a table to itself."""
        results = detect_table_releationship(relational_datasets)
        for r in results:
            assert r["source_table"] != r["target_table"]

    def test_scoring_breakdown_present(self, relational_datasets):
        """Each relationship should have scoring breakdown details."""
        results = detect_table_releationship(relational_datasets)
        for r in results:
            assert "scoring_breakdown" in r
            breakdown = r["scoring_breakdown"]
            assert "same_column_name" in breakdown
            assert "compatible_datatype" in breakdown
            assert "target_is_unique" in breakdown
            assert "value_overlap_percentage" in breakdown

    def test_confidence_level_labels(self, relational_datasets):
        """Confidence levels should be either HIGH or MEDIUM."""
        results = detect_table_releationship(relational_datasets)
        for r in results:
            assert r["confidence_level"] in ["HIGH", "MEDIUM"]

    def test_single_table_no_relationships(self):
        """Single table dataset should return empty relationship list."""
        datasets = {
            "only_table": pd.DataFrame({"id": [1, 2, 3], "val": [10, 20, 30]})
        }
        results = detect_table_releationship(datasets)
        assert results == []

    def test_empty_datasets(self):
        """Empty datasets should return empty list."""
        results = detect_table_releationship({})
        assert results == []

    def test_no_matching_columns(self):
        """Tables with completely different columns should have no relationships above threshold."""
        datasets = {
            "table_a": pd.DataFrame({"alpha": [1, 2], "beta": [3, 4]}),
            "table_b": pd.DataFrame({"gamma": ["x", "y"], "delta": ["a", "b"]})
        }
        results = detect_table_releationship(datasets, minimum_confidence_score=60)
        assert len(results) == 0

    def test_custom_minimum_confidence(self, relational_datasets):
        """Higher threshold should return fewer or equal results."""
        results_60 = detect_table_releationship(relational_datasets, minimum_confidence_score=60)
        results_80 = detect_table_releationship(relational_datasets, minimum_confidence_score=80)
        assert len(results_80) <= len(results_60)

    def test_tables_with_no_value_overlap(self):
        """Same column name but zero value overlap should still score from name+dtype."""
        datasets = {
            "t1": pd.DataFrame({"user_id": [1, 2, 3]}),
            "t2": pd.DataFrame({"user_id": [100, 200, 300]})
        }
        results = detect_table_releationship(datasets, minimum_confidence_score=60)
        # Same name (+40) + same dtype (+20) = 60, but target unique (+20) = 80
        # Value overlap is 0 so no +20 from that
        assert len(results) >= 1

    def test_relationship_type_always_fk_pk(self, relational_datasets):
        """All detected relationships should be 'Foreign Key -> Primary Key'."""
        results = detect_table_releationship(relational_datasets)
        for r in results:
            assert r["relationship_type"] == "Foreign Key -> Primary Key"
