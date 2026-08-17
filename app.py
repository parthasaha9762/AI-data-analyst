import streamlit as st
import pandas as pd

# Import custom helper functions for schema metadata generation and relationship detection
from schema_metadata_generator import generate_table_schema, schema_to_Json, generate_multiple_schemas
from releationship_detector import detect_table_releationship

# Set main application title
st.title("AI Data Analyst")


# ------------------------------------------------------------------------------
# STEP 1: File Upload & Session State Storage
# ------------------------------------------------------------------------------

# Allow users to upload one or multiple CSV files simultaneously
uploaded_files = st.file_uploader(
    "Upload your CSV files", type=["csv"],
    accept_multiple_files=True
)

# Initialize a session state dictionary to store uploaded DataFrames
# Key = table_name (e.g. "orders"), Value = Pandas DataFrame
if "datasets" not in st.session_state:
    st.session_state["datasets"] = {}


# ------------------------------------------------------------------------------
# STEP 2: Process & Inspect Uploaded CSV Files
# ------------------------------------------------------------------------------

if uploaded_files:
    st.write("Uploaded files...")
    for file in uploaded_files:
        # Reset the buffer cursor to the beginning before reading
        file.seek(0)
        
        # Read the CSV file into a Pandas DataFrame
        df = pd.read_csv(file)
    
        # Extract the table name from the file name (e.g., "orders.csv" -> "orders")
        table_name = file.name.rsplit(".", 1)[0]

        # Store the DataFrame in session state so other modules can access it
        st.session_state["datasets"][table_name] = df

        # Display the file name and created table name
        st.write(f"✅ **File:** `{file.name}` ➔ **Table Name:** `{table_name}`")

        # --- Data Quality Checks & Summary ---
        
        # 1. Missing Values Check
        missing_values = df.isnull().sum()
        with st.expander("Show missing values"):           
            # Display missing value counts per column or a success message if clean
            st.write(missing_values if missing_values.sum() > 0 else "No missing values found! 🎉")

        # 2. Duplicate Records Check & Auto-Cleaning
        num_duplicates = df.duplicated().sum()
        with st.expander("Show duplicate records"):
            if num_duplicates > 0:
                st.write(f"❌ Found **{num_duplicates}** duplicate records!")
                st.dataframe(df[df.duplicated()])

                # Reassign df without duplicates and update session state storage
                df = df.drop_duplicates()
                st.session_state["datasets"][table_name] = df 
                st.success("Duplicate records have been cleared!")
            else:
                st.write("No duplicate records found! 🎉")

        # 3. Descriptive Summary Statistics (Mean, Min, Max, Quantiles for numeric columns)
        with st.expander("Show statistics"):
            st.write(df.describe())

        # 4. Table Dimensions (Row count and Column count)
        st.write(f"No: of rows: {len(df)}  \nNo: of columns: {len(df.columns)}")

        # 5. Data Preview & Simplified Data Types
        with st.expander("Show sample rows of the table"):
            # Display the first 10 rows with 1-based indexing for cleaner presentation
            sample_dataframe = df.head(10).copy()
            sample_dataframe.index = range(1, len(sample_dataframe) + 1)
            st.dataframe(sample_dataframe)

            # Display simplified, human-readable data types (int, float, boolean, object)
            with st.expander("Show data types"):
                clean_dtypes = pd.Series(
                    [
                        "int" if "int" in str(dt) else
                        "float" if "float" in str(dt) else
                        "boolean" if "bool" in str(dt) else str(dt)
                        for dt in df.dtypes
                    ],
                    index=df.columns
                )
                st.write(clean_dtypes)


    # --------------------------------------------------------------------------
    # STEP 3: Multi-Table Schema Metadata Generation
    # --------------------------------------------------------------------------

    # Generate schema metadata (data types, null counts, PK candidates) for all uploaded tables
    schema_table_dictionary = generate_multiple_schemas(st.session_state["datasets"])
    
    # Convert schema dictionary to a formatted JSON string for display
    schema_JSON = schema_to_Json(schema_table_dictionary, 4)
    with st.expander("Show all the metadata schemas in JSON format"):
        st.json(schema_JSON)   


    # --------------------------------------------------------------------------
    # STEP 4: Table Relationship Detection (Foreign Key -> Primary Key)
    # --------------------------------------------------------------------------

    # Scan all pairs of uploaded tables to detect potential Foreign Key -> Primary Key relationships
    table_relationships = detect_table_releationship(st.session_state["datasets"])        

    with st.expander("Show detected table relationships"):
        if table_relationships:
            # Transform detected relationship dictionaries into a clean table structure
            display_data = []
            for relation in table_relationships:
                # Add visual confidence indicator
                badge = "🟢 HIGH" if relation["confidence_level"] == "HIGH" else "🟡 MEDIUM"
                display_data.append({
                    "Confidence": badge,
                    "Score": f"{relation['confidence_score']}%",
                    "Source (Foreign Key)": f"{relation['source_table']}.{relation['source_column']}",
                    "Target (Primary Key)": f"{relation['target_table']}.{relation['target_column']}",
                    "Relationship Type": relation["relationship_type"],
                    "Value Overlap": f"{relation['scoring_breakdown']['value_overlap_percentage']}%"
                })
            
            # Display relationship DataFrame without row index numbers
            rel_df = pd.DataFrame(display_data)
            st.dataframe(rel_df, use_container_width=True, hide_index=True)
        else:
            st.write("No table relationships detected ❌")


# ------------------------------------------------------------------------------
# STEP 5: Natural Language Query Interface
# ------------------------------------------------------------------------------

# Form allowing user submission via Analyze button or pressing Enter
with st.form("query_form"):
    question = st.text_input("Enter your question here", placeholder="Ask a question about your data in your natural language")

    # Custom CSS for input field instruction text
    st.markdown("""
    <style>
    div[data-testid="InputInstructions"] {
        font-size: 0px;
    }
    div[data-testid="InputInstructions"]::after {
        content: "Press Enter or click Analyze button to Analyze 🚀";
        font-size: 12px;
        color: #888;
    }
    </style>
    """, unsafe_allow_html=True)

    # Form submit button
    analyze_submitted = st.form_submit_button("Analyze")

# Handle query submission logic
if analyze_submitted:
    if question.strip():
        st.write("Analyzing your data...")
        st.write("Your question:", question)
    else:
        st.warning("Please enter a question before analyzing.")