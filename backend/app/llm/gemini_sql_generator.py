import google.generativeai as genai
import os
from dotenv import load_dotenv
from app.schema_inspector import get_db_schema

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_sql_from_nl(nl_query):
    schema = get_db_schema()
    schema_prompt = "\n".join(
        [f"Table `{table}`: {', '.join(columns)}" for table, columns in schema.items()]
    )

    prompt = f"""
You are a SQL expert. Given the database schema and a natural language question,
generate a safe, correct SQL SELECT query. Only use SELECT statements. Never use DELETE, UPDATE, etc.

Schema:
{schema_prompt}

Question: {nl_query}

SQL:
"""

    try:
        model = genai.GenerativeModel("models/gemini-2.5-pro")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"
