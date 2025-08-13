from flask import Blueprint, jsonify, request
from .db import get_schema
from .sql_executor import execute_safe_sql
from app.llm.gemini_sql_generator import generate_sql_from_nl
from app.utils.llm_handler import convert_result_to_natural_language, generate_summary
from app.utils.cache_handler import cache_handler
from config import Config
import re
import time

main = Blueprint('main', __name__)

def is_greeting_or_general(question):
    """Check if the question is a greeting or general question"""
    greetings = [
        'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
        'how are you', 'what can you do', 'help', 'guide', 'explain', 'tell me',
        'what is this', 'how does this work', 'start', 'begin', 'welcome'
    ]
    
    question_lower = question.lower().strip()
    
    # Check for exact matches
    if question_lower in greetings:
        return True
    
    # Check for partial matches
    for greeting in greetings:
        if greeting in question_lower:
            return True
    
    # Check for questions about capabilities
    if any(word in question_lower for word in ['can you', 'what do you', 'how do you', 'what is']):
        return True
    
    return False

def handle_greeting_or_general(question):
    """Handle greetings and general questions dynamically based on schema"""
    question_lower = question.lower().strip()
    
    # Get dynamic schema to generate relevant suggestions
    try:
        schema = get_schema()
        schema_analysis = analyze_schema_for_greetings(schema)
    except Exception as e:
        # Fallback if schema analysis fails
        schema_analysis = {
            "database_type": "your database",
            "main_entities": ["data", "records"],
            "suggestions": ["Show me all records", "Count total entries", "Find specific data"],
            "features": ["Data exploration", "Record analysis", "Information retrieval"]
        }
    
    if any(word in question_lower for word in ['hello', 'hi', 'hey', 'good']):
        response = {
            "success": True,
            "answer": f"Hello! 👋 Welcome to the AI SQL Chatbot!",
            "summary": f"I'm here to help you explore {schema_analysis['database_type']} using natural language questions.",
            "type": "greeting",
            "suggestions": schema_analysis["suggestions"],
            "capabilities": {
                "description": f"This is a {schema_analysis['database_type']} where you can explore:",
                "features": schema_analysis["features"]
            }
        }
    elif any(word in question_lower for word in ['help', 'guide', 'explain', 'what can you do']):
        response = {
            "success": True,
            "answer": "I'm your AI database assistant! 🚀",
            "summary": f"I can help you explore {schema_analysis['database_type']} by converting your questions into SQL queries.",
            "type": "help",
            "suggestions": schema_analysis["suggestions"],
            "capabilities": {
                "description": "I can help you with:",
                "features": [
                    "🔍 Data exploration and analysis",
                    "📈 Performance insights",
                    "👥 Entity relationship analysis", 
                    "📦 Data categorization and filtering",
                    "💰 Financial and statistical analysis"
                ]
            }
        }
    else:
        response = {
            "success": True,
            "answer": f"I'm here to help you explore {schema_analysis['database_type']}! 📊",
            "summary": f"Ask me questions about {', '.join(schema_analysis['main_entities'])} and more.",
            "type": "general",
            "suggestions": schema_analysis["suggestions"],
            "capabilities": {
                "description": f"Your database contains:",
                "features": schema_analysis["features"]
            }
        }
    
    return jsonify(response)

def analyze_schema_for_greetings(schema):
    """Dynamically analyze schema to generate relevant greetings and suggestions"""
    tables = list(schema.keys())
    
    # Analyze table names to determine database type
    if any(word in ' '.join(tables).lower() for word in ['user', 'customer', 'client']):
        if any(word in ' '.join(tables).lower() for word in ['order', 'sale', 'transaction', 'payment']):
            database_type = "e-commerce or sales database"
        else:
            database_type = "user management database"
    elif any(word in ' '.join(tables).lower() for word in ['product', 'inventory', 'item']):
        database_type = "inventory or product database"
    elif any(word in ' '.join(tables).lower() for word in ['employee', 'staff', 'worker']):
        database_type = "HR or employee database"
    elif any(word in ' '.join(tables).lower() for word in ['student', 'course', 'grade']):
        database_type = "educational database"
    elif any(word in ' '.join(tables).lower() for word in ['patient', 'medical', 'health']):
        database_type = "healthcare database"
    else:
        database_type = "business database"
    
    # Generate relevant suggestions based on actual tables
    suggestions = []
    for table in tables[:5]:  # Limit to 5 suggestions
        if 'user' in table.lower() or 'customer' in table.lower():
            suggestions.append(f"Show me all {table}")
        elif 'order' in table.lower() or 'sale' in table.lower():
            suggestions.append(f"How many {table} do we have?")
        elif 'product' in table.lower() or 'item' in table.lower():
            suggestions.append(f"List all {table}")
        elif 'date' in table.lower() or 'time' in table.lower():
            suggestions.append(f"Show {table} trends")
        else:
            suggestions.append(f"Count total {table}")
    
    # Generate features based on actual schema
    features = []
    for table in tables:
        if 'user' in table.lower() or 'customer' in table.lower():
            features.append(f"👥 {table.title()} management")
        elif 'order' in table.lower() or 'sale' in table.lower():
            features.append(f"🛒 {table.title()} tracking")
        elif 'product' in table.lower() or 'item' in table.lower():
            features.append(f"📦 {table.title()} catalog")
        elif 'payment' in table.lower() or 'transaction' in table.lower():
            features.append(f"💰 {table.title()} processing")
        elif 'review' in table.lower() or 'rating' in table.lower():
            features.append(f"⭐ {table.title()} system")
        else:
            features.append(f"📊 {table.title()} data")
    
    return {
        "database_type": database_type,
        "main_entities": tables[:3],  # Show first 3 main entities
        "suggestions": suggestions,
        "features": features[:6]  # Limit to 6 features
    }

def extract_table_names(sql):
    """Extract table names from SQL for logging purposes (security-focused)"""
    try:
        # Simple regex to find table names after FROM and JOIN
        import re
        from_pattern = r'FROM\s+(\w+)'
        join_pattern = r'JOIN\s+(\w+)'
        
        tables = set()
        tables.update(re.findall(from_pattern, sql, re.IGNORECASE))
        tables.update(re.findall(join_pattern, sql, re.IGNORECASE))
        
        return list(tables)[:3]  # Limit to 3 tables for security
    except:
        return ["unknown"]

def generate_query_suggestions(question):
    """Generate helpful suggestions based on the user's question"""
    question_lower = question.lower()
    
    # Get schema for context-aware suggestions
    try:
        schema = get_schema()
        tables = list(schema.keys())
    except:
        tables = ["users", "orders", "products", "customers"]
    
    suggestions = []
    
    # Analyze question type and provide relevant suggestions
    if any(word in question_lower for word in ['show', 'display', 'list', 'get']):
        suggestions.extend([
            f"Show me all {tables[0] if tables else 'records'}",
            f"List the first 10 {tables[0] if tables else 'items'}",
            f"Display {tables[0] if tables else 'data'} with specific criteria"
        ])
    
    if any(word in question_lower for word in ['count', 'how many', 'total']):
        suggestions.extend([
            f"How many {tables[0] if tables else 'records'} do we have?",
            f"Count total {tables[0] if tables else 'entries'}",
            f"What's the total number of {tables[0] if tables else 'items'}?"
        ])
    
    if any(word in question_lower for word in ['find', 'search', 'where']):
        suggestions.extend([
            f"Find {tables[0] if tables else 'records'} that match criteria",
            f"Search for specific {tables[0] if tables else 'data'}",
            f"Show {tables[0] if tables else 'items'} with conditions"
        ])
    
    if any(word in question_lower for word in ['average', 'sum', 'calculate']):
        suggestions.extend([
            f"Calculate average of a field",
            f"Sum up values for {tables[0] if tables else 'data'}",
            f"Show statistical information"
        ])
    
    # Add general helpful suggestions
    suggestions.extend([
        "Try using simpler language",
        "Be more specific about what you want to see",
        "Use words like 'show', 'count', 'find', or 'calculate'"
    ])
    
    return suggestions[:5]  # Limit to 5 suggestions

@main.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@main.before_app_request
def before_request_logging():
    print("📥 Incoming request to:", request.path)

@main.route("/api/schema", methods=["GET"])
def get_db_schema():
    try:
        schema = get_schema()
        return jsonify({"success": True, "schema": schema})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@main.route("/api/cache/stats", methods=["GET"])
def get_cache_stats():
    """Get cache statistics for monitoring performance"""
    try:
        stats = cache_handler.get_stats()
        return jsonify({
            "success": True, 
            "cache_stats": stats,
            "config": {
                "cache_timeout": Config.CACHE_TIMEOUT,
                "llm_timeout": Config.LLM_TIMEOUT,
                "gemini_model": Config.GEMINI_MODEL
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@main.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    """Clear all cache for troubleshooting"""
    try:
        cache_handler.clear()
        return jsonify({"success": True, "message": "Cache cleared successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@main.route("/api/query", methods=["POST"])
def run_sql_query():
    print("🚀 /api/query route hit")
    data = request.get_json()
    sql = data.get("sql", "")
    print("Received data:", data)

    result = execute_safe_sql(sql)
    return jsonify(result)

@main.route("/api/nl-to-sql", methods=["POST"])
def nl_to_sql():
    start_time = time.time()
    data = request.get_json()
    question = data.get("question", "")

    # Check if it's a greeting or general question
    if is_greeting_or_general(question):
        return handle_greeting_or_general(question)

    # Step 1: Convert NL to SQL (with caching)
    print(f"🧠 Generating SQL for: {question[:50]}...")
    sql = generate_sql_from_nl(question)
    if sql.startswith("ERROR"):
        # Provide helpful suggestions instead of just error
        suggestions = generate_query_suggestions(question)
        return jsonify({
            "success": False,
            "error": "I couldn't understand your question clearly. Let me help you with some suggestions:",
            "suggestions": suggestions,
            "original_question": question,
            "type": "query_help"
        }), 400

    # Log query type for security monitoring (without exposing actual SQL)
    if Config.LOG_QUERY_TYPE:
        query_type = "SELECT" if sql.strip().upper().startswith("SELECT") else "OTHER"
        print(f"🔒 Query type: {query_type}")
        
        if Config.LOG_TABLE_NAMES:
            tables = extract_table_names(sql)
            print(f"🔒 Tables accessed: {tables}")
    
    # Step 2: Execute SQL safely
    query_result = execute_safe_sql(sql)
    if not query_result.get("success", False):
        # Provide helpful suggestions for SQL execution errors
        suggestions = generate_query_suggestions(question)
        return jsonify({
            "success": False,
            "error": "I found some issues with the query. Here are some suggestions:",
            "suggestions": suggestions,
            "original_question": question,
            "type": "query_help"
        }), 500

    # Step 3: Postprocess result
    rows = query_result.get("rows", [])

    # Answer: Natural text from result
    answer = convert_result_to_natural_language(question, rows)

    # Summary: Delightful natural overview (with caching)
    summary = generate_summary(question, rows)

    total_time = time.time() - start_time
    print(f"⚡ Total processing time: {total_time:.2f}s")

    # ✅ Return clean output
    return jsonify({
        "success": True,
        "answer": answer,
        "summary": summary,
        "data": rows,
        "performance": {
            "total_time": round(total_time, 2),
            "cached": "partial" if summary else "none"
        }
    })
