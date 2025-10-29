from flask import Blueprint, jsonify, request
import time
import re
import json
from app.utils.json_encoder import MongoJSONEncoder
from sqlalchemy import text

# --- Database & LLM Imports ---
# SQL Components
from .db import get_schema # Assuming this is for SQL schema retrieval
from .db import execute_sql_on_all_databases # Executes SQL across multiple configured DBs
from .sql_executor import execute_safe_sql # Used by /api/query (single SQL execution)

# MongoDB Components
from app.db_mongo import get_mongo_collections_schema # Gets MongoDB collection schema
from app.db_mongo import execute_mongo_query # Executes MongoDB query
from app.db_mongo import is_mongo_available, last_mongo_uri_tried
import os
from urllib.parse import urlparse

# LLM & Utility Components
from app.llm.gemini_sql_generator import generate_sql_from_nl
from app.llm.gemini_mongo_generator import generate_mongo_query_from_nl 
from app.utils.llm_handler import convert_result_to_natural_language, generate_summary
# NOTE: Assuming these are implemented elsewhere, used for analysis/caching
# from app.utils.cache_handler import cache_handler 
# from app.utils.analytics_handler import analytics_handler
# from config import Config 

main = Blueprint('main', __name__)

# --- Helper Functions (Keeping identical to previous response) ---

def is_greeting_or_general(question):
    """Checks if the question is a greeting or a general help request."""
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
    if question_lower in greetings:
        return True

    # For very short messages, be more strict
    words = question_lower.split()
    if len(words) <= 2 and question_lower in greetings:
        return True

    return False

def get_schema_by_type(db_type):
    """
    Dynamically get schema/collections based on database type.
    
    IMPORTANT: Sanitizes MongoDB schema by removing large binary fields (like 'data') 
    to prevent LLM context overflow or safety issues.
    """
    if db_type == "mongo":
        # Returns dict of collection names to a sample structure
        raw_schema = get_mongo_collections_schema() 
        # Sanitize schema by removing fields that typically hold large binary data
        sanitized_schema = {}
        for collection_name, fields in raw_schema.items():
            sanitized_fields = {}
            for field_name, field_type in fields.items():
                # Explicitly remove the 'data' field often used for storing binary content
                if field_name.lower() != 'data':
                    sanitized_fields[field_name] = field_type
            sanitized_schema[collection_name] = sanitized_fields
        return sanitized_schema
    else:
        # Returns dict of table names to columns
        return get_schema()

def detect_chart_intent(question):
    """Simple intent detection for chart/graph requests."""
    question_lower = question.lower()
    if any(word in question_lower for word in ['chart', 'graph', 'plot', 'visualize', 'trend', 'pie', 'bar']):
        return True
    return False

def analyze_schema_for_greetings(schema, db_type):
    """Dynamically analyze schema to generate relevant greetings and suggestions"""
    entities = list(schema.keys()) # Tables for SQL, Collections for Mongo
    
    if db_type == "mongo":
        database_type = "MongoDB document store"
    else: # SQL
        database_type = "SQL business database"
        
    # --- Logic for determining main entities and suggestions (simplified) ---
    suggestions = []
    if entities:
        suggestions.append(f"Show me all {entities[0]}")
        if len(entities) > 1:
            suggestions.append(f"Count total {entities[1]}")
    
    # Generate generic suggestions if few entities or none
    if not suggestions:
        suggestions.extend(["Show me all records", "Count total entries", "Find specific data"])

    features = [f"📊 {entity.title()} data" for entity in entities[:3]]
    features.extend(["🔍 Data exploration", "📈 Performance insights"])
    
    return {
        "database_type": database_type,
        "main_entities": entities[:3],
        "suggestions": suggestions,
        "features": features[:6]
    }

def handle_greeting_or_general(question, db_type):
    """Handle greetings and general questions dynamically based on schema and db_type"""
    question_lower = question.lower().strip()
    
    try:
        # Use the dynamic schema retrieval
        schema = get_schema_by_type(db_type)
        schema_analysis = analyze_schema_for_greetings(schema, db_type)
    except Exception as e:
        print(f"Error during schema analysis for greeting: {e}")
        # Default analysis if schema retrieval fails
        schema_analysis = {
            "database_type": "your database",
            "main_entities": ["data", "records"],
            "suggestions": ["Show me all records", "Count total entries", "Find specific data"],
            "features": ["Data exploration", "Record analysis"]
        }
    
    if 'how are you' in question_lower:
        answer = "I'm doing great, thanks for asking! I'm your AI database assistant."
        summary = f"I help you explore {schema_analysis['database_type']} using natural language."
    elif any(word in question_lower for word in ['hello', 'hi', 'hey', 'good']):
        answer = f"Hello! 👋 Welcome to the AI Database Chatbot!"
        summary = f"I'm here to help you explore {schema_analysis['database_type']} using natural language questions."
    elif any(word in question_lower for word in ['help', 'guide', 'explain', 'what can you do']):
        answer = "I'm your AI database assistant! 🚀"
        summary = f"I can help you explore {schema_analysis['database_type']} by converting your questions into queries."
    else:
        answer = f"I'm here to help you explore {schema_analysis['database_type']}! 📊"
        summary = f"Ask me questions about {', '.join(schema_analysis['main_entities'])} and more."

    response = {
        "success": True,
        "answer": answer,
        "summary": summary,
        "type": "greeting" if 'how are you' not in question_lower else "general",
        "suggestions": schema_analysis["suggestions"],
        "capabilities": {
            "description": f"You can explore:",
            "features": schema_analysis["features"]
        }
    }
    return jsonify(response)


def detect_existence_question(question, db_type):
    """Checks for table/collection or column/field existence."""
    ql = question.lower()
    try:
        schema = get_schema_by_type(db_type)
    except Exception:
        return None

    _re = re
    if db_type == "sql":
        entity_word = "table"
        field_word = "column"
    else: # mongo
        entity_word = "collection"
        field_word = "field"

    # Check for column/field existence (simplified regex pattern)
    m_col = _re.search(fr"([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:{field_word})\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)", ql)
    if m_col:
        col = m_col.group(1).strip()
        tbl = m_col.group(2).strip()
        
        # Check if entity exists AND field is in its schema definition
        exists = tbl in schema and col in (schema.get(tbl) or [])
        answer = f"Yes, {field_word} '{col}' exists in {entity_word} '{tbl}'." if exists else f"No, {field_word} '{col}' does not exist in {entity_word} '{tbl}'."
        return {"answer": answer, "summary": answer}

    # Check for table/collection existence (simplified regex pattern)
    m_tbl = _re.search(fr"(?:is there|there is no|is there any)\s+([a-zA-Z_][a-zA-Z0-9_]*)", ql)
    if m_tbl:
        tbl = m_tbl.group(1).strip()
        exists = tbl in schema
        answer = f"Yes, {entity_word} '{tbl}' exists." if exists else f"No, {entity_word} '{tbl}' does not exist."
        return {"answer": answer, "summary": answer}
    
    return None

def generate_query_suggestions(question, db_type):
    """Generate helpful suggestions based on the user's question and db_type"""
    question_lower = question.lower()
    
    try:
        schema = get_schema_by_type(db_type)
        entities = list(schema.keys())
    except:
        entities = ["users", "orders", "products"]
    
    suggestions = []
    
    # Add 3 relevant suggestions based on entities and question context
    if entities:
        if any(word in question_lower for word in ['count', 'total']):
             suggestions.append(f"Count total {entities[0]}")
        else:
             suggestions.append(f"List the first 10 {entities[0]}")
    
    suggestions.extend([
        "Try using simpler language and be more specific.",
        "Use words like 'show', 'count', 'find', or 'calculate'.",
        "Check your question against the known tables/collections."
    ])
    
    return suggestions[:5]

# --- Route Definitions ---

@main.route("/api/schema", methods=["GET"])
def get_db_schema():
    """Returns the schema for the default database type (SQL) and MongoDB."""
    try:
        sql_schema = get_schema() 
    except Exception as e:
        sql_schema = {"error": f"SQL schema retrieval failed: {str(e)}"}
    
    # Use the sanitized schema 
    try:
        mongo_schema = get_schema_by_type("mongo") 
    except Exception as e:
        mongo_schema = {"error": f"Mongo schema retrieval failed: {str(e)}"}
        
    return jsonify({
        "success": True, 
        "sql_schema": sql_schema,
        "mongo_schema": mongo_schema
    })


@main.route('/api/health-details', methods=['GET'])
def health_details():
    """Return detailed health status for configured SQL engines and MongoDB.

    - sql: for each configured DB (from app.db.engines) return reachable and error
    - mongo: reachable boolean and last tried URI
    """
    # Import here to avoid circular imports at module load time
    import importlib
    db_module = importlib.import_module('app.db')

    sql_status = {}
    try:
        for name, engine in getattr(db_module, 'engines', {}).items():
            try:
                with engine.connect() as conn:
                    # Run a safe lightweight check
                    conn.execute(text('SELECT 1'))
                    sql_status[name] = {'ok': True}
            except Exception as e:
                sql_status[name] = {'ok': False, 'error': str(e)}
    except Exception as e:
        sql_status = {'error': f'Could not evaluate SQL engines: {str(e)}'}

    # Mongo status
    try:
        mongo_ok = is_mongo_available()
        mongo_uri = last_mongo_uri_tried()
        mongo_status = {'ok': bool(mongo_ok), 'uri_tried': mongo_uri}
    except Exception as e:
        mongo_status = {'ok': False, 'error': str(e)}

    return jsonify({'success': True, 'sql': sql_status, 'mongo': mongo_status})

@main.route("/api/query", methods=["POST"])
def run_query():
    """Executes pre-generated query for SQL or MongoDB."""
    print("🚀 /api/query route hit")
    data = request.get_json()
    db_type = data.get("db_type", "sql").lower()
    
    start_time = time.time()

    if db_type == "mongo":
        # MongoDB logic
        collection = data.get("collection")
        filter_query = data.get("filter", {})
        projection = data.get("projection")
        limit = data.get("limit", 50)
        # allow caller to specify db_name; otherwise extract default from MONGODB_URI
        db_name = data.get("db_name")
        if not db_name:
            mongo_uri = os.environ.get("MONGODB_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
            try:
                parsed = urlparse(mongo_uri)
                db_name = parsed.path.strip('/') or None
            except Exception:
                db_name = None
        try:
            # if db_name is provided, call with db_name first, otherwise let execute_mongo_query handle it if it supports None
            if db_name:
                result = execute_mongo_query(db_name, collection, filter_query, projection, limit)
            else:
                result = execute_mongo_query(collection, filter_query, projection, limit)
            total_time = time.time() - start_time
            return jsonify({
                "success": True, 
                "rows": result, 
                "query_type": "mongo",
                "performance": {"total_time": round(total_time, 2)}
            })
        except Exception as e:
            return jsonify({"success": False, "error": f"MongoDB execution error: {str(e)}"}), 500
    else:
        # SQL logic
        sql = data.get("sql", "")
        try:
            result = execute_safe_sql(sql)
            total_time = time.time() - start_time
            return jsonify({
                "success": True, 
                "rows": result, 
                "query_type": "sql",
                "performance": {"total_time": round(total_time, 2)}
            })
        except Exception as e:
            return jsonify({"success": False, "error": f"SQL execution error: {str(e)}"}), 500

@main.route("/api/nl-to-mongodb", methods=["POST"])
def nl_to_mongodb():
    """Handle natural language queries for MongoDB"""
    start_time = time.time()
    question = ""
    mongo_error = None
    
    try:
        data = request.get_json()
        question = data.get("question", "")
        
        # Check for greeting
        if is_greeting_or_general(question):
            return handle_greeting_or_general(question, "mongo")

        # Check if it's a schema question
        existence = detect_existence_question(question, "mongo")
        if existence is not None:
            total_time = time.time() - start_time
            return jsonify({
                "success": True,
                "answer": existence["answer"],
                "summary": existence.get("summary"),
                "data": [],
                "db_type_used": "mongo",
                "performance": {"total_time": round(total_time, 2), "cached": "none"}
            })

        # Generate and execute MongoDB query
        mongo_query_dict = generate_mongo_query_from_nl(question)
        print(f"🔎 Attempting Mongo. Gemini MongoDB dict: {mongo_query_dict}")

        if isinstance(mongo_query_dict, dict) and "error" in mongo_query_dict:
            mongo_error = mongo_query_dict["error"]
            print(f"❌ MongoDB Generation failed: {mongo_error}")
            suggestions = generate_query_suggestions(question, "mongo")
            return jsonify({
                "success": False,
                "error": f"Failed to generate MongoDB query: {mongo_error}",
                "suggestions": suggestions,
                "type": "query_failure"
            }), 500

        # Execute MongoDB query
        if isinstance(mongo_query_dict, dict) and "collection" in mongo_query_dict:
            collection = mongo_query_dict.get("collection")
            filter_query = mongo_query_dict.get("filter", {})
            projection = mongo_query_dict.get("projection")
            limit = mongo_query_dict.get("limit", 50)
            db_name = mongo_query_dict.get("db_name")
            db_name_used = None
            rows = []
            
            try:
                if db_name:
                    rows = execute_mongo_query(db_name, collection, filter_query, projection, limit)
                    db_name_used = db_name
                    # If LLM suggested DB contained no rows, probe other DBs for the data
                    if not rows:
                        from app.db_mongo import find_db_for_collection, execute_mongo_query_across_dbs
                        resolved_db = find_db_for_collection(collection, filter_query)
                        if resolved_db and resolved_db != db_name:
                            rows = execute_mongo_query(resolved_db, collection, filter_query, projection, limit)
                            db_name_used = resolved_db
                        else:
                            # As a last resort scan all DBs and take the first non-empty result
                            aggregated = execute_mongo_query_across_dbs(collection=collection, filter_query=filter_query, projection=projection, limit=limit)
                            for dbn, res in aggregated.items():
                                if dbn != db_name and isinstance(res, list) and res:
                                    rows = res
                                    db_name_used = dbn
                                    break
                else:
                    # Try to find the best DB for this collection+filter
                    from app.db_mongo import find_db_for_collection, execute_mongo_query_across_dbs
                    resolved_db = find_db_for_collection(collection, filter_query)
                    if resolved_db:
                        rows = execute_mongo_query(resolved_db, collection, filter_query, projection, limit)
                        db_name_used = resolved_db
                    else:
                        # No single DB identified, search across DBs and take first non-empty
                        aggregated = execute_mongo_query_across_dbs(collection=collection, filter_query=filter_query, projection=projection, limit=limit)
                        for dbn, res in aggregated.items():
                            if isinstance(res, list) and res:
                                rows = res
                                db_name_used = dbn
                                break

                if rows:
                    print("✅ MongoDB execution successful and data found.")
                    answer = convert_result_to_natural_language(question, rows)
                    summary = generate_summary(question, rows)
                    total_time = time.time() - start_time
                    chart_request = detect_chart_intent(question)
                    
                    return jsonify({
                        "success": True,
                        "answer": answer,
                        "summary": summary,
                        "data": rows,
                        "db_type_used": "mongo",
                        "db_name_used": db_name_used,
                        "chart_request": chart_request,
                        "performance": {"total_time": round(total_time, 2), "cached": "none"}
                    })

            except Exception as e:
                mongo_error = str(e)
                print(f"❌ MongoDB Execution failed: {mongo_error}")
                suggestions = generate_query_suggestions(question, "mongo")
            error_msg = f"MongoDB execution failed: {mongo_error}"
            # Add collection info to error message if collection doesn't exist
            if mongo_error and "Collection does not exist" in str(mongo_error):
                try:
                    from app.db_mongo import get_mongo_collections_schema
                    schema = get_mongo_collections_schema()
                    if db_name and db_name in schema:
                        collections = list(schema[db_name].keys())
                        error_msg += f"\nAvailable collections in {db_name}: {', '.join(collections)}"
                except Exception as schema_error:
                    print(f"Error getting collection schema: {schema_error}")
            
            # Construct and return error response
            return jsonify({
                "success": False,
                "error": error_msg,
                "suggestions": suggestions,
                "type": "execution_failure"
            }), 500

        # If we get here, the query dict didn't have a collection or was malformed
        return jsonify({
            "success": False,
            "error": "Could not understand the MongoDB query request",
            "suggestions": generate_query_suggestions(question, "mongo"),
            "type": "parsing_failure"
        }), 500

    except Exception as e:
        print(f"CRITICAL UNCAUGHT ERROR in nl_to_mongodb: {e}")
        suggestions = generate_query_suggestions(question, "mongo")
        return jsonify({
            "success": False,
            "error": f"An unexpected server error occurred: {str(e)}",
            "suggestions": suggestions,
            "type": "server_error"
        }), 500

@main.route("/api/nl-to-sql", methods=["POST"])
def nl_to_sql():
    """The core route with SQL-first fallback to MongoDB logic."""
    start_time = time.time()
    question = ""
    sql_error = None
    mongo_error = None
    
    try:
        data = request.get_json()
        question = data.get("question", "")
        
        # --- 0. Initial Checks (db_type agnostic) ---
        
        # If it's a greeting, handle it using the default database type provided in the request
        db_type_hint = data.get("db_type", "sql").lower()
        if is_greeting_or_general(question):
            return handle_greeting_or_general(question, db_type_hint)

        # --- 1. Attempt SQL Query Generation and Execution (Primary) ---
        
        merged_rows = []
        
        # 1a. Check for existence question (defaulting to SQL logic first)
        existence = detect_existence_question(question, "sql")
        if existence is not None:
             # If it was an existence question for SQL, return immediately
            total_time = time.time() - start_time
            return jsonify({
                "success": True,
                "answer": existence["answer"],
                "summary": existence.get("summary"),
                "data": [],
                "db_type_used": "sql",
                "performance": {"total_time": round(total_time, 2), "cached": "none"}
            })


        try:
            # Generate SQL
            sql_dict = generate_sql_from_nl(question)
            print(f"🔎 Attempting SQL. Gemini SQL dict: {sql_dict}")

            if isinstance(sql_dict, dict) and "error" in sql_dict:
                sql_error = sql_dict["error"]
                print(f"⚠️ SQL Generation failed: {sql_error}. Proceeding to Mongo fallback.")
            else:
                # Execute SQL
                query_results = execute_sql_on_all_databases(sql_dict)
                separate_results = {}
                
                for db_name, rows_or_error in query_results.items():
                    if isinstance(rows_or_error, list):
                        merged_rows.extend(rows_or_error)
                        separate_results[db_name] = rows_or_error
                    else:
                        # Store SQL execution error if it occurred
                        sql_error = rows_or_error
                        separate_results[db_name] = {"error": rows_or_error}

                # Success Check: If SQL executed without error AND returned data, return the result
                if merged_rows:
                    print("⚡ SQL execution successful and data found. Returning SQL results.")
                    
                    answer = convert_result_to_natural_language(question, merged_rows)
                    summary = generate_summary(question, merged_rows)
                    total_time = time.time() - start_time
                    chart_request = detect_chart_intent(question)
                    
                    return jsonify({
                        "success": True,
                        "answer": answer,
                        "summary": summary,
                        "data": merged_rows,
                        "db_type_used": "sql",
                        "separate_results": separate_results,
                        "chart_request": chart_request,
                        "performance": {"total_time": round(total_time, 2), "cached": "none"}
                    })
                # If we reach here, SQL failed to generate a result or returned 0 rows
                print("⚠️ SQL executed but returned 0 rows. Attempting Mongo fallback.")

        except Exception as e:
            # Catch unexpected SQL execution errors (like connectivity)
            sql_error = str(e)
            print(f"⚠️ SQL Execution failed: {sql_error}. Attempting Mongo fallback.")
        

        # --- 2. Attempt MongoDB Query Generation and Execution (Fallback) ---
        
        print("🔄 Falling back to MongoDB.")
        
        # 2a. Check for existence question for Mongo
        existence = detect_existence_question(question, "mongo")
        if existence is not None:
            total_time = time.time() - start_time
            return jsonify({
                "success": True,
                "answer": existence["answer"],
                "summary": existence.get("summary"),
                "data": [],
                "db_type_used": "mongo",
                "performance": {"total_time": round(total_time, 2), "cached": "none"}
            })

        # 2b. Generate Mongo Query
        mongo_query_dict = generate_mongo_query_from_nl(question)
        print(f"🔎 Attempting Mongo. Gemini MongoDB dict: {mongo_query_dict}")

        rows = []
        
        # 1. Check for None: If LLM generation failed and returned None.
        if mongo_query_dict is None: 
            mongo_error = "MongoDB query generation failed (LLM returned None)."
            print(f"❌ MongoDB Generation failed (Returned None).")
            
        # 2. Check for successful dict structure: If it generated a query.
        elif isinstance(mongo_query_dict, dict) and "collection" in mongo_query_dict:
            mongo_error = None
            try:
                collection = mongo_query_dict.get("collection")
                filter_query = mongo_query_dict.get("filter", {})
                projection = mongo_query_dict.get("projection")
                limit = mongo_query_dict.get("limit", 50)
                db_name = mongo_query_dict.get("db_name")
                db_name_used = None
                try:
                    if db_name:
                        rows = execute_mongo_query(db_name, collection, filter_query, projection, limit)
                        db_name_used = db_name
                        # If LLM suggested DB contained no rows, probe other DBs for the data
                        if not rows:
                            from app.db_mongo import find_db_for_collection, execute_mongo_query_across_dbs
                            resolved_db = find_db_for_collection(collection, filter_query)
                            if resolved_db and resolved_db != db_name:
                                rows = execute_mongo_query(resolved_db, collection, filter_query, projection, limit)
                                db_name_used = resolved_db
                            else:
                                # As a last resort scan all DBs and take the first non-empty result (excluding original db)
                                aggregated = execute_mongo_query_across_dbs(collection=collection, filter_query=filter_query, projection=projection, limit=limit)
                                for dbn, res in aggregated.items():
                                    if dbn == db_name:
                                        continue
                                    if isinstance(res, list) and res:
                                        rows = res
                                        db_name_used = dbn
                                        break
                except Exception as e:
                    mongo_error = str(e)
                    print(f"Error executing MongoDB query: {mongo_error}")
                    rows = []
                except Exception as e:
                    print(f"Error probing databases: {e}")
                    # Continue with empty rows
                else:
                    # Try to find the best DB for this collection+filter
                    from app.db_mongo import find_db_for_collection, execute_mongo_query_across_dbs
                    resolved_db = find_db_for_collection(collection, filter_query)
                    if resolved_db:
                        rows = execute_mongo_query(resolved_db, collection, filter_query, projection, limit)
                        db_name_used = resolved_db
                    else:
                        # No single DB identified, search across DBs and take first non-empty
                        aggregated = execute_mongo_query_across_dbs(collection=collection, filter_query=filter_query, projection=projection, limit=limit)
                        rows = []
                        for dbn, res in aggregated.items():
                            if isinstance(res, list) and res:
                                rows = res
                                db_name_used = dbn
                                break
                
                if rows:
                    print("✅ MongoDB execution successful and data found. Returning Mongo results.")
                    answer = convert_result_to_natural_language(question, rows)
                    summary = generate_summary(question, rows)
                    total_time = time.time() - start_time
                    chart_request = detect_chart_intent(question)
                    
                    return jsonify({
                        "success": True,
                        "answer": answer,
                        "summary": summary,
                        "data": rows,
                        "db_type_used": "mongo",
                        "db_name_used": db_name_used,
                        "chart_request": chart_request,
                        "performance": {"total_time": round(total_time, 2), "cached": "none"}
                    })
                
                print("❌ MongoDB query executed successfully but returned no data.")

            except Exception as e:
                mongo_error = str(e)
                print(f"❌ MongoDB Execution failed: {mongo_error}")
                
        # 3. Check for error dict: If it generated a dictionary with an explicit 'error' key.
        else:
            mongo_error = mongo_query_dict.get("error", "MongoDB query generation failed with unexpected dictionary structure.")
            print(f"❌ MongoDB Generation failed: {mongo_error}")


        # --- 3. Final Failure Response (Both failed) ---
        
        print("🛑 Both SQL and Mongo attempts failed or returned no data.")
        
        # Use the SQL db type for generating final suggestions if SQL was the primary failure path
        suggestions = generate_query_suggestions(question, "sql") 
        
        final_error = "Failed to get data from both databases."
        if sql_error and mongo_error:
            final_error += f" (SQL failure: {sql_error}. Mongo failure: {mongo_error})"
        elif sql_error:
            final_error += f" (SQL failure: {sql_error})"
        elif mongo_error:
            final_error += f" (Mongo failure: {mongo_error})"
        else:
            final_error += " (Queries executed but returned 0 results from both sources.)"

        return jsonify({
            "success": False,
            "error": final_error,
            "suggestions": suggestions,
            "original_question": question,
            "type": "query_failure_dual"
        }), 500

    except Exception as e:
        # Catch critical unhandled errors
        print(f"CRITICAL UNCAUGHT ERROR in nl_to_sql: {e}")
        suggestions = generate_query_suggestions(question, "sql") 
        return jsonify({
            "success": False, 
            "error": f"An unexpected server error occurred: {str(e)}", 
            "suggestions": suggestions,
            "type": "server_error"
        }), 500
