# The Relationship Detector identifies foreign key (FK) -> primary key (PK) connections between uploaded CSV tables.
# It uses deterministic heuristics (column names, data types, uniqueness, and value overlaps) to compute a confidence score.

import pandas as pd 

def check_datatype_compatibility(source_dtype, target_dtype) -> bool:
    """
    Checks if the data types of two columns are compatible for joining.
    Compatible types include:
    - Exact same pandas dtype (e.g. int64 and int64)
    - Both numeric (e.g. int64 and float64)
    - Both text/string (e.g. object, string, category)
    """

    source_dtype_str = str(source_dtype).lower()
    target_dtype_str = str(target_dtype).lower()

    # Case 1: Exact data type match
    if source_dtype == target_dtype:
        return True

    # Case 2: If one of them is int or float, return True
    is_source_numeric = any(num_type in source_dtype_str for num_type in ["int", "float"])
    is_target_numeric = any(num_type in target_dtype_str for num_type in ["int", "float"])

    if is_source_numeric and is_target_numeric:
        return True

    # Case 3: If both are string/object types:
    is_source_text = any(text_type in source_dtype_str for text_type in ["object", "string", "category"])
    is_target_text = any(text_type in target_dtype_str for text_type in ["object", "string", "category"])

    if is_source_text and is_target_text:
        return True

    return False



def check_column_value_overlap(source_column: pd.Series, target_column: pd.Series)-> float:
    """
    pd.Series -> It's a 1D column of a dataframe,i.e, it will represent a specific column of a Pandas dataframe in a series form.

    Calculates what fraction of unique non-null values in the source column exist in the target column.
    Returns:
        float: Overlap ratio between 0.0 (0% overlap) and 1.0 (100% overlap).
    """

    # Extract non null values from both the columns for Set operations
    unique_source_values = set(source_column.dropna().unique())
    unique_target_values = set(target_column.dropna().unique())


    # If no unique values exists in the source column, return 0.0 just to prevent ZeroDivisionError
    if not unique_source_values:
        return 0.0

    # Calculate how many source values are present in the target values
    shared_values = unique_source_values.intersection(unique_target_values)
    overlap_ratio = len(shared_values) / len(unique_source_values)

    return overlap_ratio
    