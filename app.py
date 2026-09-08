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

from pathlib import Path
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
from modules.sql_generator import generate_SQL_query, synthesize_standalone_question

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


# ------------------------------------------------------------------------------
# Page Configuration & UI Theme Styling
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Data Analyst - Enterprise Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_css(file_path: Path):
    """Loads and injects external CSS stylesheet into Streamlit."""
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Load external CSS styles & dynamic keyframe animations from assets/style.css
load_css(Path(__file__).resolve().parent / "assets" / "style.css")


# ------------------------------------------------------------------------------
# STEP 0: Executive Hero Header Banner (Animated)
# ------------------------------------------------------------------------------
st.markdown("""
<div class="hero-wrapper">
    <div class="hero-header-row">
        <h1 class="hero-title">⚡ AI Data Analyst</h1>
        <div class="hero-badge-live">
            <span class="hero-badge-dot"></span>
            Enterprise Engine Active
        </div>
    </div>
    <div class="hero-subtitle">
        Autonomous Multi-Table Intelligence • Automated Data Quality & Preprocessing Using Pandas • Zero-Shot SQL Generation • Interactive Plotly Studio • Executive Presentation Deck Export 
    </div>
    <div class="hero-tags-row">
        <span class="hero-tag">🔗 Multi-CSV Relational Ingestion</span>
        <span class="hero-tag">🧹 Automated Data Quality & Imputation Using Pandas</span>
        <span class="hero-tag">🧠 Gemini Two-Tier Semantic SQL</span>
        <span class="hero-tag">📊 Dynamic Plotly Visualizations</span>
        <span class="hero-tag">💡 Strategic Growth Actions (AI Pro)</span>
        <span class="hero-tag">💼 16:9 PowerPoint Briefing Deck</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# STEP 1: Session State Initialization & Workspace Setup
# ------------------------------------------------------------------------------
# Key = table_name (e.g. "orders"), Value = Pandas DataFrame
if "datasets" not in st.session_state:
    st.session_state["datasets"] = {}

# Audit dictionary to track cleaning metrics and missing/duplicate row dataframes
if "cleaning_audit" not in st.session_state:
    st.session_state["cleaning_audit"] = {}

# Initialize DatabaseManager in session state if not present
# This maintains a single active SQLite database connection throughout the user's session
if "db_manager" not in st.session_state:
    st.session_state["db_manager"] = DatabaseManager()

# Initialize conversational memory buffer to support multi-turn follow-up questions
# Stores the last few question/SQL pairs so the LLM can understand follow-up context
if "conversation_history" not in st.session_state:
    st.session_state["conversation_history"] = []


# ------------------------------------------------------------------------------
# STEP 2: Sample Datasets Showcase & Download Helper
# ------------------------------------------------------------------------------
sample_directory = Path(__file__).resolve().parent / "sample_datasets"
if not sample_directory.exists():
    sample_directory = Path("sample_datasets")

sample_info = [
    {
        "filename": "customers.csv",
        "title": "👥 customers.csv",
        "desc": "2,600 raw records • 5 columns\n(Includes sample nulls & duplicate rows to test data cleaning)",
        "key": "dl_cust_raw"
    },
    {
        "filename": "orders.csv",
        "title": "📦 orders.csv",
        "desc": "10,300 raw records • 7 columns\n(Includes sample nulls & duplicate rows to test data cleaning)",
        "key": "dl_orders_raw"
    },
    {
        "filename": "products.csv",
        "title": "🏷️ products.csv",
        "desc": "215 raw records • 5 columns\n(Includes sample nulls & duplicate rows to test data cleaning)",
        "key": "dl_prod_raw"
    }
]

with st.expander("💡 **Don't have a CSV file? Download or load sample datasets to test features**", expanded=not bool(st.session_state.get("datasets"))):
    st.caption("Download our raw sample datasets containing real-world quality scenarios or **load all 3 relational tables instantly with 1-click** to test automated preprocessing, SQL joins, interactive charts, and executive presentations:")

    # 1-Click Direct Sample Dataset Loader & Unloader
    is_sample_active = (st.session_state.get("dataset_source") == "sample" and bool(st.session_state.get("datasets")))
    col_load, col_info = st.columns([1.6, 3.4])

    with col_load:
        if is_sample_active:
            if st.button("🗑️ Remove Sample Datasets", type="secondary", use_container_width=True):
                st.session_state["datasets"] = {}
                st.session_state["cleaning_audit"] = {}
                st.session_state["db_manager"] = DatabaseManager()
                st.session_state["conversation_history"] = []
                st.session_state.pop("active_sql", None)
                st.session_state.pop("active_df", None)
                st.session_state.pop("active_question", None)
                st.session_state.pop("active_explanation", None)
                st.session_state.pop("active_chart_config", None)
                st.session_state.pop("active_insights", None)
                st.session_state.pop("active_figure", None)
                st.session_state.pop("dataset_source", None)
                st.session_state["show_chart"] = None
                st.toast("Sample datasets removed!", icon="🗑️")
                st.rerun()
        else:
            if st.button("⚡ Load All 3 Sample Datasets (1-Click)", type="primary", use_container_width=True):
                for item in sample_info:
                    fpath = sample_directory / item["filename"]
                    if fpath.exists():
                        raw_df = pd.read_csv(fpath)
                        table_name = item["filename"].rsplit(".", 1)[0]
                        orig_len = len(raw_df)

                        # Missing values analysis
                        missing_by_col = raw_df.isnull().sum()
                        missing_by_col = missing_by_col[missing_by_col > 0]
                        null_count = int(missing_by_col.sum())
                        missing_rows_df = raw_df[raw_df.isnull().any(axis=1)].copy()

                        # Duplicate records analysis
                        dup_count = int(raw_df.duplicated().sum())
                        duplicate_rows_df = raw_df[raw_df.duplicated(keep=False)].copy()

                        # Auto-clean nulls
                        df = raw_df.copy()
                        for col in df.columns:
                            if "int" in str(df[col].dtype).lower() or "float" in str(df[col].dtype).lower():
                                df[col] = df[col].fillna(0)
                            else:
                                df[col] = df[col].fillna("N/A")

                        # Auto-clean duplicates
                        df = df.drop_duplicates().reset_index(drop=True)

                        st.session_state["datasets"][table_name] = df
                        st.session_state["cleaning_audit"][table_name] = {
                            "orig_rows": orig_len,
                            "final_rows": len(df),
                            "nulls_fixed": null_count,
                            "missing_by_col": missing_by_col,
                            "missing_rows_df": missing_rows_df,
                            "dups_removed": dup_count,
                            "duplicate_rows_df": duplicate_rows_df
                        }

                st.session_state["dataset_source"] = "sample"
                st.session_state["db_manager"].load_datasets(st.session_state["datasets"])
                st.toast("✅ All 3 Sample Datasets auto-cleaned and loaded into SQLite!", icon="🚀")
                st.rerun()

    with col_info:
        if is_sample_active:
            st.markdown("""
            <div style="padding-top: 8px; font-size: 0.88rem; color: #34D399; font-weight: 600;">
                🟢 <b>Sample Datasets Active:</b> <code>customers</code>, <code>orders</code>, and <code>products</code> are loaded in SQLite engine.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("⚡ **Instant Demo Mode**: Automatically ingests `customers`, `orders`, and `products`, resolves foreign key joins, and launches the AI analysis engine.")

    st.markdown("---")
    cols = st.columns(3)
    for idx, item in enumerate(sample_info):
        full_path = sample_directory / item["filename"]
        with cols[idx]:
            st.markdown(f"**{item['title']}**")
            st.caption(item["desc"])
            if full_path.exists():
                with open(full_path, "rb") as file:
                    try:
                        file.seek(0)
                        st.download_button(
                            label=f"📥 Download `{item['filename']}`",
                            data=file.read(),
                            file_name=item["filename"],
                            mime="text/csv",
                            key=item["key"],
                            use_container_width=True
                        )
                    except Exception:
                        st.error("Download failed for technical issue. Please try again later.")
            else:
                st.warning(f"Error: {item['filename']} not found.")


# ------------------------------------------------------------------------------
# STEP 3: File Upload & Multi-CSV Ingestion
# ------------------------------------------------------------------------------
uploaded_files = st.file_uploader(
    "Upload your CSV files", type=["csv"],
    accept_multiple_files=True
)

if uploaded_files:
    new_datasets = {}
    new_cleaning_audit = {}
    for file in uploaded_files:
        file.seek(0)
        raw_df = pd.read_csv(file)
        table_name = file.name.rsplit(".", 1)[0]
        orig_len = len(raw_df)

        # Missing values analysis
        missing_by_col = raw_df.isnull().sum()
        missing_by_col = missing_by_col[missing_by_col > 0]
        null_count = int(missing_by_col.sum())
        missing_rows_df = raw_df[raw_df.isnull().any(axis=1)].copy()

        # Duplicate records analysis
        dup_count = int(raw_df.duplicated().sum())
        duplicate_rows_df = raw_df[raw_df.duplicated(keep=False)].copy()

        # Auto-cleaning: Impute missing numeric values with 0, text/categorical with "N/A"
        df = raw_df.copy()
        for col in df.columns:
            if "int" in str(df[col].dtype).lower() or "float" in str(df[col].dtype).lower():
                df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna("N/A")

        # Auto-cleaning: Drops ONLY rows where all columns are 100% identical
        df = df.drop_duplicates().reset_index(drop=True)

        new_datasets[table_name] = df
        new_cleaning_audit[table_name] = {
            "orig_rows": orig_len,
            "final_rows": len(df),
            "nulls_fixed": null_count,
            "missing_by_col": missing_by_col,
            "missing_rows_df": missing_rows_df,
            "dups_removed": dup_count,
            "duplicate_rows_df": duplicate_rows_df
        }

    st.session_state["datasets"] = new_datasets
    st.session_state["cleaning_audit"] = new_cleaning_audit
    st.session_state["dataset_source"] = "upload"
elif st.session_state.get("dataset_source") == "upload":
    # If the user cross-removed all uploaded files from the uploader, clear the dataset state
    st.session_state["datasets"] = {}
    st.session_state["cleaning_audit"] = {}


# ------------------------------------------------------------------------------
# STEP 4: Interactive Executive Data Quality & Relational Schema Inspection
# ------------------------------------------------------------------------------
if st.session_state.get("datasets"):
    datasets = st.session_state["datasets"]

    # Load cleaned datasets into SQLite database
    st.session_state["db_manager"].load_datasets(datasets)

    # Calculate overall data health stats
    total_tbls = len(datasets)
    total_records = sum(len(d) for d in datasets.values())
    total_columns_count = sum(len(d.columns) for d in datasets.values())
    total_nulls = sum(st.session_state.get("cleaning_audit", {}).get(t, {}).get("nulls_fixed", 0) for t in datasets)
    total_dups = sum(st.session_state.get("cleaning_audit", {}).get(t, {}).get("dups_removed", 0) for t in datasets)

    # Executive Metric KPI Tiles Row (with Animations)
    st.markdown("### 📊 Ingested Datasets & Data Quality Health")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        st.markdown(f"""
        <div class="metric-card-container">
            <div class="metric-card-top">
                <span class="metric-card-label">Active Tables</span>
                <span class="metric-card-icon">📁</span>
            </div>
            <div class="metric-card-value">{total_tbls}</div>
            <div class="metric-card-desc">In-memory SQLite tables ready</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        st.markdown(f"""
        <div class="metric-card-container">
            <div class="metric-card-top">
                <span class="metric-card-label">Total Ingested Rows</span>
                <span class="metric-card-icon">📊</span>
            </div>
            <div class="metric-card-value">{total_records:,}</div>
            <div class="metric-card-desc">Cleaned & preprocessed</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col3:
        st.markdown(f"""
        <div class="metric-card-container">
            <div class="metric-card-top">
                <span class="metric-card-label">Auto-Cleaned Values</span>
                <span class="metric-card-icon">🧹</span>
            </div>
            <div class="metric-card-value">{total_nulls + total_dups:,}</div>
            <div class="metric-card-desc">{total_nulls} nulls filled • {total_dups} duplicates purged</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col4:
        st.markdown(f"""
        <div class="metric-card-container">
            <div class="metric-card-top">
                <span class="metric-card-label">Total Features</span>
                <span class="metric-card-icon">🏷️</span>
            </div>
            <div class="metric-card-value">{total_columns_count}</div>
            <div class="metric-card-desc">Columns across all tables</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Interactive Tabbed Dataset Explorer
    tab_overview, tab_cleaning, tab_preview, tab_stats, tab_schema = st.tabs([
        "📁 Tables & Dimensions",
        "🧹 Data Quality Audit Log",
        "🔍 Interactive Data Explorer",
        "📈 Statistical Distributions",
        "🤖 AI Schema Context (for LLM)"
    ])

    with tab_overview:
        overview_cols = st.columns(min(len(datasets), 3))
        for idx, (tname, tdf) in enumerate(datasets.items()):
            col_target = overview_cols[idx % 3]
            with col_target:
                st.markdown(f"""
                <div class="custom-card" style="padding: 18px; margin-bottom: 12px; border: 1px solid rgba(99, 102, 241, 0.25);">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #60A5FA; margin-bottom: 8px;">
                        📄 Table: <code>{tname}</code>
                    </div>
                    <div style="font-size: 0.92rem; color: #CBD5E1; line-height: 1.7;">
                        • <b>Total Rows:</b> {len(tdf):,}<br>
                        • <b>Total Columns:</b> {len(tdf.columns)} ({", ".join(list(tdf.columns)[:4])}{"..." if len(tdf.columns) > 4 else ""})<br>
                        • <b>Memory Usage:</b> ~{tdf.memory_usage(deep=True).sum() / 1024:.1f} KB
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab_cleaning:
        st.markdown("#### 🧹 Data Quality Audit Log")
        st.caption("Summary of total records, duplicate records, and missing values detected and cleaned across tables:")
        
        audit_cols = st.columns(len(datasets))
        for idx, (tname, tdf) in enumerate(datasets.items()):
            audit = st.session_state.get("cleaning_audit", {}).get(tname, {})
            orig_rows = audit.get("orig_rows", len(tdf))
            nulls_f = audit.get("nulls_fixed", 0)
            dups_f = audit.get("dups_removed", 0)
            final_rows = audit.get("final_rows", len(tdf))

            with audit_cols[idx]:
                st.markdown(f"""
                <div class="custom-card" style="padding: 22px; border-radius: 16px; border: 1px solid rgba(99, 102, 241, 0.3); background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%); min-height: 230px;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #60A5FA; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                        📄 Table: <code>{tname}</code>
                    </div>
                    <div style="font-size: 0.95rem; color: #F1F5F9; line-height: 2.0; margin-bottom: 12px;">
                        • <b>Total records:</b> <span style="color: #38BDF8; font-weight: 700;">{orig_rows:,}</span><br>
                        • <b>Duplicate records:</b> <span style="color: {'#F87171' if dups_f > 0 else '#34D399'}; font-weight: 700;">{dups_f:,}</span><br>
                        • <b>Missing values:</b> <span style="color: {'#FBBF24' if nulls_f > 0 else '#34D399'}; font-weight: 700;">{nulls_f:,}</span>
                    </div>
                    <div style="border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 12px; font-size: 0.88rem; line-height: 1.6;">
                        <div style="color: #34D399; font-weight: 600; margin-bottom: 4px;">
                            {'✅ ' + str(dups_f) + ' duplicate records purged & cleaned' if dups_f > 0 else '✨ No duplicate records detected'}
                        </div>
                        <div style="color: #38BDF8; font-weight: 600; margin-bottom: 4px;">
                            {'✅ ' + str(nulls_f) + ' missing values filled (0 for numbers, "N/A" for text)' if nulls_f > 0 else '✨ No missing values detected'}
                        </div>
                        <div style="color: #A5B4FC; font-weight: 600;">
                            🚀 Clean dataset: <b>{final_rows:,} rows</b> ready for analysis
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab_preview:
        selected_tbl = st.selectbox("Select table to inspect:", list(datasets.keys()), key="preview_tbl_select")
        if selected_tbl:
            curr_df = datasets[selected_tbl]
            st.markdown(f"**First 10 sample rows of `{selected_tbl}`:**")
            sample_df = curr_df.head(10).copy()
            sample_df.index = range(1, len(sample_df) + 1)
            st.dataframe(sample_df, use_container_width=True)

            with st.expander(f"📋 View Column Data Types for `{selected_tbl}`"):
                clean_dtypes = pd.Series(
                    [
                        "int" if "int" in str(dt) else
                        "float" if "float" in str(dt) else
                        "boolean" if "bool" in str(dt) else str(dt)
                        for dt in curr_df.dtypes
                    ],
                    index=curr_df.columns
                )
                st.write(clean_dtypes)

    with tab_stats:
        selected_stat_tbl = st.selectbox("Select table for descriptive statistics:", list(datasets.keys()), key="stat_tbl_select")
        if selected_stat_tbl:
            num_desc = datasets[selected_stat_tbl].describe()
            if not num_desc.empty:
                st.dataframe(num_desc, use_container_width=True)
            else:
                st.info("No numeric columns found in this table for statistical distribution.")

    with tab_schema:
        schema_context_text = generate_schema_context(datasets)
        st.markdown("#### 🤖 AI-Readable Schema Context (for LLM)")
        st.caption("Structured schema representation formatted specifically for LLM zero-shot query generation:")
        st.code(schema_context_text, language="text")


# ------------------------------------------------------------------------------
# STEP 5: Natural Language Query Interface
# ------------------------------------------------------------------------------
if st.session_state.get("datasets"):
    with st.expander("⚡ **Quick Analytical Prompts (Click to Analyze)**", expanded=False):
        prompt_cols = st.columns(3)
        suggested_prompts = [
            "🏆 Top 5 customers by total spending",
            "📦 Total revenue & order count by product category",
            "📈 Monthly sales trends over time",
            "🏙️ Top 5 cities with highest revenue",
            "🏷️ Top 5 most expensive products",
            "👥 Customer distribution by country"
        ]
        for idx, prompt_text in enumerate(suggested_prompts):
            with prompt_cols[idx % 3]:
                if st.button(prompt_text, key=f"quick_prompt_{idx}", use_container_width=True):
                    st.session_state["pending_prompt"] = prompt_text
                    st.rerun()

pending_prompt = st.session_state.pop("pending_prompt", None)
user_prompt = st.chat_input("💬 Ask any business question about your data (e.g. 'What are the top 5 sales by category?')...")

active_input_prompt = pending_prompt or user_prompt

if active_input_prompt:
    # Validation check: Ensure the user has uploaded datasets before querying
    if not st.session_state.get("datasets"):
        st.warning("⚠️ Please upload at least one CSV file or load sample datasets first before analyzing!")
    elif active_input_prompt.strip():
        question = active_input_prompt.strip()

        # --- Tier 1 Validation: Fast Heuristic Validation (0ms latency, zero API cost) ---
        is_valid, warning_msg = is_meaningful_query(question)
        if not is_valid:
            st.warning(f"⚠️ {warning_msg}")
        else:
            st.toast(f"🔍 Analyzing: \"{question}\"", icon="🤖")

            # 1. Fetch current schema context representing the uploaded datasets
            schema_context = generate_schema_context(st.session_state["datasets"])

            try:
                # 2. Call LLM to translate natural language question into an SQL query
                with st.spinner("🤖 AI is synthesizing schema context and generating SQL query..."):
                    generated_sql, is_follow_up = generate_SQL_query(
                        schema_context=schema_context, 
                        user_question=question, 
                        conversation_history=st.session_state.get("conversation_history", [])
                    )

                # --- Tier 2 Validation: LLM Semantic Verification ---
                if generated_sql.strip() == "INVALID_QUERY":
                    st.error("⚠️ Your question doesn't appear to be related to your uploaded dataset or data analysis. Please ask a specific question about your data (e.g., 'What are the top 5 sales by category?').")
                else:
                    # 3. Execute the generated SQL query on the SQLite database engine
                    result_df = st.session_state["db_manager"].execute_query(generated_sql)

                    st.toast("✅ SQL Query generated successfully! Generating explanation now...", icon="🚀")

                    # If this is a conversational follow-up, synthesize a complete standalone question for executive presentation, charts, and insights
                    if is_follow_up and st.session_state.get("conversation_history"):
                        resolved_question = synthesize_standalone_question(
                            conversation_history=st.session_state.get("conversation_history", []),
                            current_question=question,
                            generated_sql=generated_sql
                        )
                    else:
                        resolved_question = question

                    # 4. Generate plain-English explanation for the generated SQL query
                    with st.spinner("💡 AI is formulating business explanation..."):
                        sql_explanation = explain_SQL_query(schema_context, resolved_question, generated_sql)

                    # Clear prior cached chart config, insights, and chart display toggle for fresh query
                    st.session_state.pop("active_chart_config", None)
                    st.session_state.pop("active_insights", None)
                    st.session_state.pop("active_figure", None)
                    st.session_state["show_chart"] = None

                    # Store current active query state in session state for persistence and interactive editing
                    st.session_state["active_question"] = resolved_question
                    st.session_state["active_sql"] = generated_sql
                    st.session_state["active_df"] = result_df
                    st.session_state["active_explanation"] = sql_explanation
                    st.session_state["edited_sql_input"] = generated_sql

                    # Track question in history for auditing and user context
                    if "query_history" not in st.session_state:
                        st.session_state["query_history"] = []

                    st.session_state["query_history"].append(resolved_question)

                    # --- Automatic Conversational Memory Management with Topic Shift Detection ---
                    if is_follow_up:
                        st.session_state["conversation_history"].append({
                            "question": resolved_question,
                            "sql": generated_sql
                        })
                    else:
                        st.session_state["conversation_history"] = [{
                            "question": resolved_question,
                            "sql": generated_sql
                        }]

            except Exception as e:
                st.error(f"❌ Failed to generate or run query: {e}")


# ------------------------------------------------------------------------------
# STEP 7: Render Active Query Results, SQL Workbench, and Explanations
# ------------------------------------------------------------------------------
if "active_sql" in st.session_state:
    st.markdown("---")
    turn_count = len(st.session_state.get("conversation_history", []))

    # Active Query Status Card
    st.markdown(f"""
    <div class="custom-card" style="border-left: 4px solid #6366F1;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #FFFFFF;">
                💬 Current Analysis: <span style="color: #60A5FA;">"{st.session_state.get('active_question', '')}"</span>
            </div>
            <div style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.35); color: #A5B4FC; padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: 600;">
                🧠 Memory: {turn_count} prior turn{'s' if turn_count > 1 else ''}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Generated SQL Query Block
    st.subheader("⚡ Generated SQL Query")
    st.code(st.session_state["active_sql"], language="sql")

    # Interactive SQL Workbench: Allows users to inspect, modify, and re-run SQL queries directly
    with st.expander("✏️ Open Interactive SQL Workbench (Edit & Re-run Query)"):
        edited_sql = st.text_area(
            "Modify SQL Query:",
            value=st.session_state.get("edited_sql_input", st.session_state["active_sql"]),
            height=120,
            key="edited_sql_input"
        )
        if st.button("⚡ Execute Modified SQL", type="primary"):
            if edited_sql.strip():
                try:
                    new_df = st.session_state["db_manager"].execute_query(edited_sql)
                    st.session_state["active_sql"] = edited_sql
                    st.session_state["active_df"] = new_df

                    # Clear old chart and insights so the newly modified SQL gets fresh visualizations and insights
                    st.session_state.pop("active_chart_config", None)
                    st.session_state.pop("active_insights", None)
                    st.session_state["show_chart"] = None

                    st.toast("Modified query executed successfully!", icon="🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"Query execution failed: {e}")
            else:
                st.warning("Please enter a valid SQL query.")

    # Tabular Query Results Viewer
    st.subheader("📊 Query Results")
    active_df = st.session_state.get("active_df")

    if active_df is not None:
        col_res_meta, col_res_dl = st.columns([3, 1])
        with col_res_meta:
            st.caption(f"Showing **{len(active_df):,} rows** • **{len(active_df.columns)} columns** returned by SQLite engine.")
        with col_res_dl:
            csv_data = active_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Query Result (CSV)",
                data=csv_data,
                file_name="query_results.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.dataframe(active_df, use_container_width=True, hide_index=True)

        # Plain-English SQL Explanation Breakdown
        st.subheader("💡 Plain-English Query Explanation")
        with st.container():
            st.markdown(st.session_state.get("active_explanation", ""))


    # --------------------------------------------------------------------------
    # STEP 8: Intelligent Plotly Visualization Studio
    # --------------------------------------------------------------------------
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
            st.subheader("📊 AI Generated Visualization Studio")

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
                st.session_state["active_figure"] = figure

                if figure is not None:
                    # Render Plotly Chart inside container
                    st.plotly_chart(figure, use_container_width=True)

                    # Executive Conclusion Banner
                    if "conclusion" in chart_config and chart_config["conclusion"]:
                        clean_conclusion = chart_config["conclusion"].replace("$", r"\$")
                        st.markdown(f"""
                        <div class="takeaway-banner">
                            <div class="takeaway-title">🎯 Executive Conclusion & Key Finding</div>
                            <div class="takeaway-text">{clean_conclusion}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # AI Reasoning Pill
                    if "reasoning" in chart_config:
                        st.caption(f"💡 **AI Reasoning:** {chart_config['reasoning']}")

                    # Hide Button
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
    # STEP 9: Executive Business Insights & Growth Actions (AI Pro)
    # --------------------------------------------------------------------------
    # Formulates high-level strategic insights, performance metrics, and growth recommendations
    # based on statistical context, SQL query logic, and user question intent.
    if active_df is not None and not active_df.empty:
        st.markdown("---")
        st.subheader("💡 Executive Business Insights & Growth Actions (AI Pro)")

        # Check if insights are already generated in session state
        if "active_insights" not in st.session_state or st.session_state["active_insights"] is None:
            # On-demand button trigger avoids automatic API token usage until the user requests insights
            if st.button("💡 Generate AI-Powered Business Insights (AI Pro)", type="primary", use_container_width=True):
                with st.spinner("🤖 AI Pro is analyzing trends and formulating key takeaways..."):
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
            # Display generated markdown insights inside a styled container
            with st.container():
                st.markdown(st.session_state["active_insights"])

            # Button to refresh/regenerate insights if desired
            if st.button("🔄 Refresh Business Insights", key="refresh_insights_btn"):
                st.session_state.pop("active_insights", None)
                st.rerun()


    # --------------------------------------------------------------------------
    # STEP 10: Executive PowerPoint Presentation Export Hub (.pptx)
    # --------------------------------------------------------------------------
    # Generate a boardroom-ready, executive 16:9 widescreen PowerPoint presentation.
    if active_df is not None and not active_df.empty:
        st.markdown("---")
        st.subheader("💼 Boardroom PowerPoint Presentation Hub")

        st.markdown("""
        <div class="custom-card" style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.85) 100%); border: 1px solid rgba(99, 102, 241, 0.3);">
            <div style="font-size: 1.15rem; font-weight: 700; color: #FFFFFF; margin-bottom: 6px;">
                📑 Executive 16:9 Widescreen Presentation Deck (.pptx)
            </div>
            <div style="font-size: 0.9rem; color: #94A3B8; margin-bottom: 16px; line-height: 1.5;">
                Generates a polished, boardroom-ready slide deck containing executive summaries, SQL lineage, tabular metrics, visual chart figures, and strategic growth recommendations.
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 8px;">
                <span class="hero-tag">📺 16:9 Widescreen Master</span>
                <span class="hero-tag">🔒 View-Only Protected</span>
                <span class="hero-tag">📊 Native Table & Visual Cards</span>
                <span class="hero-tag">⚡ Ready to Present</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Gather current analysis artifacts
        current_question = st.session_state.get("active_question", "Data Analysis briefing")
        current_sql = st.session_state.get("active_sql", "")
        current_explanation = st.session_state.get("active_explanation", "")
        current_chart_config = st.session_state.get("active_chart_config")
        current_fig = st.session_state.get("active_figure")
        current_insights = st.session_state.get("active_insights", "")
        dataset_names = list(st.session_state.get("datasets", {}).keys())

        # Compile presentation in memory (View-Only Protected .pptx)
        try:
            pptx_bytes = create_powerpoint_deck(
                user_question=current_question,
                df=active_df,
                generated_sql=current_sql,
                sql_explanation=current_explanation,
                chart_figure=current_fig,
                chart_config=current_chart_config,
                business_insights=current_insights,
                dataset_names=dataset_names,
                view_only_mode=True
            )

            col_btn, _ = st.columns([2, 3])
            with col_btn:
                st.download_button(
                    label="📥 Download Executive Presentation (.pptx)",
                    data=pptx_bytes,
                    file_name="Executive_Data_Briefing.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    type="primary",
                    use_container_width=True
                )

            st.caption("🔒 **Confidentiality Protected**: This presentation opens in **View-Only Mode** by default to prevent unintended changes.")

        except Exception:
            st.error("Sorry! Could not generate presentation deck. Please try again.")