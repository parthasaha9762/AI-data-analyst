"""
Shared Test Fixtures & Configuration
======================================
Provides common test fixtures used across multiple test modules.
"""
import pytest
import pandas as pd
import sys
import os

# Ensure the project root is on the path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_customers_df():
    """Realistic customers DataFrame matching sample_datasets/customers.csv structure."""
    return pd.DataFrame({
        "customer_id": [1001, 1002, 1003, 1004, 1005],
        "customer_name": ["Laura Miller", "Diana Wilson", "Nina Lopez", "Michael Wilson", "Test User"],
        "email": ["laura@test.com", "diana@test.com", None, "michael@test.com", "test@test.com"],
        "city": ["Sydney", "Tokyo", "Chicago", "Singapore", None],
        "signup_date": ["2023-06-14", "2023-06-18", "2023-05-28", "2023-01-19", "2024-01-01"]
    })


@pytest.fixture
def sample_orders_df():
    """Realistic orders DataFrame matching sample_datasets/orders.csv structure."""
    return pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5, 6, 7],
        "customer_id": [1001, 1002, 1001, 1003, 1002, 1004, 1001],
        "product_id": [501, 502, 503, 501, 504, 502, 505],
        "quantity": [2, 1, 3, 1, 2, 1, 4],
        "unit_price": [29.99, 49.99, 15.00, 29.99, 89.99, 49.99, 9.99],
        "total_amount": [59.98, 49.99, 45.00, 29.99, 179.98, 49.99, 39.96],
        "order_date": ["2024-01-15", "2024-01-16", "2024-02-10", "2024-02-12", "2024-03-01", "2024-03-15", "2024-04-01"]
    })


@pytest.fixture
def sample_products_df():
    """Realistic products DataFrame matching sample_datasets/products.csv structure."""
    return pd.DataFrame({
        "product_id": [501, 502, 503, 504, 505],
        "product_name": ["Running Shoes", "Yoga Mat Pro", "Water Bottle", "Dumbbell Set", "Jump Rope"],
        "category": ["Footwear", "Fitness", "Accessories", "Weights", "Cardio"],
        "price": [29.99, 49.99, 15.00, 89.99, 9.99],
        "brand": ["Nike", "Lululemon", "Hydro Flask", "Bowflex", "CrossRope"]
    })


@pytest.fixture
def multi_table_datasets(sample_customers_df, sample_orders_df, sample_products_df):
    """Combined multi-table dataset dictionary."""
    return {
        "customers": sample_customers_df,
        "orders": sample_orders_df,
        "products": sample_products_df
    }
