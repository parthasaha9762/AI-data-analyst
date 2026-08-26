import streamlit as st
import pandas as pd

# Import custom helper functions for schema metadata generation and relationship detection
from modules.schema_metadata_generator import generate_table_schema, schema_to_Json, generate_multiple_schemas
from modules.releationship_detector import detect_table_releationship

# Import database manager from module
from modules.database_manager import DatabaseManager

# Import schema context generator from module
from modules.schema_context import generate_schema_context

# Import SQL generator from module
from modules.sql_generator import generate_SQL_query

# Import SQL explainer from sql_explainer module
from modules.sql_explainer import explain_SQL_query

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

# Initialize DatabaseManager in session state if not present
if "db_manager" not in st.session_state:
    st.session_state["db_manager"] = DatabaseManager()


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
        
        # 1. Missing Values Check & Auto-Cleaning
        missing_values = df.isnull().sum()
        with st.expander("Show missing values"):           
            if missing_values.sum() > 0:
                st.write(missing_values[missing_values > 0])

                # Impute missing numeric values with 0, text values with "N/A"
                for col in df.columns:
                    if "int" in str(df[col].dtype).lower() or "float" in str(df[col].dtype).lower():
                        df[col] = df[col].fillna(0)
                    else:
                        df[col] = df[col].fillna("N/A")

                # Update session state storage with cleaned DataFrame
                st.session_state["datasets"][table_name] = df
                st.success("Missing values have been auto-cleaned! (Numeric ➔ 0, Text ➔ 'N/A') 🎉")
            else:
                st.write("No missing values found! 🎉")

        # 2. Duplicate Records Check & Auto-Cleaning
        num_duplicates = df.duplicated().sum()
        with st.expander("Show duplicate records"):
            if num_duplicates > 0:
                st.write(f"❌ Found **{num_duplicates}** duplicate records!")
                st.dataframe(df[df.duplicated()])

                # Reassign df without duplicates and update session state storage

                # Drops ONLY rows where ID, Name, Email, City, AND Date are ALL 100% identical (based on previous upload)
                df = df.drop_duplicates().reset_index(drop=True)
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
    # STEP 2.5: AI-Readable Database Schema Context Generation
    # --------------------------------------------------------------------------

    # Generate a clean, structured text representation of all tables, columns,
    # and detected relationships formatted specifically for LLM prompt context
    schema_context = generate_schema_context(st.session_state["datasets"])

    # Display the formatted schema description in a copyable monospaced code block
    with st.expander("Show AI-Readable Schema Context (for LLM)"):
        st.code(schema_context, language="text")


    # Load all uploaded and cleaned datasets into SQLite database tables
    st.session_state["db_manager"].load_datasets(st.session_state["datasets"])




    # --------------------------------------------------------------------------
    # STEP 3: Multi-Table Schema Metadata Generation
    # --------------------------------------------------------------------------

    # Generate schema metadata (data types, null counts, PK candidates) for all uploaded tables
    schema_table_dictionary = generate_multiple_schemas(st.session_state["datasets"])
    
    # Commented out from UI display, but runs in backend
    # with st.expander("Show all the metadata schemas in JSON format"):
    #     st.json(schema_JSON)   
    # --------------------------------------------------------------------------
    # STEP 4: Table Relationship Detection (Foreign Key -> Primary Key) [UI Hidden]
    # --------------------------------------------------------------------------
    # Note: Commented out from UI display, but runs automatically in backend (schema_context.py)
    #
    # table_relationships = detect_table_releationship(st.session_state["datasets"])        
    # with st.expander("Show detected table relationships"):
    #     if table_relationships:
    #         display_data = []
    #         for relation in table_relationships:
    #             badge = "🟢 HIGH" if relation["confidence_level"] == "HIGH" else "🟡 MEDIUM"
    #             display_data.append({
    #                 "Confidence": badge,
    #                 "Score": f"{relation['confidence_score']}%",
    #                 "Source (Foreign Key)": f"{relation['source_table']}.{relation['source_column']}",
    #                 "Target (Primary Key)": f"{relation['target_table']}.{relation['target_column']}",
    #                 "Relationship Type": relation["relationship_type"],
    #                 "Value Overlap": f"{relation['scoring_breakdown']['value_overlap_percentage']}%"
    #             })
    #         rel_df = pd.DataFrame(display_data)
    #         st.dataframe(rel_df, use_container_width=True, hide_index=True)
    #     else:
    #         st.write("No table relationships detected ❌")


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
    if not st.session_state["datasets"]:
        st.warning("Please upload at least one CSV file first before analyzing!")
    elif question.strip():
        st.write(f"🔍 **Analyzing Question:** *\"{question}\"*")

        # 1. Fetch current schema context
        schema_context = generate_schema_context(st.session_state["datasets"])

        try:
            # 2. Call LLM to generate SQL query (Spinner #1 stops as soon as SQL is ready)
            with st.spinner("🤖 AI is generating SQL query..."):
                generated_sql = generate_SQL_query(schema_context, question)

            # 3. Execute generated SQL on SQLite Database Manager
            result_df = st.session_state["db_manager"].execute_query(generated_sql)

            # Trigger animated toast notification immediately after SQL generation!
            st.toast("✅ SQL Query generated successfully! Generating explanation now...", icon="🚀")

            # 4. Generate Explanation (Spinner #2 starts only for explanation)
            with st.spinner("💡 AI is generating explanation..."):
                sql_explanation = explain_SQL_query(schema_context, question, generated_sql)

            # Store query state in session state for persistence and interactive editing
            st.session_state["active_question"] = question
            st.session_state["active_sql"] = generated_sql
            st.session_state["active_df"] = result_df
            st.session_state["active_explanation"] = sql_explanation
            st.session_state["edited_sql_input"] = generated_sql

        except Exception as e:
            st.error(f"❌ Failed to generate or run query: {e}")
    else:
        st.warning("Please enter a question before analyzing.")

# Render AI Query Results and Interactive SQL Workbench
if "active_sql" in st.session_state:
    st.success("SQL Query generated successfully! 🪄✨", icon="✅")
    st.subheader("Generated SQL Query")
    st.code(st.session_state["active_sql"], language="sql")

    # Interactive SQL Workbench: Allow users to modify and re-execute the SQL query
    with st.expander("✏️ Edit & Re-run SQL(Optional)"):
        edited_sql = st.text_area(
            "Modify SQL Query:",
            value=st.session_state.get("edited_sql_input", st.session_state["active_sql"]),
            height=120,
            key="edited_sql_input"
        )
        if st.button("⚡ Run Modified SQL"):
            if edited_sql.strip():
                try:
                    new_df = st.session_state["db_manager"].execute_query(edited_sql)
                    st.session_state["active_sql"] = edited_sql
                    st.session_state["active_df"] = new_df
                    st.success("Modified query executed successfully! 🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"Query execution failed: {e}")
            else:
                st.warning("Please enter a valid SQL query.")

    st.subheader("Query Results")
    if st.session_state.get("active_df") is not None:
        st.dataframe(st.session_state["active_df"], use_container_width=True, hide_index=True)
        st.success("Query executed successfully! 🎉")

    st.subheader("Explanation behind this query")
    st.markdown(st.session_state["active_explanation"])