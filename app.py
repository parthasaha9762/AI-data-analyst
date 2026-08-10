import streamlit as st
import pandas as pd

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
        df.dropna()
        df.fillna(0)

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
                df.drop_duplicates()
                
            else:
                st.write("No duplicate records found! 🎉")

        with st.expander("Show statistics"):
            st.write(df.describe())

        #Show no of rows and columns of each CSV files
        st.write(f"No: of rows: {len(df)}  \nNo: of columns: {len(df.columns)}")

        # #Show columns of each CSV file
        # with st.expander("Show columns"):
        #     st.write(", ".join(df.columns))

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