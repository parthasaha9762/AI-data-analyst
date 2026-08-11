#The Schema and Metadata Generator is used to generate the schema and metadata for each table in the database whenever the user uploads CSV files so that we can use this to generate the SQL queries for the uploaded CSV files

import json
import pandas as pd 

def generate_table_schema(df: pd.DataFrame, table_name: str) -> dict:
    """Generates schema metadata for a single pandas DataFrame in Python dictionary format.
    Parameters:
        df (pd.DataFrame): The DataFrame to analyze.
        table_name (str): Name of the table (e.g. extracted from file name).
    Returns:
        dict: Schema metadata dictionary matching the exact target format.
    """

    row_count = int(len(df))
    columns_count = int(len(df.columns))
 
    columns_metadata = []

    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_percentage = float(round((null_count / row_count) * 100, 2)) if row_count > 0 else 0.0

        unique_count = int(df[col].nunique())
        unique_percentage = float(round((unique_count / row_count) * 100, 2)) if row_count > 0 else 0.0

        #Candidate_primary_key rule: the column must have no null values and every row count must be equals to unique count
        candidate_primary_key = bool(null_count == 0 and unique_count == row_count)

        #Creating a dictionary for each column in the table and pass it on to the columns_metadata list
        col_info = {
            "name": str(col),
            "dtype": str(df[col].dtype),
            "null_count": null_count,
            "null_percentage": null_percentage,
            "unique_count": unique_count,
            "unique_percentage": unique_percentage,
            "candidate_primary_key": candidate_primary_key
        }

        columns_metadata.append(col_info)

    schema_meta_dictionary = {
        "table name": table_name,
        "row count": row_count,
        "column count": columns_count,
        "columns": columns_metadata
    }

    return schema_meta_dictionary


def schema_to_Json(schema_data: dict | list, indent: int = 4) -> str:
    """Converts a schema dictionary (or list of dictionaries) into a JSON string.
    Parameters:
        schema_data (dict or list): Schema metadata dictionary or list of dicts.
        indent (int): Number of spaces for JSON indentation.
    Returns:
        str: Formatted JSON string.
    """

    return json.dumps(schema_data, indent=indent)


def generate_multiple_schemas(datasets: dict) -> list[dict]:
    """Generates schema metadata dictionaries for a collection of uploaded tables.
    Parameters:
        datasets (dict): Dictionary mapping table_name -> pd.DataFrame
    Returns:
        list[dict]: List of schema metadata dictionaries for all tables.
    """
    schemas = []
    for table_name, df in datasets.items(): # 👈 Expects a DICTIONARY of DataFrames
        schemas.append(generate_table_schema(df, table_name))

    return schemas


# Creating multiple dummy DataFrames to test multi-table schema generation
users_data = {
    "user_id": [1, 2, 3, 4],
    "name": ["Alice", "Bob", "Charlie", "David"],
    "email": ["alice@test.com", "bob@test.com", None, "david@test.com"],
}

orders_data = {
    "order_id": [101, 102, 103, 104, 105],
    "user_id": [1, 2, 1, 3, 2],
    "total_amount": [250.5, 99.0, 150.0, 450.0, 120.0],
    "status": ["completed", "pending", "completed", "completed", "cancelled"],
}

products_data = {
    "product_id": [501, 502, 503],
    "product_name": ["Laptop", "Phone", "Headphones"],
    "price": [1200.0, 800.0, 150.0],
}

# Combine multiple datasets into a dictionary (simulating uploaded CSV files in Streamlit)
dummy_datasets = {
    "users": pd.DataFrame(users_data),
    "orders": pd.DataFrame(orders_data),
    "products": pd.DataFrame(products_data),
}

# Generate schema metadata for multiple tables
multiple_schemas = generate_multiple_schemas(dummy_datasets)

# Convert all schema metadata to JSON format
multiple_schemas_json = schema_to_Json(multiple_schemas)

# Print the final JSON output
print("=== MULTIPLE TABLES SCHEMA METADATA (JSON) ===")
print(multiple_schemas_json)
