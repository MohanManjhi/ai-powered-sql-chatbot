from flask import Blueprint, jsonify, request
from .db import get_schema
from .sql_executor import execute_safe_sql
from app.llm.gemini_sql_generator import generate_sql_from_nl
from app.utils.llm_handler import convert_result_to_natural_language, generate_summary
from app.utils.cache_handler import cache_handler
from app.utils.analytics_handler import analytics_handler
from config import Config
import re
import time

main = Blueprint('main', __name__)

def is_greeting_or_general(question):
    """Check if the question is a greeting or very short general help message.

    This intentionally avoids matching partial phrases inside longer analytical
    questions to prevent misclassification.
    """
    greetings = {
        'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
        'help', 'start', 'begin', 'welcome', 'how are you', 'what can you do'
    }

    question_lower = question.lower().strip()

    # If the question clearly expresses data intent, do not treat as greeting
    data_intent_keywords = [
        'select', 'show', 'display', 'list', 'get', 'count', 'how many', 'total',
        'find', 'search', 'where', 'average', 'sum', 'calculate', 'min', 'max',
        'group by', 'order by', 'join', 'table', 'column', 'chart', 'graph', 'plot', 'compare'
    ]
    if any(keyword in question_lower for keyword in data_intent_keywords):
        return False

    # Only treat as greeting/help if the whole message exactly matches a greeting
    # or is extremely short (<= 2 words) and equals one of the known prompts.
    if question_lower in greetings:
        return True

    # For very short messages, be more strict
    words = question_lower.split()
    if len(words) <= 2 and question_lower in greetings:
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
    
    if 'how are you' in question_lower:
        response = {
            "success": True,
            "answer": "I'm doing great, thanks for asking! I'm your AI SQL assistant.",
            "summary": f"I help you explore {schema_analysis['database_type']} using natural language—ask me to show, count, filter data, and I can visualize and export it.",
            "type": "greeting",
            "suggestions": schema_analysis["suggestions"],
            "capabilities": {
                "description": "You can do:",
                "features": schema_analysis["features"]
            }
        }
    elif any(word in question_lower for word in ['hello', 'hi', 'hey', 'good']):
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
    try:
        from flask import request
        origin = request.headers.get('Origin', '')
        # Reflect only allowed origins; Flask-CORS already handles most cases
        response.headers.add('Vary', 'Origin')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    except Exception:
        pass
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

    # Check if it's a greeting or general question that lacks clear data intent
    if is_greeting_or_general(question):
        return handle_greeting_or_general(question)

    # Quick direct checks for existence questions (tables/columns)
    ql = question.lower()
    try:
        schema = get_schema()
    except Exception:
        schema = {}
    # Check patterns like: "there is no categories?", "is there categories?"
    import re as _re
    m_tbl = _re.search(r"(?:is there|there is no|is there any)\s+([a-zA-Z_][a-zA-Z0-9_]*)", ql)
    m_col = _re.search(r"(?:is there|there is no|is there any)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:column|field)\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)", ql)
    if m_col:
        col = m_col.group(1)
        tbl = m_col.group(2)
        exists = tbl in schema and col in (schema.get(tbl) or [])
        answer = f"Yes, column '{col}' exists in table '{tbl}'." if exists else f"No, column '{col}' does not exist in table '{tbl}'."
        return jsonify({
            "success": True,
            "answer": answer,
            "summary": answer,
            "data": []
        })
    if m_tbl:
        tbl = m_tbl.group(1)
        exists = tbl in schema
        answer = f"Yes, table '{tbl}' exists." if exists else f"No, table '{tbl}' does not exist."
        return jsonify({
            "success": True,
            "answer": answer,
            "summary": answer,
            "data": []
        })

    # Step 1a: Handle direct existence questions (tables/columns)
    existence = detect_existence_question(question)
    if existence is not None:
        total_time = time.time() - start_time
        return jsonify({
            "success": True,
            "answer": existence["answer"],
            "summary": existence.get("summary"),
            "data": [],
            "performance": {"total_time": round(total_time, 2), "cached": "none"}
        })

    # Step 1b: Convert NL to SQL (with caching)
    print(f"🧠 Generating SQL for: {question[:50]}...")
    sql = generate_sql_from_nl(question)
    # Fallback: handle generic requests gracefully
    if sql.startswith("ERROR"):
        # If the user asked for all data without specifying a table, pick a reasonable default table
        question_lower = question.lower()
        generic_all_data = any(phrase in question_lower for phrase in [
            'show me all data', 'show all data', 'all data', 'show everything'
        ])
        try:
            schema = get_schema()
            tables = list(schema.keys())
        except Exception:
            tables = []

        if tables and generic_all_data:
            sql = f"SELECT * FROM {tables[0]} LIMIT 50"
        else:
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
    # If LLM returned a non-SELECT but user intent seems generic all-data, try safe fallback
    if not sql.strip().upper().startswith("SELECT"):
        try:
            schema = get_schema()
            tables = list(schema.keys())
        except Exception:
            tables = []
        if tables:
            sql = f"SELECT * FROM {tables[0]} LIMIT 50"

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

    # Detect chart intent
    chart_request = detect_chart_intent(question)

    # ✅ Return clean output
    return jsonify({
        "success": True,
        "answer": answer,
        "summary": summary,
        "data": rows,
        "chart_request": chart_request,
        "performance": {
            "total_time": round(total_time, 2),
            "cached": "partial" if summary else "none"
        }
    })

@main.route("/api/analytics/chart", methods=["POST"])
def generate_chart():
    """Generate chart data based on user query and chart type preference"""
    try:
        data = request.get_json()
        question = data.get("question", "")
        chart_type = data.get("chart_type", "auto")
        sql = data.get("sql", "")
        rows = data.get("rows")  # Optional: allow passing rows directly (no SQL exposure)

        # If rows not provided, execute SQL (for server-side generation use cases)
        if rows is None:
            if not sql:
                return jsonify({"success": False, "error": "Either rows or SQL query is required"}), 400
            query_result = execute_safe_sql(sql)
            if not query_result.get("success", False):
                return jsonify({"success": False, "error": "Failed to execute query"}), 500
            rows = query_result.get("rows", [])
        if not rows:
            return jsonify({"success": False, "error": "No data found for chart"}), 400
        
        # Auto-detect chart type if not specified
        if chart_type == "auto":
            chart_type = analytics_handler.detect_optimal_chart_type(rows, question)
        
        # Generate chart data based on type
        chart_data = analytics_handler.generate_chart_data(rows, chart_type, question)
        
        return jsonify({
            "success": True,
            "chart_data": chart_data,
            "chart_type": chart_type,
            "data_count": len(rows),
            "suggestions": analytics_handler.get_chart_suggestions(chart_type, rows)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@main.route("/api/analytics/export", methods=["POST"])
def export_data():
    """Export data in various formats (CSV, Excel, JSON)"""
    try:
        data = request.get_json()
        sql = data.get("sql", "")
        export_format = data.get("format", "csv")
        filename = data.get("filename", "data_export")
        rows = data.get("rows")  # Optional: allow passing rows directly (no SQL exposure)

        # If rows not provided, execute SQL (for server-side generation use cases)
        if rows is None:
            if not sql:
                return jsonify({"success": False, "error": "Either rows or SQL query is required"}), 400
            query_result = execute_safe_sql(sql)
            if not query_result.get("success", False):
                return jsonify({"success": False, "error": "Failed to execute query"}), 500
            rows = query_result.get("rows", [])
        if not rows:
            return jsonify({"success": False, "error": "No data to export"}), 400
        
        # Generate export file
        export_result = analytics_handler.generate_export_file(rows, export_format, filename)
        
        return jsonify({
            "success": True,
            "download_url": export_result["download_url"],
            "filename": export_result["filename"],
            "format": export_format,
            "data_count": len(rows)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@main.route("/api/analytics/suggestions", methods=["GET"])
def get_analytics_suggestions():
    """Get suggestions for analytics and chart types"""
    try:
        schema = get_schema()
        suggestions = analytics_handler.generate_analytics_suggestions(schema)
        
        return jsonify({
            "success": True,
            "suggestions": suggestions,
            "chart_types": analytics_handler.get_available_chart_types()
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def detect_optimal_chart_type(rows, question):
    """Automatically detect the best chart type based on data and question"""
    if not rows:
        return "bar"
    
    # Analyze data structure
    num_columns = len(rows[0]) if rows else 0
    num_rows = len(rows)
    
    # Check for time series data
    question_lower = question.lower()
    if any(word in question_lower for word in ['trend', 'over time', 'daily', 'monthly', 'yearly', 'date']):
        return "line"
    
    # Check for comparison data
    if any(word in question_lower for word in ['compare', 'vs', 'versus', 'difference', 'ranking']):
        if num_rows <= 10:
            return "bar"
        else:
            return "horizontal_bar"
    
    # Check for distribution data
    if any(word in question_lower for word in ['distribution', 'frequency', 'count', 'how many']):
        if num_rows <= 20:
            return "bar"
        else:
            return "histogram"
    
    # Check for relationship data
    if any(word in question_lower for word in ['correlation', 'relationship', 'scatter']):
        if num_columns >= 2:
            return "scatter"
    
    # Check for composition data
    if any(word in question_lower for word in ['percentage', 'proportion', 'share', 'breakdown']):
        if num_rows <= 8:
            return "pie"
        else:
            return "doughnut"
    
    # Default based on data characteristics
    if num_rows <= 15:
        return "bar"
    elif num_columns >= 3:
        return "scatter"
    else:
        return "line"

def generate_chart_data(rows, chart_type, question):
    """Generate chart data based on chart type and data"""
    if not rows:
        return {}
    
    # Extract column names
    columns = list(rows[0].keys()) if rows else []
    
    if chart_type == "bar":
        return generate_bar_chart_data(rows, columns, question)
    elif chart_type == "line":
        return generate_line_chart_data(rows, columns, question)
    elif chart_type == "pie":
        return generate_pie_chart_data(rows, columns, question)
    elif chart_type == "scatter":
        return generate_scatter_chart_data(rows, columns, question)
    elif chart_type == "area":
        return generate_area_chart_data(rows, columns, question)
    elif chart_type == "doughnut":
        return generate_doughnut_chart_data(rows, columns, question)
    elif chart_type == "horizontal_bar":
        return generate_horizontal_bar_chart_data(rows, columns, question)
    elif chart_type == "histogram":
        # Fallback: treat histogram as a bar chart over first column grouping
        return generate_bar_chart_data(rows, columns, question)
    else:
        return generate_bar_chart_data(rows, columns, question)  # Default fallback

def generate_bar_chart_data(rows, columns, question):
    """Generate bar chart data"""
    if len(columns) < 2:
        return {"error": "Need at least 2 columns for bar chart"}
    
    # Use first column as labels, second as values
    labels = [str(row[columns[0]]) for row in rows[:20]]  # Limit to 20 bars
    values = [float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else 1 for row in rows[:20]]
    
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": columns[1],
                "data": values,
                "backgroundColor": generate_colors(len(values)),
                "borderColor": generate_colors(len(values)),
                "borderWidth": 1
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": f"Bar Chart: {question[:50]}..."
                }
            }
        }
    }

def generate_line_chart_data(rows, columns, question):
    """Generate line chart data"""
    if len(columns) < 2:
        return {"error": "Need at least 2 columns for line chart"}
    
    # Sort by first column if it looks like dates
    sorted_rows = sorted(rows, key=lambda x: str(x[columns[0]]))
    
    labels = [str(row[columns[0]]) for row in sorted_rows[:50]]  # Limit to 50 points
    values = [float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else 1 for row in sorted_rows[:50]]
    
    return {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": columns[1],
                "data": values,
                "borderColor": "rgb(75, 192, 192)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
                "tension": 0.1
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": f"Line Chart: {question[:50]}..."
                }
            }
        }
    }

def generate_pie_chart_data(rows, columns, question):
    """Generate pie chart data"""
    if len(columns) < 2:
        return {"error": "Need at least 2 columns for pie chart"}
    
    # Group by first column and sum second column
    grouped_data = {}
    for row in rows:
        key = str(row[columns[0]])
        value = float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else 1
        grouped_data[key] = grouped_data.get(key, 0) + value
    
    # Limit to top 8 categories
    sorted_items = sorted(grouped_data.items(), key=lambda x: x[1], reverse=True)[:8]
    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]
    
    return {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": values,
                "backgroundColor": generate_colors(len(values)),
                "borderColor": "#fff",
                "borderWidth": 2
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": f"Pie Chart: {question[:50]}..."
                }
            }
        }
    }

def generate_scatter_chart_data(rows, columns, question):
    """Generate scatter chart data"""
    if len(columns) < 3:
        return {"error": "Need at least 3 columns for scatter chart"}
    
    # Use first two columns as x,y coordinates, third as size/color if available
    x_values = [float(row[columns[0]]) if isinstance(row[columns[0]], (int, float)) else i for i, row in enumerate(rows[:100])]
    y_values = [float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else i for i, row in enumerate(rows[:100])]
    
    return {
        "type": "scatter",
        "data": {
            "datasets": [{
                "label": f"{columns[0]} vs {columns[1]}",
                "data": [{"x": x, "y": y} for x, y in zip(x_values, y_values)],
                "backgroundColor": "rgba(75, 192, 192, 0.6)",
                "borderColor": "rgb(75, 192, 192)"
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": f"Scatter Plot: {question[:50]}..."
                }
            },
            "scales": {
                "x": {"title": {"display": True, "text": columns[0]}},
                "y": {"title": {"display": True, "text": columns[1]}}
            }
        }
    }

def generate_area_chart_data(rows, columns, question):
    """Generate area chart data"""
    if len(columns) < 2:
        return {"error": "Need at least 2 columns for area chart"}
    
    sorted_rows = sorted(rows, key=lambda x: str(x[columns[0]]))
    labels = [str(row[columns[0]]) for row in sorted_rows[:50]]
    values = [float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else 1 for row in sorted_rows[:50]]
    
    return {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": columns[1],
                "data": values,
                "backgroundColor": "rgba(75, 192, 192, 0.3)",
                "borderColor": "rgb(75, 192, 192)",
                "fill": True,
                "tension": 0.1
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": f"Area Chart: {question[:50]}..."
                }
            }
        }
    }

def generate_doughnut_chart_data(rows, columns, question):
    """Generate doughnut chart data"""
    pie_data = generate_pie_chart_data(rows, columns, question)
    if "error" in pie_data:
        return pie_data
    
    pie_data["type"] = "doughnut"
    return pie_data

def generate_horizontal_bar_chart_data(rows, columns, question):
    """Generate horizontal bar chart data"""
    # Build like bar chart but with indexAxis set to 'y' for horizontal bars
    if len(columns) < 2:
        return {"error": "Need at least 2 columns for bar chart"}

    labels = [str(row[columns[0]]) for row in rows[:20]]
    values = [
        float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else 1
        for row in rows[:20]
    ]

    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": columns[1],
                "data": values,
                "backgroundColor": generate_colors(len(values)),
                "borderColor": generate_colors(len(values)),
                "borderWidth": 1
            }]
        },
        "options": {
            "indexAxis": "y",
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": f"Horizontal Bar: {question[:50]}..."}
            }
        }
    }

def generate_colors(count):
    """Generate a list of colors for charts"""
    colors = [
        "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
        "#FF9F40", "#FF6384", "#C9CBCF", "#4BC0C0", "#FF6384"
    ]
    
    if count <= len(colors):
        return colors[:count]
    
    # Generate additional colors if needed
    import random
    additional_colors = []
    for _ in range(count - len(colors)):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        additional_colors.append(f"rgb({r}, {g}, {b})")
    
    return colors + additional_colors

def get_chart_suggestions(chart_type, rows):
    """Get suggestions for the current chart"""
    suggestions = []
    
    if chart_type == "bar":
        suggestions.extend([
            "Try asking for trends over time to see line charts",
            "Ask for percentages to see pie charts",
            "Request comparisons between categories"
        ])
    elif chart_type == "line":
        suggestions.extend([
            "Ask for category breakdowns to see bar charts",
            "Request distribution analysis for histograms",
            "Ask for correlations between variables"
        ])
    elif chart_type == "pie":
        suggestions.extend([
            "Ask for trends over time to see line charts",
            "Request detailed breakdowns with bar charts",
            "Ask for comparisons between specific categories"
        ])
    
    suggestions.extend([
        "Download this data for further analysis",
        "Try different chart types for better visualization",
        "Ask for specific insights about the data"
    ])
    
    return suggestions

def generate_export_file(rows, export_format, filename):
    """Generate export file in specified format"""
    import tempfile
    import os
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_filename = safe_filename.replace(' ', '_')
    
    if export_format == "csv":
        return generate_csv_export(rows, safe_filename, timestamp)
    elif export_format == "excel":
        return generate_excel_export(rows, safe_filename, timestamp)
    elif export_format == "json":
        return generate_json_export(rows, safe_filename, timestamp)
    else:
        return generate_csv_export(rows, safe_filename, timestamp)  # Default to CSV

def generate_csv_export(rows, filename, timestamp):
    """Generate CSV export"""
    import csv
    import os
    
    if not rows:
        return {"error": "No data to export"}
    
    # Ensure downloads directory exists
    downloads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'downloads'))
    os.makedirs(downloads_dir, exist_ok=True)

    final_filename = f"{filename}_{timestamp}.csv"
    final_path = os.path.join(downloads_dir, final_filename)

    # Write CSV data to final path
    with open(final_path, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return {
        "download_url": f"/downloads/{final_filename}",
        "filename": final_filename,
        "file_path": final_path
    }

def generate_excel_export(rows, filename, timestamp):
    """Generate Excel export"""
    try:
        import pandas as pd
        import os

        downloads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'downloads'))
        os.makedirs(downloads_dir, exist_ok=True)

        final_filename = f"{filename}_{timestamp}.xlsx"
        final_path = os.path.join(downloads_dir, final_filename)

        df = pd.DataFrame(rows)
        with pd.ExcelWriter(final_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Data', index=False)

        return {
            "download_url": f"/downloads/{final_filename}",
            "filename": final_filename,
            "file_path": final_path
        }
    except ImportError:
        # Fallback to CSV if pandas/openpyxl not available
        return generate_csv_export(rows, filename, timestamp)

def generate_json_export(rows, filename, timestamp):
    """Generate JSON export"""
    import json
    import os

    downloads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'downloads'))
    os.makedirs(downloads_dir, exist_ok=True)

    final_filename = f"{filename}_{timestamp}.json"
    final_path = os.path.join(downloads_dir, final_filename)

    with open(final_path, mode='w') as f:
        json.dump(rows, f, indent=2, default=str)

    return {
        "download_url": f"/downloads/{final_filename}",
        "filename": final_filename,
        "file_path": final_path
    }

def generate_analytics_suggestions(schema):
    """Generate analytics suggestions based on database schema"""
    suggestions = []
    
    for table_name, columns in schema.items():
        # Sales/Revenue analysis
        if any(word in table_name.lower() for word in ['sale', 'order', 'transaction', 'revenue']):
            suggestions.extend([
                f"Show sales trends over time from {table_name}",
                f"Compare sales by category in {table_name}",
                f"Calculate total revenue from {table_name}",
                f"Show top performing products in {table_name}"
            ])
        
        # User/Customer analysis
        if any(word in table_name.lower() for word in ['user', 'customer', 'client']):
            suggestions.extend([
                f"Show user growth over time from {table_name}",
                f"Analyze customer demographics in {table_name}",
                f"Show customer retention rates from {table_name}",
                f"Compare user activity patterns in {table_name}"
            ])
        
        # Product/Inventory analysis
        if any(word in table_name.lower() for word in ['product', 'inventory', 'item']):
            suggestions.extend([
                f"Show inventory levels in {table_name}",
                f"Analyze product performance in {table_name}",
                f"Show stock turnover rates in {table_name}",
                f"Compare product categories in {table_name}"
            ])
    
    return suggestions[:10]  # Limit to 10 suggestions

def get_available_chart_types():
    """Get list of available chart types with descriptions"""
    return [
        {
            "type": "bar",
            "name": "Bar Chart",
            "description": "Best for comparing categories or showing rankings",
            "best_for": ["Comparisons", "Rankings", "Categorical data"]
        },
        {
            "type": "line",
            "name": "Line Chart",
            "description": "Best for showing trends over time",
            "best_for": ["Time series", "Trends", "Continuous data"]
        },
        {
            "type": "pie",
            "name": "Pie Chart",
            "description": "Best for showing parts of a whole",
            "best_for": ["Percentages", "Proportions", "Composition"]
        },
        {
            "type": "scatter",
            "name": "Scatter Plot",
            "description": "Best for showing relationships between variables",
            "best_for": ["Correlations", "Relationships", "Two variables"]
        },
        {
            "type": "area",
            "name": "Area Chart",
            "description": "Best for showing cumulative data over time",
            "best_for": ["Cumulative data", "Time series", "Volume"]
        },
        {
            "type": "doughnut",
            "name": "Doughnut Chart",
            "description": "Alternative to pie charts with better readability",
            "best_for": ["Percentages", "Proportions", "Modern look"]
        },
        {
            "type": "horizontal_bar",
            "name": "Horizontal Bar Chart",
            "description": "Better for long category names",
            "best_for": ["Long labels", "Many categories", "Readability"]
        }
    ]

def detect_chart_intent(question: str) -> dict:
    """Parse the question to detect if the user requests a chart and which type.

    Returns a dict like {requested: bool, type: 'bar'|'line'|..., compare: bool}
    """
    q = (question or '').lower()
    requested = any(word in q for word in ['chart', 'graph', 'plot', 'visualize', 'visualise', 'visualization'])

    type_map = {
        'bar': 'bar',
        'bar chart': 'bar',
        'column': 'bar',
        'line': 'line',
        'line chart': 'line',
        'pie': 'pie',
        'pie chart': 'pie',
        'doughnut': 'doughnut',
        'donut': 'doughnut',
        'scatter': 'scatter',
        'scatter plot': 'scatter',
        'area': 'area',
        'horizontal bar': 'horizontal_bar',
        'stacked bar': 'bar'
    }
    detected_type = None
    for key, value in type_map.items():
        if key in q:
            detected_type = value
            break

    compare = any(word in q for word in ['compare', 'vs', 'versus', 'difference'])

    return {
        'requested': requested,
        'type': detected_type or 'auto',
        'compare': compare
    }

def detect_existence_question(question: str):
    """Detect if the user is asking whether a table/column exists and answer directly."""
    q = (question or '').lower().strip()
    # Patterns like: "is there", "do we have", "there is no", "does <table> exist"
    patterns = [
        'is there', 'do we have', 'there is no', 'does', 'exist', 'available', 'present'
    ]
    if not any(p in q for p in patterns):
        return None

    try:
        schema = get_schema()
        tables = list(schema.keys())
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", q)
        # Try to match a table or column name from the question
        target_table = next((w for w in words if w in tables), None)
        if target_table:
            return {
                "answer": f"Yes, the table '{target_table}' exists with columns: {', '.join(schema[target_table])}.",
                "summary": None
            }
        # Try columns
        all_columns = {col for cols in schema.values() for col in cols}
        target_col = next((w for w in words if w in all_columns), None)
        if target_col:
            owners = [t for t, cols in schema.items() if target_col in cols]
            return {
                "answer": f"Yes, the column '{target_col}' exists in table(s): {', '.join(owners)}.",
                "summary": None
            }
        # If user implies non-existence
        if 'there is no' in q or 'does not exist' in q or "doesn't exist" in q:
            return {
                "answer": "I could not confirm the item in your question in the connected database schema.",
                "summary": None
            }
        # Otherwise say not found
        return {
            "answer": "I couldn't find a matching table or column in the schema. Please specify the name more clearly.",
            "summary": None
        }
    except Exception:
        return {
            "answer": "I couldn't access the schema to verify. Please try again.",
            "summary": None
        }

@main.route("/downloads/<filename>", methods=["GET"])
def download_file(filename):
    """Download exported files"""
    try:
        import os
        from flask import send_file
        
        # Security: Only allow downloads from downloads directory
        downloads_dir = os.path.join(os.path.dirname(__file__), '..', 'downloads')
        file_path = os.path.join(downloads_dir, filename)
        
        # Ensure the file exists and is in the downloads directory
        if not os.path.exists(file_path) or not file_path.startswith(downloads_dir):
            return jsonify({"success": False, "error": "File not found"}), 404
        
        # Determine content type based on file extension
        content_type = 'application/octet-stream'
        if filename.endswith('.csv'):
            content_type = 'text/csv'
        elif filename.endswith('.xlsx'):
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.endswith('.json'):
            content_type = 'application/json'
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype=content_type
        )
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
