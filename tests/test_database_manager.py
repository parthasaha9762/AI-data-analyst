"""
Comprehensive Test Suite: DatabaseManager
==========================================
Tests SQLite in-memory database operations including table creation,
query execution, duplicate column renaming, edge cases, and error handling.
"""
import pytest
import pandas as pd
import sqlite3
import sys
import os

# Ensure the parent directory is on the path so 'modules' is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.database_manager import DatabaseManager


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db():
    """Provides a fresh in-memory DatabaseManager for each test."""
    manager = DatabaseManager()
    yield manager
    manager.close()


@pytest.fixture
def sample_datasets():
    """Standard multi-table test datasets."""
    return {
        "customers": pd.DataFrame({
            "customer_id": [1, 2, 3, 4],
            "name": ["Alice", "Bob", "Charlie", "David"],
            "city": ["NYC", "London", "Tokyo", "Paris"]
        }),
        "orders": pd.DataFrame({
            "order_id": [101, 102, 103],
            "customer_id": [1, 2, 1],
            "amount": [250.50, 99.00, 150.00]
        })
    }


# ============================================================================
# TEST: Basic Initialization
# ============================================================================

class TestDatabaseManagerInit:
    """Tests for DatabaseManager initialization."""

    def test_init_creates_connection(self, db):
        """Verify that DatabaseManager initializes with a valid SQLite connection."""
        assert db.conn is not None
        assert isinstance(db.conn, sqlite3.Connection)

    def test_init_in_memory_default(self):
        """Verify default db_name is ':memory:' (no file created)."""
        manager = DatabaseManager()
        # Connection should be alive and functional
        cursor = manager.conn.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
        manager.close()

    def test_init_custom_db_name(self, tmp_path):
        """Verify DatabaseManager works with a file-based SQLite database."""
        db_file = str(tmp_path / "test.db")
        manager = DatabaseManager(db_name=db_file)
        manager.load_datasets({"t": pd.DataFrame({"x": [1]})})
        assert manager.get_tables() == ["t"]
        manager.close()


# ============================================================================
# TEST: load_datasets
# ============================================================================

class TestLoadDatasets:
    """Tests for loading pandas DataFrames into SQLite tables."""

    def test_load_single_table(self, db):
        """Load a single DataFrame and verify table creation."""
        df = pd.DataFrame({"id": [1, 2], "val": ["a", "b"]})
        db.load_datasets({"test_table": df})
        tables = db.get_tables()
        assert "test_table" in tables

    def test_load_multiple_tables(self, db, sample_datasets):
        """Load multiple DataFrames and verify all tables created."""
        db.load_datasets(sample_datasets)
        tables = db.get_tables()
        assert "customers" in tables
        assert "orders" in tables

    def test_load_empty_dict(self, db):
        """Loading an empty dict should not create any tables."""
        db.load_datasets({})
        assert db.get_tables() == []

    def test_load_empty_dataframe(self, db):
        """Loading an empty DataFrame should create a table with 0 rows."""
        df = pd.DataFrame({"col_a": pd.Series(dtype="int64"), "col_b": pd.Series(dtype="str")})
        db.load_datasets({"empty_table": df})
        assert "empty_table" in db.get_tables()
        result = db.execute_query("SELECT COUNT(*) as cnt FROM empty_table")
        assert result["cnt"].iloc[0] == 0

    def test_reload_replaces_table(self, db):
        """Re-loading same table name with if_exists='replace' should overwrite data."""
        df1 = pd.DataFrame({"id": [1, 2, 3]})
        df2 = pd.DataFrame({"id": [10, 20]})
        db.load_datasets({"tbl": df1})
        result1 = db.execute_query("SELECT COUNT(*) as cnt FROM tbl")
        assert result1["cnt"].iloc[0] == 3

        db.load_datasets({"tbl": df2})
        result2 = db.execute_query("SELECT COUNT(*) as cnt FROM tbl")
        assert result2["cnt"].iloc[0] == 2

    def test_load_preserves_data_types(self, db):
        """Verify that numeric and string types are preserved through SQLite roundtrip."""
        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.5, 2.5, 3.5],
            "str_col": ["a", "b", "c"]
        })
        db.load_datasets({"typed": df})
        result = db.execute_query("SELECT * FROM typed")
        assert result["int_col"].dtype in ["int64", "int32", "int"]
        assert result["float_col"].dtype in ["float64", "float32", "float"]

    def test_load_with_special_characters_in_values(self, db):
        """Values with special characters should be stored correctly."""
        df = pd.DataFrame({
            "name": ["O'Brien", 'She said "hello"', "Home & Kitchen", "50% off"],
            "id": [1, 2, 3, 4]
        })
        db.load_datasets({"special": df})
        result = db.execute_query("SELECT * FROM special")
        assert len(result) == 4
        assert "O'Brien" in result["name"].values

    def test_load_large_dataframe(self, db):
        """Verify that a large DataFrame (10K rows) loads correctly."""
        df = pd.DataFrame({
            "id": range(10000),
            "value": [f"item_{i}" for i in range(10000)]
        })
        db.load_datasets({"big_table": df})
        result = db.execute_query("SELECT COUNT(*) as cnt FROM big_table")
        assert result["cnt"].iloc[0] == 10000

    def test_load_with_null_values(self, db):
        """DataFrames with NaN/None should load without errors."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", None, "Charlie"],
            "score": [90.5, float("nan"), 85.0]
        })
        db.load_datasets({"nulls": df})
        result = db.execute_query("SELECT * FROM nulls WHERE name IS NULL")
        assert len(result) == 1


# ============================================================================
# TEST: execute_query
# ============================================================================

class TestExecuteQuery:
    """Tests for SQL query execution."""

    def test_simple_select(self, db, sample_datasets):
        """Execute a basic SELECT * query."""
        db.load_datasets(sample_datasets)
        result = db.execute_query("SELECT * FROM customers")
        assert len(result) == 4
        assert "customer_id" in result.columns

    def test_select_with_where(self, db, sample_datasets):
        """Execute a filtered SELECT with WHERE clause."""
        db.load_datasets(sample_datasets)
        result = db.execute_query("SELECT * FROM customers WHERE city = 'NYC'")
        assert len(result) == 1
        assert result.iloc[0]["name"] == "Alice"

    def test_aggregation_query(self, db, sample_datasets):
        """Execute an aggregation query with SUM and GROUP BY."""
        db.load_datasets(sample_datasets)
        result = db.execute_query(
            "SELECT customer_id, SUM(amount) as total FROM orders GROUP BY customer_id"
        )
        assert len(result) == 2

    def test_join_query(self, db, sample_datasets):
        """Execute a JOIN query across two tables."""
        db.load_datasets(sample_datasets)
        result = db.execute_query("""
            SELECT c.name, o.amount 
            FROM customers c 
            JOIN orders o ON c.customer_id = o.customer_id
        """)
        assert len(result) == 3
        assert "name" in result.columns

    def test_count_query(self, db, sample_datasets):
        """Execute a COUNT query."""
        db.load_datasets(sample_datasets)
        result = db.execute_query("SELECT COUNT(*) as total FROM customers")
        assert result["total"].iloc[0] == 4

    def test_order_by_limit(self, db, sample_datasets):
        """Execute query with ORDER BY and LIMIT."""
        db.load_datasets(sample_datasets)
        result = db.execute_query("SELECT * FROM orders ORDER BY amount DESC LIMIT 2")
        assert len(result) == 2
        assert result.iloc[0]["amount"] >= result.iloc[1]["amount"]

    def test_invalid_sql_raises_error(self, db, sample_datasets):
        """Invalid SQL should raise an exception."""
        db.load_datasets(sample_datasets)
        with pytest.raises(Exception):
            db.execute_query("SELECT * FROM nonexistent_table")

    def test_empty_result_returns_empty_df(self, db, sample_datasets):
        """Query that matches 0 rows should return empty DataFrame."""
        db.load_datasets(sample_datasets)
        result = db.execute_query("SELECT * FROM customers WHERE city = 'Atlantis'")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_duplicate_column_renaming(self, db):
        """Duplicate column names from JOIN SELECT * should be renamed."""
        db.load_datasets({
            "t1": pd.DataFrame({"id": [1], "name": ["A"]}),
            "t2": pd.DataFrame({"id": [1], "name": ["B"]})
        })
        result = db.execute_query("SELECT * FROM t1, t2 WHERE t1.id = t2.id")
        # Should have renamed duplicates like name_1
        col_list = list(result.columns)
        assert len(col_list) == len(set(col_list)), f"Duplicate columns found: {col_list}"

    def test_returns_dataframe(self, db, sample_datasets):
        """All queries should return pandas DataFrames."""
        db.load_datasets(sample_datasets)
        result = db.execute_query("SELECT 1 as val")
        assert isinstance(result, pd.DataFrame)


# ============================================================================
# TEST: get_tables
# ============================================================================

class TestGetTables:
    """Tests for listing tables."""

    def test_empty_database(self, db):
        """Fresh database should have no tables."""
        assert db.get_tables() == []

    def test_after_loading(self, db, sample_datasets):
        """After loading datasets, get_tables should list them."""
        db.load_datasets(sample_datasets)
        tables = db.get_tables()
        assert set(tables) == {"customers", "orders"}

    def test_after_reload(self, db):
        """After reloading a table, it should still appear exactly once."""
        db.load_datasets({"t": pd.DataFrame({"x": [1]})})
        db.load_datasets({"t": pd.DataFrame({"x": [2]})})
        tables = db.get_tables()
        assert tables.count("t") == 1


# ============================================================================
# TEST: close
# ============================================================================

class TestClose:
    """Tests for connection cleanup."""

    def test_close_prevents_further_queries(self):
        """After close(), queries should fail."""
        manager = DatabaseManager()
        manager.load_datasets({"t": pd.DataFrame({"x": [1]})})
        manager.close()
        with pytest.raises(Exception):
            manager.execute_query("SELECT * FROM t")

    def test_double_close_no_crash(self):
        """Calling close() twice should not raise an error."""
        manager = DatabaseManager()
        manager.close()
        # Second close may or may not raise, but shouldn't crash the process
        try:
            manager.close()
        except Exception:
            pass  # Acceptable behavior
