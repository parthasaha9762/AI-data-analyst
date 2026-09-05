"""
AI Data Analyst - Main Streamlit Application
=============================================
This is the core entry-point and UI orchestration layer for the AI Data Analyst application.
It integrates all backend and AI modules to provide a seamless, end-to-end conversational
data analysis experience.

Key Application Workflow:
1. Multi-CSV Ingestion & Storage:
   - Allows users to upload one or multiple CSV files.
   - Stores raw datasets in Streamlit's session state.
2. Automated Data Quality & Cleaning:
   - Identifies and auto-cleans missing values (numeric -> 0, text -> 'N/A').
   - Detects and eliminates duplicate rows.
   - Generates summary statistics, table dimensions, and sample previews.
3. In-Memory Database & Schema Management:
   - Loads cleaned DataFrames into an in-memory SQLite database via DatabaseManager.
   - Extracts schema metadata, data types, and primary/foreign key relationships.
   - Compiles a unified schema context formatted specifically for LLMs.
4. Two-Tier Query Validation:
   - Tier 1: Instant heuristic checks to filter empty, trivial, or gibberish input.
   - Tier 2: Semantic validation during SQL generation to catch non-analytical prompts.
5. AI SQL Generation & Plain-English Explanation:
   - Converts natural language business questions into precise, executable SQLite queries.
   - Generates clear, step-by-step business explanations of how the SQL query works.
   - Provides an interactive SQL Workbench for manual edits and immediate re-execution.
6. Intelligent Data Visualization (Plotly):
   - User-controlled visualization trigger (opt-in rendering).
   - AI-powered chart recommendation (Chart type, X/Y axes, color grouping, title).
   - Interactive Plotly figures with high-impact executive conclusion takeaways.
7. Executive Business Insights & Growth Actions (AI Pro):
   - Synthesizes statistical context, query results, and business context.
   - Delivers actionable strategic recommendations and risk/opportunity analyses.
"""

import streamlit as st
import pandas as pd

# ------------------------------------------------------------------------------
# Module Imports & Component Overview
# ------------------------------------------------------------------------------

# Schema metadata generators and relationship detectors for multi-table understanding
from modules.schema_metadata_generator import generate_table_schema, schema_to_Json, generate_multiple_schemas
from modules.releationship_detector import detect_table_releationship

# DatabaseManager: Manages in-memory SQLite database creation, table ingestion, and query execution
from modules.database_manager import DatabaseManager

# Schema Context: Formats database tables, columns, and relationships into LLM-ready prompt text
from modules.schema_context import generate_schema_context

# SQL Generator: Uses Google Gemini to translate natural language questions into SQLite queries
from modules.sql_generator import generate_SQL_query

# SQL Explainer: Breaks down SQL queries into clear, educational, non-technical explanations
from modules.sql_explainer import explain_SQL_query

# Chart Selector: Recommends optimal chart configurations and renders interactive Plotly figures
from modules.chart_selector import generate_plotly_chart, recommend_chart_config

# Query Validator: Validates prompts to filter out greetings, gibberish, or non-analytical queries
from modules.query_validator import is_meaningful_query

# Insight Generator: Produces executive business insights and strategic growth recommendations
from modules.insight_generator import generate_business_insights

# Presentation Generator: Generates 16:9 executive PowerPoint decks (.pptx)
from modules.presentation_generator import create_powerpoint_deck


# Set main application page title in Streamlit UI
st.title("AI Data Analyst")


# ------------------------------------------------------------------------------
# STEP 1: File Upload & Session State Initialization
# ------------------------------------------------------------------------------
# We initialize session state variables to ensure that uploaded data, database connections,
# and query states persist across Streamlit reruns without requiring re-uploading.

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
# This maintains a single active SQLite database connection throughout the user's session
if "db_manager" not in st.session_state:
    st.session_state["db_manager"] = DatabaseManager()

# Initialize conversational memory buffer to support multi-turn follow-up questions
# Stores the last few question/SQL pairs so the LLM can understand follow-up context
if "conversation_history" not in st.session_state:
    st.session_state["conversation_history"] = []

# ------------------------------------------------------------------------------
# STEP 2: Process & Inspect Uploaded CSV Files
# ------------------------------------------------------------------------------

if uploaded_files:
    st.write("Uploaded files...")
    for file in uploaded_files:
        # Reset the file buffer cursor to byte 0 before reading to avoid empty reads on reruns
        file.seek(0)
        
        # Read the CSV file into a Pandas DataFrame
        df = pd.read_csv(file)
    
        # Extract the table name from the file name (e.g., "orders.csv" -> "orders")
        # This table name will serve as the SQL table identifier in SQLite
        table_name = file.name.rsplit(".", 1)[0]

        # Store the raw DataFrame in session state so other modules can access it
        st.session_state["datasets"][table_name] = df

        # Display confirmation of file name and assigned table name to the user
        st.write(f"✅ **File:** `{file.name}` ➔ **Table Name:** `{table_name}`")

        # --- Data Quality Checks & Automated Data Cleaning ---
        
        # 1. Missing Values Check & Auto-Cleaning
        # Null values can cause SQL aggregation discrepancies and plotting errors;
        # we detect missing values and apply safe default imputations.
        missing_values = df.isnull().sum()
        with st.expander("Show missing values"):           
            if missing_values.sum() > 0:
                st.write(missing_values[missing_values > 0])

                # Impute missing numeric values with 0, text/categorical values with "N/A"
                for col in df.columns:
                    if "int" in str(df[col].dtype).lower() or "float" in str(df[col].dtype).lower():
                        df[col] = df[col].fillna(0)
                    else:
                        df[col] = df[col].fillna("N/A")

                # Update session state storage with the cleaned DataFrame
                st.session_state["datasets"][table_name] = df
                st.success("Missing values have been auto-cleaned! (Numeric ➔ 0, Text ➔ 'N/A') 🎉")
            else:
                st.write("No missing values found! 🎉")

        # 2. Duplicate Records Check & Auto-Cleaning
        # Duplicate rows inflate totals and distort analytics; we detect and remove exact matches.
        num_duplicates = df.duplicated().sum()
        with st.expander("Show duplicate records"):
            if num_duplicates > 0:
                st.write(f"❌ Found **{num_duplicates}** duplicate records!")
                st.dataframe(df[df.duplicated()])

                # Drops ONLY rows where all columns are 100% identical, then resets the integer index
                df = df.drop_duplicates().reset_index(drop=True)
                st.session_state["datasets"][table_name] = df 
                st.success("Duplicate records have been cleared!")
            else:
                st.write("No duplicate records found! 🎉")


        # 3. Descriptive Summary Statistics
        # Computes count, mean, std, min, 25%, 50%, 75%, max for numeric columns for quick exploration
        with st.expander("Show statistics"):
            st.write(df.describe())

        # 4. Table Dimensions
        # Informs the user of total row and column counts
        st.write(f"No: of rows: {len(df)}  \nNo: of columns: {len(df.columns)}")

        # 5. Data Preview & Simplified Data Types
        # Provides an initial 10-row glimpse with user-friendly 1-based indexing
        with st.expander("Show sample rows of the table"):
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
    # sample values, and detected relationships formatted specifically for LLM prompt context
    schema_context = generate_schema_context(st.session_state["datasets"])

    # Display the AI-readable schema context formatted for the LLM
    with st.expander("Show AI-Readable Schema Context (for LLM)"):
        st.code(schema_context, language="text")

    # Load all uploaded and cleaned datasets into SQLite database tables
    # This enables real SQL queries to be executed directly against in-memory tables
    st.session_state["db_manager"].load_datasets(st.session_state["datasets"])


    # --------------------------------------------------------------------------
    # STEP 3: Multi-Table Schema Metadata Generation [UI Hidden]
    # --------------------------------------------------------------------------
    # Inspects data types, null percentages, cardinality, and primary key candidates across tables
    schema_table_dictionary = generate_multiple_schemas(st.session_state["datasets"])
    
    # Kept commented out: runs in backend, available for future UI debugging if needed
    # schema_JSON = schema_to_Json(schema_table_dictionary)
    # with st.expander("Show all the metadata schemas in JSON format"):
    #     st.json(schema_JSON)

    # --------------------------------------------------------------------------
    # STEP 4: Table Relationship Detection (Foreign Key -> Primary Key) [UI Hidden]
    # --------------------------------------------------------------------------
    # Note: Table relationship detection runs automatically in the backend inside schema_context.py.
    # Kept commented out here for future UI display if needed.
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

# Inject custom CSS to give the bottom chat input a floating, modern shadow and rounded border
st.markdown("""
<style>
div[data-testid="stChatInput"] {
    border-radius: 12px;
    box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.15);
}
</style>
""", unsafe_allow_html=True)

# Count how many previous questions are currently stored in memory
turn_count = len(st.session_state.get("conversation_history", []))


# Fixed Chat Input anchored to the bottom of the viewport for easy conversational queries
user_prompt = st.chat_input("💬 Ask any question about your data (e.g., 'What are the top 5 sales by category?')...")

# Handle natural language query submission logic
if user_prompt:
    # Validation check: Ensure the user has uploaded datasets before querying
    if not st.session_state.get("datasets"):
        st.warning("⚠️ Please upload at least one CSV file first before analyzing!")
    elif user_prompt.strip():
        question = user_prompt.strip()

        # --- Tier 1 Validation: Fast Heuristic Validation (0ms latency, zero API cost) ---
        # Filters out single characters, random strings, greetings, and empty questions
        is_valid, warning_msg = is_meaningful_query(question)
        if not is_valid:
            st.warning(f"⚠️ {warning_msg}")
        else:
            # Display an immediate toast notification that analysis has commenced
            st.toast(f"🔍 Analyzing: \"{question}\"", icon="🤖")

            # 1. Fetch current schema context representing the uploaded datasets
            schema_context = generate_schema_context(st.session_state["datasets"])

            try:
                # 2. Call LLM to translate natural language question into an SQL query
                # Spinner #1 runs specifically for SQL generation
                with st.spinner("🤖 AI is generating SQL query..."):
                    generated_sql, is_follow_up = generate_SQL_query(
                        schema_context=schema_context, 
                        user_question=question, 
                        conversation_history=st.session_state.get("conversation_history", [])
                    )

                # --- Tier 2 Validation: LLM Semantic Verification ---
                # Check if the LLM flagged the prompt as non-analytical or unrelated to the schema
                if generated_sql.strip() == "INVALID_QUERY":
                    st.error("⚠️ Your question doesn't appear to be related to your uploaded dataset or data analysis. Please ask a specific question about your data (e.g., 'What are the top 5 sales by category?').")
                else:
                    # 3. Execute the generated SQL query on the SQLite database engine
                    result_df = st.session_state["db_manager"].execute_query(generated_sql)

                    # Trigger animated toast notification immediately after SQL generation!
                    st.toast("✅ SQL Query generated successfully! Generating explanation now...", icon="🚀")

                    # 4. Generate plain-English explanation for the generated SQL query
                    # Spinner #2 runs specifically for explanation generation
                    with st.spinner("💡 AI is generating explanation..."):
                        sql_explanation = explain_SQL_query(schema_context, question, generated_sql)

                    # Clear prior cached chart config, insights, and chart display toggle for fresh query
                    st.session_state.pop("active_chart_config", None)
                    st.session_state.pop("active_insights", None)
                    st.session_state.pop("active_figure", None)
                    st.session_state["show_chart"] = None

                    # Store current active query state in session state for persistence and interactive editing
                    st.session_state["active_question"] = question
                    st.session_state["active_sql"] = generated_sql
                    st.session_state["active_df"] = result_df
                    st.session_state["active_explanation"] = sql_explanation
                    st.session_state["edited_sql_input"] = generated_sql

                    # Track question in history for auditing and user context
                    if "query_history" not in st.session_state:
                        st.session_state["query_history"] = []

                    st.session_state["query_history"].append(question)

                    # --- Automatic Conversational Memory Management with Topic Shift Detection ---
                    if is_follow_up:
                        # Follow-up detected -> append to existing conversation thread
                        st.session_state["conversation_history"].append({
                            "question": question,
                            "sql": generated_sql
                        })
                    else:
                        # NEW TOPIC detected -> automatically reset memory and start fresh thread as Turn 1
                        st.session_state["conversation_history"] = [{
                            "question": question,
                            "sql": generated_sql
                        }]
  

            except Exception as e:
                st.error(f"❌ Failed to generate or run query: {e}")

# ------------------------------------------------------------------------------
# Render Active Query Results, SQL Workbench, and Explanations
# ------------------------------------------------------------------------------
if "active_sql" in st.session_state:
    st.markdown("---")
    turn_count = len(st.session_state.get("conversation_history", []))
    if turn_count > 0:
        col_q, col_btn = st.columns([4, 1])
        with col_q:
            st.info(f"💬 **Current Question:** *\"{st.session_state.get('active_question', '')}\"* &nbsp; `🧠 Memory: {turn_count} prior turn{'s' if turn_count > 1 else ''}`", icon="💡")
    else:
        st.info(f"💬 **Current Question:** *\"{st.session_state.get('active_question', '')}\"*", icon="💡")

    st.success("SQL Query generated successfully! 🪄✨", icon="✅")
    st.subheader("Generated SQL Query")
    st.code(st.session_state["active_sql"], language="sql")

    # Interactive SQL Workbench: Allows users to inspect, modify, and re-run SQL queries directly
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
                    # Execute modified SQL query on SQLite
                    new_df = st.session_state["db_manager"].execute_query(edited_sql)
                    st.session_state["active_sql"] = edited_sql
                    st.session_state["active_df"] = new_df

                    # Clear old chart and insights so the newly modified SQL gets fresh visualizations and insights
                    st.session_state.pop("active_chart_config", None)
                    st.session_state.pop("active_insights", None)
                    st.session_state["show_chart"] = None
        
                    st.success("Modified query executed successfully! 🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"Query execution failed: {e}")
            else:
                st.warning("Please enter a valid SQL query.")

    # Display Tabular Query Results
    st.subheader("Query Results")
    if st.session_state.get("active_df") is not None:
        st.dataframe(st.session_state["active_df"], use_container_width=True, hide_index=True)
        st.success("Query executed successfully! 🎉")
        
        # Display plain-English explanation breakdown
        st.subheader("Explanation behind this query")
        st.markdown(st.session_state["active_explanation"])

    # --------------------------------------------------------------------------
    # STEP 6: User-Controlled AI Visualization Chart Section
    # --------------------------------------------------------------------------
    # Gives the user control over whether to generate visual charts, avoiding unnecessary
    # chart generation API calls when a tabular view is sufficient.
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

        # Case 2: User opted to generate and view the AI visualization chart
        elif show_chart is True:
            st.subheader("📊 AI Generated Visualization Chart")

            # Fetch or generate chart configuration recommended by Gemini LLM
            if "active_chart_config" not in st.session_state:
                with st.spinner("🤖 AI is analyzing query and generating chart based on your question..."):
                    try:
                        st.session_state["active_chart_config"] = recommend_chart_config(active_question, active_df)
                    except Exception as e:
                        st.error(f"Could not generate chart: {e}")
                        st.session_state["active_chart_config"] = None

            chart_config = st.session_state.get("active_chart_config")
            if chart_config:
                # Render the Plotly figure from chart configuration dictionary
                figure = generate_plotly_chart(active_df, chart_config)

                # Store generated chart figure for download functionality
                st.session_state["active_figure"] = figure

                if figure is not None:
                    st.plotly_chart(figure, use_container_width=True)

                    # Single-Line Executive Chart Takeaway / Conclusion
                    if "conclusion" in chart_config and chart_config["conclusion"]:
                        # Escape dollar signs ($) so Streamlit doesn't parse currency as LaTeX math syntax
                        clean_conclusion = chart_config["conclusion"].replace("$", r"\$")
                        st.write(f"**THE CONCLUSION:** {clean_conclusion}\n\n")

                    # Display the AI's plain-English reasoning for why this chart type was selected
                    if "reasoning" in chart_config:
                        st.info(f"💡 **AI Reasoning:** {chart_config['reasoning']}")

                    # Provide an option to collapse/hide the visualization chart
                    if st.button("🙈 Hide Visualization Chart", key="hide_chart_btn"):
                        st.session_state["show_chart"] = False
                        st.rerun()
                else:
                    st.info("ℹ️ AI could not determine an appropriate chart type for this query. The tabular view above contains all result details.")
            else:
                st.info("ℹ️ Visualization could not be generated for this query.")

        # Case 3: User initially chose not to see the visualization; provide an option to reconsider
        elif show_chart is False:
            st.caption("ℹ️ Visualization skipped. You are viewing the tabular results above.")
            if st.button("📊 Generate Visualization Chart Now", key="gen_chart_later_btn"):
                st.session_state["show_chart"] = True
                st.rerun()

    # --------------------------------------------------------------------------
    # STEP 7: Executive Business Insights & Growth Actions (Gemini Pro)
    # --------------------------------------------------------------------------
    # Formulates high-level strategic insights, performance metrics, and growth recommendations
    # based on statistical context, SQL query logic, and user question intent.
    if active_df is not None and not active_df.empty:
        st.markdown("---")
        st.subheader("💡 Executive Business Insights & Growth Actions")

        # Check if insights are already generated in session state
        if "active_insights" not in st.session_state or st.session_state["active_insights"] is None:
            # On-demand button trigger avoids automatic API token usage until the user requests insights
            if st.button("💡 Generate AI-Powered Business Insights (AI Pro)", type="primary", use_container_width=True):
                with st.spinner("🤖 AI Pro is analyzing trends and formulating key takeaways..."):
                    chart_config = st.session_state.get("active_chart_config")
                    current_sql = st.session_state.get("active_sql")
                    
                    # Generate deep business insights using Gemini Pro model
                    insights = generate_business_insights(
                        user_question=active_question,
                        df=active_df,
                        chart_config=chart_config,
                        generated_sql=current_sql
                    )
                    st.session_state["active_insights"] = insights
                    st.rerun()

        else:
            # Display generated markdown insights inside a styled container
            with st.container():
                st.markdown(st.session_state["active_insights"])

            # Button to refresh/regenerate insights if desired
            if st.button("🔄 Refresh Business Insights", key="refresh_insights_btn"):
                st.session_state.pop("active_insights", None)
                st.rerun()


    # --------------------------------------------------------------------------
    # STEP 8: Executive PowerPoint Presentation Export (.pptx)
    # --------------------------------------------------------------------------
    # Generate a boardroom-ready, executive 16:9 widescreen PowerPoint presentation.
    
    if active_df is not None and not active_df.empty:
        st.markdown("---")
        st.subheader("Export and share analysis")
        st.caption("Generate an executive-ready 16:9 PowerPoint slide deck summarizing this analysis, visual chart, and strategic insights.")

        # Gather current analysis artifacts
        current_question = st.session_state.get("active_question", "Data Analysis briefing")
        current_sql = st.session_state.get("active_sql","")
        current_explanation = st.session_state.get("active_explanation","")
        current_chart_config = st.session_state.get("active_chart_config")
        current_fig = st.session_state.get("active_figure")
        current_insights = st.session_state.get("active_insights", "")
        dataset_names = list(st.session_state.get("datasets", {}).keys())
        

        # Compile presentation in memory
        try:
            pptx_bytes = create_powerpoint_deck(
                user_question=current_question,
                df=active_df,
                generated_sql=current_sql,
                sql_explanation=current_explanation,
                chart_figure=current_fig,
                chart_config=current_chart_config,
                business_insights=current_insights,
                dataset_names=dataset_names
            )

            # Generate clean filename
            filename = f"Analysis Deck.pptx"

            # Display download button in download-themed container
            if pptx_bytes:

                col_btn, _ = st.columns([2,3])
                with col_btn:
                    st.download_button(
                        label="📥 Download Presentation (PPTX) file",
                        data=pptx_bytes,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        type="primary",
                        use_container_width=True
                    )

                st.caption(f"Saved as: {filename} • Executive widescreen slide deck • Ready for board meetings and stakeholder briefings")

        except Exception as e:
            st.error("Sorry! Could not generate presentation deck. Please try again.")

        