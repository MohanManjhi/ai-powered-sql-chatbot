import google.generativeai as genai
import os
from dotenv import load_dotenv
from app.utils.cache_handler import cache_handler
from config import Config
import time

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_sql_query(user_query, schema):
    # Prepare prompt including schema + user query
    prompt = f"""
You are an expert SQL generator. Based on this schema:
{schema}

Generate a valid SQL SELECT query for:
{user_query}

Only use tables and columns available in the schema.
"""
    # Call Gemini API with prompt and get SQL
    from ..llm.gemini_sql_generator import generate_sql_from_nl
    sql = generate_sql_from_nl(prompt)
    return sql


def generate_summary(question, rows):
    if not rows:
        return None

    # Check cache first for performance
    cache_key = f"summary:{question.lower().strip()}:{hash(str(rows[:3]))}"
    cached_summary = cache_handler.get(cache_key)
    if cached_summary:
        print(f"🚀 Cache hit for summary generation: {question[:50]}...")
        return cached_summary

    try:
        start_time = time.time()
        
        # Simplified prompt for faster generation
        sample_data = rows[:3]  # Reduced from 5 to 3 for speed
        prompt = f"""
Question: "{question}"
Data: {sample_data}
Write a brief summary in 1-2 lines:"""

        # Use faster model and optimized settings
        model = genai.GenerativeModel(Config.GEMINI_MODEL)
        
        generation_config = genai.types.GenerationConfig(
            temperature=Config.TEMPERATURE,
            max_output_tokens=200,  # Shorter for speed
            top_p=0.8,
            top_k=20
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        summary = response.text.strip()
        generation_time = time.time() - start_time
        
        print(f"⚡ Summary generated in {generation_time:.2f}s: {question[:50]}...")
        
        # Clean up any markdown formatting
        if summary.startswith("```"):
            summary = summary.split("```")[1] if len(summary.split("```")) > 1 else summary
        if summary.startswith("sql"):
            summary = summary[3:].strip()
        
        # Cache the result
        cache_handler.set(cache_key, summary)
        
        return summary
    
    except Exception as e:
        print(f"❌ Summary generation failed: {str(e)}")
        # Return a simple fallback summary
        if len(rows) == 1:
            return f"Found 1 result for your query."
        else:
            return f"Found {len(rows)} results for your query."


def convert_result_to_natural_language(question, rows):
    if not rows:
        return f"No results found for: \"{question}\""

    try:
        # Simple, fast response without LLM call
        if len(rows) == 1:
            return f"Found 1 result for your query: \"{question}\""
        else:
            return f"Found {len(rows)} results for your query: \"{question}\""

    except Exception as e:
        return f"Data fetched successfully, but formatting failed: {str(e)}"


