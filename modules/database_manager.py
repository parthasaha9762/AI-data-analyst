import sqlite3
import pandas as pd 


class DatabaseManager:
    def __init__(self, db_name=":memory:"):
        """
        Initialize the SQLite database connection.
        - `:memory:` keeps the database in-memory (super fast, no leftover files).
        - `check_same_thread=False` is REQUIRED for Streamlit because multi-threading 
          is used by Streamlit under the hood.
        """

        self.conn = sqlite3.connect(db_name, check_same_thread=False)

    def load_datasets(self, datasets: dict):
        """
        Converts a dictionary of {table_name: DataFrame} into SQLite tables.
        """

        for table_name, df in datasets.items():
            # df.to_sql automatically infers SQL data types from Pandas data types
            df.to_sql(
                name = table_name,
                con = self.conn,
                if_exists="replace",  # Overwrite table if re-uploaded
                index=False           # Don't store the pandas index as a column    
            )

    def execute_query(self, query: str)-> pd.DataFrame:
        """
        Executes a SQL query and returns the results directly as a Pandas DataFrame.
        """
        # Automatically rename duplicate columns if present (e.g. JOIN SELECT *)

        df = pd.read_sql_query(query, self.conn)

        if len(df.columns) != len(set(df.columns)):
            new_columns = []
            counts = {}
            
            for col in df.columns:
                if col in counts:
                    counts[col] += 1
                    new_columns.append(f"{col}_{counts[col]}")
                else:
                    counts[col] = 0
                    new_columns.append(col)

            df.columns = new_columns

        return df
        

    def get_tables(self)-> list:
        """
        Helper method to list all table names currently loaded in SQLite.
        Useful for UI verification.
        """

        query = "SELECT name FROM sqlite_master WHERE type='table';" 
        tables_df = self.execute_query(query)

        return tables_df["name"].tolist()

    def close(self):
        """
        Close Database connection.
        """
        self.conn.close()