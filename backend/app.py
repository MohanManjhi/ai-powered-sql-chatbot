# backend/app.py
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from sqlalchemy import create_engine, inspect, text
import os
import google.generativeai as genai
import sqlparse
import pandas as pd
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication

# --- Configuration ---
# Set your database connection string as an environment variable
# For local testing, you can put it directly here, but ENV VARS are recommended for production!
# Example PostgreSQL: 'postgresql+psycopg2://user:password@host:port/database_name'
# Example SQLite: 'sqlite:///./data.db' (creates a file 'data.db' in backend directory)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test_database.db')

# Configure your Gemini API key
# IMPORTANT: Replace 'YOUR_GEMINI_API_KEY_HERE' with your actual API key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyB0l8PIY6qx05E8fZzYjB9r7qbAHNUvmOQ') # Keep your key here if you want to hardcode it, or remove it if you prefer environment variable
if GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE': # This check should be against the placeholder
    logging.warning("GEMINI_API_KEY is not set. Please set it as an environment variable or replace 'YOUR_GEMINI_API_KEY_HERE' in app.py.")

genai.configure(api_key=GEMINI_API_KEY)
# Using gemini-1.5-flash for potentially better performance and context handling
# You can switch to gemini-1.0-pro or gemini-2.0-flash if preferred/available
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Database Engine Initialization ---
engine = create_engine(DATABASE_URL)

# For a quick test with SQLite, let's create a simple DB if it doesn't exist
# This block is for initial setup convenience, remove or guard in production
if 'sqlite' in DATABASE_URL:
    db_file = DATABASE_URL.replace('sqlite:///./', '')
    if not os.path.exists(db_file):
        logging.info(f"Creating a sample SQLite database: {db_file}")
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS products (
                        product_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        category TEXT,
                        price REAL,
                        stock INTEGER
                    );
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS customers (
                        customer_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT,
                        region TEXT
                    );
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id INTEGER PRIMARY KEY,
                        customer_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER,
                        order_date TEXT, -- Store as TEXT for simplicity, can be DATE
                        total_amount REAL,
                        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                        FOREIGN KEY (product_id) REFERENCES products(product_id)
                    );
                """))

                # Insert sample data if tables were just created
                conn.execute(text("""
                    INSERT INTO products (product_id, name, category, price, stock) VALUES
                    (101, 'Laptop', 'Electronics', 1200.00, 50),
                    (102, 'Mouse', 'Electronics', 25.00, 200),
                    (103, 'Keyboard', 'Electronics', 75.00, 150),
                    (104, 'Monitor', 'Electronics', 300.00, 80),
                    (105, 'Desk Chair', 'Furniture', 150.00, 30),
                    (106, 'Coffee Maker', 'Home Goods', 80.00, 100),
                    (107, 'Headphones', 'Electronics', 100.00, 120)
                    ON CONFLICT(product_id) DO NOTHING;
                """))
                conn.execute(text("""
                    INSERT INTO customers (customer_id, name, email, region) VALUES
                    (1, 'Alice Smith', 'alice@example.com', 'North'),
                    (2, 'Bob Johnson', 'bob@example.com', 'South'),
                    (3, 'Charlie Brown', 'charlie@example.com', 'East'),
                    (4, 'Diana Prince', 'diana@example.com', 'West'),
                    (5, 'Eve Adams', 'eve@example.com', 'North'),
                    (6, 'Frank Miller', 'frank@example.com', 'South')
                    ON CONFLICT(customer_id) DO NOTHING;
                """))
                conn.execute(text("""
                    INSERT INTO orders (order_id, customer_id, product_id, quantity, order_date, total_amount) VALUES
                    (1001, 1, 101, 1, '2023-01-20', 1200.00),
                    (1002, 2, 102, 2, '2023-02-25', 50.00),
                    (1003, 3, 103, 1, '2023-03-30', 75.00),
                    (1004, 1, 104, 1, '2023-04-05', 300.00),
                    (1005, 4, 105, 1, '2023-04-10', 150.00),
                    (1006, 2, 106, 1, '2023-05-01', 80.00),
                    (1007, 5, 107, 2, '2023-05-15', 200.00),
                    (1008, 3, 101, 1, '2023-06-01', 1200.00),
                    (1009, 4, 102, 3, '2023-06-10', 75.00),
                    (1010, 6, 103, 1, '2023-07-01', 75.00)
                    ON CONFLICT(order_id) DO NOTHING;
                """))
                conn.commit()
            logging.info("Sample SQLite database created and populated.")
        except Exception as e:
            logging.error(f"Error creating/populating SQLite database: {e}")

# --- Endpoint to get dynamic database schema ---
@app.route('/api/db-schema', methods=['GET'])
def get_db_schema():
    """
    Dynamically fetches the database schema (tables, columns, relationships)
    and formats it into a prompt suitable for the LLM.
    """
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        schema_info = {}

        llm_schema_prompt_parts = []
        llm_schema_prompt_parts.append("Database Schema:")

        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            column_details = []
            for col in columns:
                column_details.append({
                    'name': col['name'],
                    'type': str(col['type']), # Convert SQLAlchemy type to string
                    'nullable': col['nullable'],
                    'primary_key': col['primary_key']
                })

            foreign_keys = inspector.get_foreign_keys(table_name)
            fk_details = []
            for fk in foreign_keys:
                fk_details.append({
                    'constrained_columns': fk['constrained_columns'],
                    'referred_table': fk['referred_table'],
                    'referred_columns': fk['referred_columns']
                })

            schema_info[table_name] = {
                'columns': column_details,
                'foreign_keys': fk_details
            }

            llm_schema_prompt_parts.append(f"- Table: `{table_name}`")
            llm_schema_prompt_parts.append("  Columns: " + ", ".join([f"`{col['name']}` ({col['type']})" for col in details['columns']]))

            if fk_details:
                llm_schema_prompt_parts.append("  Relationships:")
                for fk in fk_details:
                    llm_schema_prompt_parts.append(f"    - `{table_name}`.`{', '.join(fk['constrained_columns'])}` references `{fk['referred_table']}`.`{', '.join(fk['referred_columns'])}`")

        llm_schema_prompt_part = "\n".join(llm_schema_prompt_parts)

        logging.info("Schema fetched successfully.")
        return jsonify({'schema_info': schema_info, 'llm_schema_prompt_part': llm_schema_prompt_part})

    except Exception as e:
        logging.error(f"Error fetching database schema: {e}")
        return jsonify({'error': f'Failed to fetch database schema: {str(e)}'}), 500

# --- Function for robust SQL validation ---
def validate_sql_query(sql_query):
    """
    Parses an SQL query and performs strict security checks.
    Allows only single SELECT statements and disallows DDL/DML.
    """
    try:
        parsed_statements = sqlparse.parse(sql_query)
        if not parsed_statements:
            raise ValueError("No SQL statements found.")

        if len(parsed_statements) > 1:
            raise ValueError("Only one SQL statement per request is allowed for security reasons.")

        stmt = parsed_statements[0]

        # Check if the statement is a SELECT statement
        # We need to find the first non-whitespace, non-comment token
        first_token = None
        for token in stmt.tokens:
            if not token.is_whitespace and not token.is_comment:
                first_token = token
                break

        if not first_token or first_token.value.upper() != 'SELECT':
            raise ValueError(f"Only SELECT statements are allowed. Found: '{first_token.value if first_token else 'N/A'}'")

        # Check for disallowed keywords anywhere in the statement
        disallowed_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE',
            'RENAME', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'UNION ALL', 'UNION',
            '--' # Prevent comments that could hide injections
        ]

        # Convert statement to string and check for keywords (case-insensitive)
        # This is a robust check against various forms of injection
        sql_upper = sql_query.upper()
        for keyword in disallowed_keywords:
            if keyword in sql_upper:
                # Special handling for UNION to allow UNION DISTINCT but not UNION ALL
                if keyword == 'UNION' and 'UNION ALL' in sql_upper:
                    raise ValueError(f"Disallowed SQL keyword '{keyword}' found in query.")
                elif keyword == 'UNION' and 'UNION DISTINCT' not in sql_upper:
                    # If it's just 'UNION' without 'DISTINCT', it's still potentially risky
                    raise ValueError(f"Disallowed SQL keyword '{keyword}' found in query. Only UNION DISTINCT is allowed.")
                elif keyword != 'UNION': # Apply for all other keywords
                    raise ValueError(f"Disallowed SQL keyword '{keyword}' found in query.")

        logging.info(f"SQL query validated successfully: {sql_query}")
        return True # Query is considered safe
    except Exception as e:
        logging.warning(f"SQL Validation Error: {e} for query: {sql_query}")
        raise ValueError(f"SQL Security check failed: {str(e)}")


# --- Endpoint for Chatbot Interaction ---
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handles natural language queries, generates SQL via LLM, validates,
    executes, and returns natural language response with data.
    """
    user_query = request.json.get('query')
    current_db_schema_llm_part = request.json.get('dbSchemaLLMPart')

    if not user_query or not current_db_schema_llm_part:
        return jsonify({'error': 'Missing user query or database schema context.'}), 400

    try:
        # Step 1: LLM to generate SQL
        prompt = f"""
        You are an AI assistant specialized in converting natural language questions into SQL SELECT queries.
        You are connected to a database with the following schema:
        ---
        {current_db_schema_llm_part}
        ---

        User's question: "{user_query}"

        Instructions:
        1. Generate ONLY a valid SQL SELECT query. Do NOT include any explanations, conversational text, or markdown formatting (like ```sql).
        2. Ensure the query strictly uses table and column names from the provided schema.
        3. Prioritize exact matches for column names and table names.
        4. If the user asks for aggregate data (e.g., "total sales", "number of products"), use appropriate SQL aggregate functions (SUM, COUNT, AVG, etc.) and GROUP BY if needed.
        5. If the request cannot be fulfilled with a SELECT query (e.g., it asks to change data, drop tables, or is irrelevant to the database), or if it's ambiguous, respond with the exact phrase: "I cannot fulfill this request. I can only answer questions related to the database."
        6. Consider common natural language phrases for filtering (e.g., "more than", "less than", "between dates").
        7. If a chart is explicitly mentioned (e.g., "show me a chart of...") or implied by an aggregation, try to return two columns suitable for a bar chart (e.g., category and count/sum).
        8. For date comparisons, use standard SQL date formats (e.g., 'YYYY-MM-DD').
        9. Ensure the query is syntactically correct and executable.

        SQL Query:
        """

        logging.info(f"Sending prompt to LLM for query: '{user_query}'")
        try:
            response = model.generate_content(prompt)
            generated_sql = response.text.strip()
            logging.info(f"LLM generated SQL: {generated_sql}")
        except Exception as e:
            logging.error(f"LLM generation failed for query '{user_query}': {e}")
            return jsonify({'bot_response': 'I apologize, I could not generate a SQL query for your request. Please try rephrasing.', 'data': []}), 500

        # Check if LLM explicitly denied the request
        if generated_sql == "I cannot fulfill this request. I can only answer questions related to the database.":
            return jsonify({
                'bot_response': generated_sql,
                'data': [],
                'sql_query_for_debug': generated_sql # For internal logging, not sent to frontend
            })

        # Step 2: Validate the generated SQL for security
        try:
            validate_sql_query(generated_sql)
        except ValueError as e:
            logging.warning(f"Attempted malicious/invalid query detected from LLM: '{generated_sql}' - Error: {e}")
            return jsonify({
                'bot_response': f"Security Alert: Your request implies an unauthorized or unsafe database operation. I can only execute safe SELECT queries. Please rephrase your question. ({e})",
                'data': [],
                'sql_query_for_debug': generated_sql # For internal logging, not sent to frontend
            }), 403 # Forbidden

        # Step 3: Execute the validated SQL query
        data = []
        try:
            with engine.connect() as conn:
                # Using text() for raw SQL execution
                result = conn.execute(text(generated_sql))

                columns = result.keys()
                data = [dict(zip(columns, row)) for row in result.fetchall()]
            logging.info(f"SQL query executed successfully. Records found: {len(data)}")
        except Exception as e:
            logging.error(f"Database execution failed for query '{generated_sql}': {e}")
            return jsonify({
                'bot_response': f"I encountered an error while querying the database. The generated SQL might be incorrect for the schema. Error: {str(e)}",
                'data': [],
                'sql_query_for_debug': generated_sql # For internal logging, not sent to frontend
            }), 500

        # Step 4: Generate Natural Language Response
        bot_response = "Here are the results from your query:\n"
        if not data:
            bot_response = "I couldn't find any data matching your request."
        elif len(data) == 1 and len(columns) == 1:
            # Special case for single aggregate result (e.g., COUNT(*))
            col_name = columns[0]
            # Try to make the name more readable
            display_col_name = col_name.replace('_', ' ').replace('(', '').replace(')', '').strip().lower()
            bot_response = f"The {display_col_name} is: {data[0][col_name]}."
        elif len(data) > 0:
            bot_response += f"Found {len(data)} record(s)."

        return jsonify({
            'bot_response': bot_response,
            'data': data,
            # 'sql_query': generated_sql # IMPORTANT: DO NOT SEND SQL TO FRONTEND FOR SECURITY
        })

    except Exception as e:
        logging.critical(f"Unhandled backend chat error: {e}")
        return jsonify({'error': f'An unexpected internal server error occurred: {str(e)}'}), 500

# --- Endpoint to download data as Excel ---
@app.route('/api/download-excel', methods=['POST'])
def download_excel():
    """
    Receives tabular data from the frontend and converts it into an Excel file for download.
    """
    data_to_export = request.json.get('data')
    file_name = request.json.get('fileName', 'query_results.xlsx')

    if not data_to_export:
        return jsonify({'error': 'No data provided for export.'}), 400

    try:
        df = pd.DataFrame(data_to_export)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Query Results')
        output.seek(0) # Go to the beginning of the BytesIO stream

        logging.info(f"Generated Excel file: {file_name}")
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=file_name
        )
    except Exception as e:
        logging.error(f"Error generating Excel file: {e}")
        return jsonify({'error': f'Failed to generate Excel file: {str(e)}'}), 500

# --- Start the Flask app ---
if __name__ == '__main__':
    # You can set debug=True for development, but set to False in production
    app.run(debug=True, port=5000)