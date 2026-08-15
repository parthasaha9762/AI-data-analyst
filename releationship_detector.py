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

    if is_source_text and target_dtype_str:
        return True

    return False