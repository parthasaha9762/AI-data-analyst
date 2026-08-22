"""
Schema Context Module
---------------------
Generates a clean, human-readable and AI-friendly database schema context description 
including tables, columns with standard SQL data types, and detected relationships.

This schema description is passed to the LLM so it understands the database structure 
without guessing table names, column names, or foreign key relationships.
"""

import sys 
import pandas as pd 

# Fallback import handling
try:
    from modules.releationship_detector import detect_table_releationship
except ImportError:
    from releationship_detector import detect_table_releationship


def map_dtype_to_sql(dtype) -> str:
    """
    Maps Pandas/Numpy data types to clean, standard SQL data types.
    """
    dtype_str = str(dtype).lower()

    # Integer types
    if "int" in dtype_str or dtype == int:
        return "INTEGER"
    
    # Float types
    elif "float" in dtype_str or "decimal" in dtype_str or dtype == float:
        return "REAL"   # Using REAL is standard SQL in SQLite

    # Boolean types
    elif "bool" in dtype_str or dtype == bool:
        return "BOOLEAN"

    # Date/Time types
    elif any(keyword in dtype_str for keyword in ["datetime", "date", "time"]):
        return "TIMESTAMP"

    else:
        # Default text fallback
        return "VARCHAR"


def generate_schema_context(
    datasets: dict[str, pd.DataFrame], 
    relationships: list[dict] | None = None
) -> str:
    """
    Generates a clean text description of the database schema for LLM context.
    If only one CSV/table is uploaded, relationship detection is skipped.
    """
    if not datasets:
        return "DATABASE SCHEMA\n\nNO TABLES FOUND."

    lines = ["DATABASE SCHEMA", ""]

    # 1. Add Tables and Columns
    for table_name, df in datasets.items():
        lines.append(f"TABLE: {table_name}\n")
        lines.append(" Columns:")
        for col_name in df.columns:
            sql_type = map_dtype_to_sql(df[col_name].dtype)
            lines.append(f"- {col_name}: {sql_type}")

        lines.append("")  # Blank line after each table

    # 2. Add Relationships
    lines.append("RELATIONSHIPS:")

    # Check if only 1 CSV/table is uploaded
    if len(datasets) <= 1:
        lines.append("- None (Single table dataset)")
    else:
        # If relationships are not provided, run relationship detector automatically
        if relationships is None:
            relationships = detect_table_releationship(datasets)
        
        if relationships:
            # Prioritize HIGH confidence relationships (score > 80) to discard coincidental matches
            high_conf_relationships = [
                rel for rel in relationships if rel.get("confidence_score", 0) > 80
            ]
            target_relationships = high_conf_relationships if high_conf_relationships else relationships

            # Deduplicate bidirectional relationships, keeping the highest confidence score direction
            best_relationships = {}

            for rel in target_relationships:
                endpoint_a = (rel["source_table"], rel["source_column"])
                endpoint_b = (rel["target_table"], rel["target_column"])
                pair_key = tuple(sorted([endpoint_a, endpoint_b]))

                if pair_key not in best_relationships:
                    best_relationships[pair_key] = rel
                elif rel["confidence_score"] > best_relationships[pair_key]["confidence_score"]:
                    best_relationships[pair_key] = rel

            # Add formatted relationships
            for rel in best_relationships.values():
                rel_str = f"- {rel['source_table']}.{rel['source_column']} → {rel['target_table']}.{rel['target_column']}"
                lines.append(rel_str)
            

    return "\n".join(lines).strip()
            

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # 1. Single Table Test
    single_table_test = {
        "orders": pd.DataFrame({"order_id": [1, 2], "amount": [100, 200]})
    }
    
    print("=== SINGLE TABLE SCHEMA CONTEXT ===")
    print(generate_schema_context(single_table_test))
    print("\n" + "=" * 50 + "\n")

    # 2. Multiple Tables Test
    orders_data = {
        "order_id": [1, 2, 3],
        "customer_id": [101, 102, 101],
        "product_id": [501, 502, 501],
        "total_amount": [250.5, 99.0, 150.0]
    }
    customers_data = {
        "customer_id": [101, 102, 103],
        "customer_name": ["Alice", "Bob", "Charlie"],
        "city": ["New York", "London", "Tokyo"]
    }
    products_data = {
        "product_id": [501, 502, 503],
        "product_name": ["Laptop", "Phone", "Headphones"],
        "category": ["Electronics", "Electronics", "Accessories"]
    }

    multiple_tables_test = {
        "orders": pd.DataFrame(orders_data),
        "customers": pd.DataFrame(customers_data),
        "products": pd.DataFrame(products_data)
    }

    print("=== MULTIPLE TABLES SCHEMA CONTEXT ===")
    print(generate_schema_context(multiple_tables_test))