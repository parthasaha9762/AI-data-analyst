import streamlit as st
import pandas as pd

from schema_metadata_generator import generate_table_schema, schema_to_Json, generate_multiple_schemas

from releationship_detector import detect_table_releationship

st.title("AI Data Analyst")


#Upload your multiple CSV files
uploaded_files = st.file_uploader(
    "Upload your CSV files", type=["csv"],
    accept_multiple_files=True
)
#Initialize session sets for all loaded tables
if "datasets" not in st.session_state:
    st.session_state["datasets"] = {}


#Display the uploaded csv files
if uploaded_files:
    st.write("Uploaded files...")
    for file in uploaded_files:
        #Read the CSV files into pandas dataframe
        file.seek(0) # Resets the cursor to the beginning of the file buffer
        df = pd.read_csv(file)
    
        #Create the table names for the uploaaded CSV files
        table_name = file.name.rsplit(".", 1)[0]

        # Store the DataFrame in session state using table_name as the key
        st.session_state["datasets"][table_name] = df

        # Display the File Name and Table Name in Streamlit
        st.write(f"✅ **File:** `{file.name}` ➔ **Table Name:** `{table_name}`")

        # Here comes the Datapreprocessing / Data Cleaning part
        # Calculate and display missing value summary
        missing_values = df.isnull().sum()
        
        with st.expander("Show missing values"):           
            #It will show no missing values if the sum of missing values is 0
            st.write(missing_values if missing_values.sum() > 0
            else "No missing values found! 🎉" )

        # Calculate and display duplicate records
        num_duplicates = df.duplicated().sum()
        with st.expander("Show duplicate records"):
            if num_duplicates > 0:
                st.write(f"❌ Found **{num_duplicates}** duplicate records!")
                st.dataframe(df[df.duplicated()])

                 # 1. Reassign df to save the cleaned copy without duplicates
                df = df.drop_duplicates()
                st.session_state["datasets"][table_name] = df 
                st.success("Duplicate records have been cleared!")
                
            else:
                st.write("No duplicate records found! 🎉")

        with st.expander("Show statistics"):
            st.write(df.describe())

        #Show no of rows and columns of each CSV files
        st.write(f"No: of rows: {len(df)}  \nNo: of columns: {len(df.columns)}")

        #Show first 10 rows of each CSV file
        with st.expander("Show sample rows of the table"):
            sample_dataframe = df.head(10).copy()
            sample_dataframe.index = range(1, len(sample_dataframe) + 1)
            st.dataframe(sample_dataframe)

            #Showing neat and clean datatypes for the uploaded CSV files
            with st.expander("Show data types"):
                clean_dtypes = pd.Series(  #pd.Series is a type of 1D array which stores the datatypes
                    [
                        "int" if "int" in str(dt) else
                        "float" if "float" in str(dt) else
                        "boolean" if "bool" in str(dt) else str(dt)
                        for dt in df.dtypes
                    ],
                    index = df.columns
                )
                st.write(clean_dtypes)

    # Display all the schemas at once in the page
    # Here we will generate the schema metadata for the uploaded CSV files
    schema_table_dictionary = generate_multiple_schemas(st.session_state["datasets"])
    
    # Converting the schema metadata to JSON format
    schema_JSON = schema_to_Json(schema_table_dictionary,4)
    with st.expander("Show all the metadata schemas in JSON format"):
        st.json(schema_JSON)   


    # Display the table relationships
    table_relationships = detect_table_releationship(st.session_state["datasets"])        

    with st.expander("Show detected table relationships"):
        if table_relationships:
            # Convert list of relationship dicts into a clean DataFrame for structured tabular display
            display_data = []
            for relation in table_relationships:
                badge = "🟢 HIGH" if relation["confidence_level"] == "HIGH" else "🟡 MEDIUM"
                display_data.append({
                    "Confidence": badge,
                    "Score": f"{relation['confidence_score']}%",
                    "Source (Foreign Key)": f"{relation['source_table']}.{relation['source_column']}",
                    "Target (Primary Key)": f"{relation['target_table']}.{relation['target_column']}",
                    "Relationship Type": relation["relationship_type"],
                    "Value Overlap": f"{relation['scoring_breakdown']['value_overlap_percentage']}%"
                })
            
            rel_df = pd.DataFrame(display_data)
            st.dataframe(rel_df, use_container_width=True, hide_index=True)
        else:
            st.write("No table relationships detected ❌")

            



# Form allowing submission via Analyze button or pressing Enter
with st.form("query_form"):
    # Ask your queries
    question = st.text_input("Enter your question here", placeholder = "Ask a question about your data in your natural language")

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


    # Analyze your data
    analyze_submitted = st.form_submit_button("Analyze")

if analyze_submitted:
    if question.strip():
        st.write("Analyzing your data...")
        st.write("Your question:", question)
    else:
        st.warning("Please enter a question before analyzing.")