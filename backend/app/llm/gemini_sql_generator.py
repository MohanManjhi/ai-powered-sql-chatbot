import google.generativeai as genai
import os
from dotenv import load_dotenv
from app.schema_inspector import get_db_schema

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_sql_from_nl(nl_query: str) -> str:
    # Get dynamic DB schema as a dictionary {table: [columns]}
    schema = get_db_schema()

    # Build a clear schema prompt listing tables and columns
    schema_prompt = "\n".join(
        [f"Table `{table}` has columns: {', '.join(columns)}" for table, columns in schema.items()]
    )

    # Construct the prompt with clear instructions
    prompt = f"""
You are an expert SQL generator. Given the database schema and a natural language question,
generate a safe, correct SQL SELECT query that follows these rules:
- Only use SELECT statements. Never use DELETE, UPDATE, INSERT, DROP, ALTER, or any other statement.
- Use only the tables and columns present in the schema below.
- Do NOT invent or guess any table or column names.
- Avoid using SELECT *; always explicitly specify columns.
- Write the query in standard SQL syntax.

Schema:
{schema_prompt}

Question: {nl_query}

SQL:
"""

    try:
        # Instantiate Gemini model
        model = genai.GenerativeModel("models/gemini-2.5-pro")

        # Generate SQL query from prompt
        response = model.generate_content(prompt)

        # Return stripped text result
        return response.text.strip()

    except Exception as e:
        # Return a clear error message for debugging/logging
        return f"ERROR: {str(e)}"
