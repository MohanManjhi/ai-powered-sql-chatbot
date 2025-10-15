import google.generativeai as genai
import os
import asyncio
from dotenv import load_dotenv
from app.schema_inspector import get_all_db_schemas
from app.utils.cache_handler import cache_handler
from config import Config
import time
from app.db import engines
import json
import logging

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_sql_from_nl(nl_query: str) -> dict:
    """
    Generate SQL for all databases and return a dict:
    {db_name: sql_query}
    """
    # Check cache first for performance
    cache_key = f"sql_generation:{nl_query.lower().strip()}"
    cached_result = cache_handler.get(cache_key)
    if cached_result:
        print(f"🚀 Cache hit for SQL generation: {nl_query[:50]}...")
        return cached_result
    
    # Get schemas for all databases
    all_schemas = get_all_db_schemas(engines)
    schema_prompt = "\n\n".join([
        f"Database `{db}`:\n" + "\n".join([
            f"  Table `{table}` has columns: {', '.join(columns)}" for table, columns in schema.items()
        ]) for db, schema in all_schemas.items()
    ])

    # Construct the prompt with clear instructions for faster generation
    prompt = f"""
You are an expert SQL generator. Given these database schemas and user question, generate a safe SQL SELECT query for each relevant database.

Database Schemas:
{schema_prompt}

User Question: {nl_query}

Instructions:
- For each database, generate ONLY a SELECT statement (no INSERT, UPDATE, DELETE, DROP, etc.)
- Use exact table and column names from the schema above
- Avoid SELECT * - specify needed columns
- Make the query safe and efficient
- If the question is unclear, ask for clarification
- Output as a JSON object: {{'db1': 'SQL for db1', 'db2': 'SQL for db2', ...}}

SQL Queries (JSON):"""

    try:
        start_time = time.time()
        
        # Use faster model for better performance
        model = genai.GenerativeModel(Config.GEMINI_MODEL)
        
        # Set generation config for speed
        generation_config = genai.types.GenerationConfig(
            temperature=Config.TEMPERATURE,
            max_output_tokens=Config.MAX_TOKENS,
            top_p=0.8,
            top_k=40
        )
        
        # Generate SQL query with timeout
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        sql_result = response.text.strip()
        # Remove triple backticks and language tag if present
        if sql_result.startswith('```'):
            # Remove leading/trailing backticks and language tag
            sql_result = sql_result.lstrip('`').lstrip('json').strip()
            # Remove trailing backticks
            if sql_result.endswith('```'):
                sql_result = sql_result[:-3].strip()
        # Also handle case where Gemini returns with newlines after backticks
        if sql_result.startswith('json'):
            sql_result = sql_result[4:].strip()
        if not sql_result:
            logging.error(f"Gemini output was empty for question: {nl_query}")
            return {"error": "Gemini output was empty.", "raw_output": sql_result}
        try:
            sql_dict = json.loads(sql_result)
            generation_time = time.time() - start_time
            print(f"⚡ SQL generated in {generation_time:.2f}s: {nl_query[:50]}...")
            cache_handler.set(cache_key, sql_dict)
            return sql_dict
        except json.JSONDecodeError as jde:
            logging.error(f"Gemini output JSON decode error: {jde}\nRaw output: {sql_result}")
            return {"error": f"Gemini output was invalid JSON: {jde}", "raw_output": sql_result}
    except Exception as e:
        error_msg = f"ERROR: {str(e)}"
        print(f"❌ SQL generation failed: {error_msg}")
        return {"error": error_msg}

async def generate_sql_from_nl_async(nl_query: str) -> dict:
    """Async version for better performance in concurrent scenarios"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_sql_from_nl, nl_query)
