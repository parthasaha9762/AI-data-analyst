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

# Import Chart Selector module for automatic chart recommendations & rendering
from modules.chart_selector import generate_plotly_chart, recommend_chart_config

# Import Query Validator module for detecting gibberish & non-analytic prompts
from modules.query_validator import is_meaningful_query

# Import Insight Generator module for generating business insights
from modules.insight_generator import generate_business_insights


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
    # STEP 2.5: AI-Readable Database Schema Context Generation [UI Hidden]
    # --------------------------------------------------------------------------

    # Generate a clean, structured text representation of all tables, columns,
    # and detected relationships formatted specifically for LLM prompt context
    schema_context = generate_schema_context(st.session_state["datasets"])

    # Note: Commented out from UI display, but runs in backend for LLM context
    # with st.expander("Show AI-Readable Schema Context (for LLM)"):
    #     st.code(schema_context, language="text")


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
# STEP 5: Natural Language Query Interface (Sticky Bottom Chatbot Bar)
# ------------------------------------------------------------------------------

# Custom CSS styling for the sticky bottom chat bar
st.markdown("""
<style>
div[data-testid="stChatInput"] {
    border-radius: 12px;
    box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.15);
}
</style>
""", unsafe_allow_html=True)

# Fixed Chat Input anchored to the bottom of the viewport throughout scrolling
user_prompt = st.chat_input("💬 Ask any question about your data (e.g., 'What are the top 5 sales by category?')...")

# Handle query submission logic from fixed chat bar
if user_prompt:
    if not st.session_state.get("datasets"):
        st.warning("⚠️ Please upload at least one CSV file first before analyzing!")
    elif user_prompt.strip():
        question = user_prompt.strip()

        # 0. Tier 1: Fast Heuristic Validation (0ms response)
        is_valid, warning_msg = is_meaningful_query(question)
        if not is_valid:
            st.warning(f"⚠️ {warning_msg}")
        else:
            st.toast(f"🔍 Analyzing: \"{question}\"", icon="🤖")

            # 1. Fetch current schema context
            schema_context = generate_schema_context(st.session_state["datasets"])

            try:
                # 2. Call LLM to generate SQL query (Spinner #1 stops as soon as SQL is ready)
                with st.spinner("🤖 AI is generating SQL query..."):
                    generated_sql = generate_SQL_query(schema_context, question)

                # Tier 2: Check if LLM flagged prompt as non-analytical / gibberish
                if generated_sql.strip() == "INVALID_QUERY":
                    st.error("⚠️ Your question doesn't appear to be related to your uploaded dataset or data analysis. Please ask a specific question about your data (e.g., 'What are the top 5 sales by category?').")
                else:
                    # 3. Execute generated SQL on SQLite Database Manager
                    result_df = st.session_state["db_manager"].execute_query(generated_sql)

                    # Trigger animated toast notification immediately after SQL generation!
                    st.toast("✅ SQL Query generated successfully! Generating explanation now...", icon="🚀")

                    # 4. Generate Explanation (Spinner #2 starts only for explanation)
                    with st.spinner("💡 AI is generating explanation..."):
                        sql_explanation = explain_SQL_query(schema_context, question, generated_sql)

                    # Clear prior cached chart config and reset chart display choice and insights for fresh query
                    st.session_state.pop("active_chart_config", None)
                    st.session_state.pop("active_insights", None)
                    st.session_state["show_chart"] = None

                    # Store query state in session state for persistence and interactive editing
                    st.session_state["active_question"] = question
                    st.session_state["active_sql"] = generated_sql
                    st.session_state["active_df"] = result_df
                    st.session_state["active_explanation"] = sql_explanation
                    st.session_state["edited_sql_input"] = generated_sql

                    # Append to query history for tracking
                    if "query_history" not in st.session_state:
                        st.session_state["query_history"] = []
                    st.session_state["query_history"].append(question)

            except Exception as e:
                st.error(f"❌ Failed to generate or run query: {e}")

# Render AI Query Results and Interactive SQL Workbench
if "active_sql" in st.session_state:
    st.markdown("---")
    st.info(f"💬 **Current Question:** *\"{st.session_state.get('active_question', '')}\"*", icon="💡")
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

                    # Clear old chart, insights and reset chart state so new modified SQL gets a fresh choice
                    st.session_state.pop("active_chart_config", None)
                    st.session_state.pop("active_insights", None)
                    st.session_state["show_chart"] = None
        
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

    # --------------------------------------------------------------------------
    # STEP 6: User-Controlled AI Visualization Chart Section
    # --------------------------------------------------------------------------
    active_df = st.session_state.get("active_df")
    active_question = st.session_state.get("active_question", "")

    if active_df is not None and not active_df.empty:
        st.markdown("---")
        show_chart = st.session_state.get("show_chart")

        # Case 1: Prompt user to decide whether they want an AI-generated visualization
        if show_chart is None:
            st.info("📊 **Would you like to see an AI-generated visualization chart for these query results?**", icon="📈")
            col1, col2, _ = st.columns([1.5, 1.5, 3])
            with col1:
                if st.button("📊 Yes, Generate AI Chart", type="primary", use_container_width=True):
                    st.session_state["show_chart"] = True
                    st.rerun()
            with col2:
                if st.button("❌ No, Table View is Enough", use_container_width=True):
                    st.session_state["show_chart"] = False
                    st.rerun()

        # Case 2: User chose to generate and view the AI chart
        elif show_chart is True:
            st.subheader("📊 AI Generated Visualization Chart")

            # Fetch or generate chart that AI has selected
            if "active_chart_config" not in st.session_state:
                with st.spinner("🤖 AI is analyzing query and generating chart based on your question..."):
                    try:
                        st.session_state["active_chart_config"] = recommend_chart_config(active_question, active_df)
                    except Exception as e:
                        st.error(f"Could not generate chart: {e}")
                        st.session_state["active_chart_config"] = None

            chart_config = st.session_state.get("active_chart_config")
            if chart_config:
                figure = generate_plotly_chart(active_df, chart_config)
                if figure is not None:
                    st.plotly_chart(figure, use_container_width=True)

                    # Show AI reasoning for chart generation
                    if "reasoning" in chart_config:
                        st.info(f"💡 **AI Reasoning:** {chart_config['reasoning']}")

                    # Option to hide/collapse the visualization chart
                    if st.button("🙈 Hide Visualization Chart", key="hide_chart_btn"):
                        st.session_state["show_chart"] = False
                        st.rerun()
                else:
                    st.info("ℹ️ AI could not determine an appropriate chart type for this query. The tabular view above contains all result details.")
            else:
                st.info("ℹ️ Visualization could not be generated for this query.")

        # Case 3: User chose not to see the visualization
        elif show_chart is False:
            st.caption("ℹ️ Visualization skipped. You are viewing the tabular results above.")
            if st.button("📊 Generate Visualization Chart Now", key="gen_chart_later_btn"):
                st.session_state["show_chart"] = True
                st.rerun()

    # --------------------------------------------------------------------------
    # STEP 7: Executive Business Insights & Strategic Projections
    # --------------------------------------------------------------------------
    if active_df is not None and not active_df.empty:
        st.markdown("---")
        st.subheader("Business Insights & Recommendations")

        # Check if insights are already generated in session state
        if "active_insights" not in st.session_state or st.session_state["active_insights"] is None:
            if st.button("💡 Genearte AI-Powered Business Insights (AI Pro)", type="primary", use_container_width=True):
                with st.spinner("🤖 AI Pro is analyzing trends, root causes, and future improvement potential..."):
                    chart_config = st.session_state.get("active_chart_config")
                    current_sql = st.session_state.get("active_sql")
                    
                    insights = generate_business_insights(
                        user_question=active_question,
                        df=active_df,
                        chart_config=chart_config,
                        generated_sql=current_sql
                    )
                    st.session_state["active_insights"] = insights
                    st.rerun()

        else:
            # Display generated insights
            st.markdown(st.session_state["active_insights"])

            # Button to refresh/regenerate insights if desired
            if st.button("Refresh business insights"):
                st.session_state.pop("active_insights", None)
                st.rerun()

                
        