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
    

def detect_table_releationship(datasets: dict[str, pd.DataFrame],
minimum_confidence_score: int = 60) -> list[dict]:
    """
    Scans all dataset pairs to detect potential Foreign Key -> Primary Key relationships.
    Parameters:
        datasets (dict): Dictionary mapping table names to pandas DataFrames.
        minimum_confidence_score (int): Minimum score required to include a relationship.
    Returns:
        list[dict]: Sorted list of detected relationship dictionaries.
    """
    detected_relationships = []
    table_names_list = list(datasets.keys()) # e.g. ["customers", "orders", "products"]

    confidence_level = "LOW"

    # Iterate through table pairs

    for source_index in range(len(table_names_list)):
        for target_index in range(len(table_names_list)):

            # Don't compare a table to itself!
            if source_index == target_index:
                continue

            source_table_name = table_names_list[source_index]
            target_table_name = table_names_list[target_index]

            source_dataframe = datasets[source_table_name]
            target_dataframe = datasets[target_table_name]

            # Inner loop: compare every column of source dataset with target dataset
            for source_column_name in source_dataframe.columns:
                for target_column_name in target_dataframe.columns:

                    score = 0

                    # Rule 1: Same Column Name (+40 Points)
                    is_same_column_name = (str(source_column_name).strip().lower() == str(target_column_name).strip().lower())

                    if is_same_column_name:
                        score += 40


                    # Rule 2: Compatible Data Types (+20 Points)
                    is_datatype_compatible = check_datatype_compatibility(source_dataframe[source_column_name].dtype,
                    target_dataframe[target_column_name].dtype)

                    if is_datatype_compatible:
                        score += 20

                    # Rule 3: Target Column is Unique / Candidate Primary Key (+20 Points)
                    target_non_null_series = target_dataframe[target_column_name].dropna()

                    is_target_column_unique = (
                        len(target_non_null_series) > 0 and
                        target_non_null_series.nunique() == len(target_non_null_series)
                    )

                    if is_target_column_unique:
                        score += 20

                    # Rule 4: High Value Overlap (+20 Points)
                    value_overlap_ratio = check_column_value_overlap(source_dataframe[source_column_name], target_dataframe[target_column_name])

                    if value_overlap_ratio >= 0.8:
                        score += 20

                    # Filter by minimum confidence score threshold (default: 60)
                    if score >= minimum_confidence_score:
                        confidence_level = "HIGH" if score >= 80 else "MEDIUM"
            
                        relationship_summary = {
                            "source_table": source_table_name,
                            "source_column": str(source_column_name),
                            "target_table": target_table_name,
                            "target_column": str(target_column_name),
                            "relationship_type": "Foreign Key -> Primary Key",
                            "confidence_score": score,
                            "confidence_level": confidence_level,
                            "scoring_breakdown": {
                                "same_column_name": is_same_column_name,
                                "compatible_datatype": is_datatype_compatible,
                                "target_is_unique": is_target_column_unique,
                                "value_overlap_percentage": round(value_overlap_ratio*100, 2)
                            }
                        }

                        detected_relationships.append(relationship_summary)
    
    # Sort relationships by highest confidence score first
    detected_relationships.sort(key=lambda item: item["confidence_score"], reverse=True)

    return detected_relationships
            
            
# Built-in standalone test script to run from terminal
customers_sample_data = {
        "customer_id": [1, 2, 3, 4],
        "customer_name": ["Alice", "Bob", "Charlie", "David"],
        "city": ["New York", "London", "Tokyo", "Paris"]
    }
orders_sample_data = {
    "order_id": [101, 102, 103, 104, 105],
    "customer_id": [1, 2, 1, 3, 2],
    "product_id": [501, 502, 501, 503, 502],
    "total_amount": [250.5, 99.0, 150.0, 450.0, 120.0]
}
products_sample_data = {
    "product_id": [501, 502, 503],
    "product_name": ["Laptop", "Phone", "Headphones"],
    "category": ["Electronics", "Electronics", "Accessories"]
}
sample_datasets = {
    "customers": pd.DataFrame(customers_sample_data),
    "orders": pd.DataFrame(orders_sample_data),
    "products": pd.DataFrame(products_sample_data)
}
print("=== DETECTED TABLE RELATIONSHIPS ===")
results = detect_table_releationship(sample_datasets)
for rank, rel in enumerate(results, start=1):
    print(f"\n{rank}. {rel['source_table']}.{rel['source_column']} -> {rel['target_table']}.{rel['target_column']}")
    print(f"   Relationship : {rel['relationship_type']}")
    print(f"   Confidence   : {rel['confidence_level']} (Score: {rel['confidence_score']}/100)")
    print(f"   Breakdown    : {rel['scoring_breakdown']}")
    