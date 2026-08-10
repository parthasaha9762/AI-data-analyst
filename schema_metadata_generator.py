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
        null_count = int(df.isnull().sum())
        null_percentage = float(round((null_count/row_count) * 100), 2) if row_count > 0 else 0.0

        unique_count = int(df[col].nunique())
        unique_percentage = float(round((unique_count/ row_count) * 100), 2) if row_count > 0 else 0.0

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