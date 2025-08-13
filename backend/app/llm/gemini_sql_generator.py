import google.generativeai as genai
import os
import asyncio
from dotenv import load_dotenv
from app.schema_inspector import get_db_schema
from app.utils.cache_handler import cache_handler
from config import Config
import time

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_sql_from_nl(nl_query: str) -> str:
    # Check cache first for performance
    cache_key = f"sql_generation:{nl_query.lower().strip()}"
    cached_result = cache_handler.get(cache_key)
    if cached_result:
        print(f"🚀 Cache hit for SQL generation: {nl_query[:50]}...")
        return cached_result
    
    # Get dynamic DB schema as a dictionary {table: [columns]}
    schema = get_db_schema()

    # Build a clear schema prompt listing tables and columns
    schema_prompt = "\n".join(
        [f"Table `{table}` has columns: {', '.join(columns)}" for table, columns in schema.items()]
    )

    # Construct the prompt with clear instructions for faster generation
    prompt = f"""
You are an expert SQL generator. Given this database schema and user question, generate a safe SQL SELECT query.

Database Schema:
{schema_prompt}

User Question: {nl_query}

Instructions:
- Generate ONLY a SELECT statement (no INSERT, UPDATE, DELETE, DROP, etc.)
- Use exact table and column names from the schema above
- Avoid SELECT * - specify needed columns
- Make the query safe and efficient
- If the question is unclear, ask for clarification

SQL Query:"""

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
        generation_time = time.time() - start_time
        
        print(f"⚡ SQL generated in {generation_time:.2f}s: {nl_query[:50]}...")
        
        # Cache the result for future use
        cache_handler.set(cache_key, sql_result)
        
        return sql_result

    except Exception as e:
        error_msg = f"ERROR: {str(e)}"
        print(f"❌ SQL generation failed: {error_msg}")
        return error_msg

async def generate_sql_from_nl_async(nl_query: str) -> str:
    """Async version for better performance in concurrent scenarios"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_sql_from_nl, nl_query)
