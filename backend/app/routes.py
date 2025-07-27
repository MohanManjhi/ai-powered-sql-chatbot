from flask import Blueprint, jsonify, request
from .db import get_schema
from .sql_executor import execute_safe_sql


main = Blueprint('main', __name__)

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
    

@main.route("/api/query", methods=["POST"])
def run_sql_query():
    print("🚀 /api/query route hit")
    data = request.get_json()
    sql = data.get("sql", "")
    print("Received data:", data)

    result = execute_safe_sql(sql)
    return jsonify(result)

@main.route("/ping")
def ping():
    print("✅ Ping hit")
    return "pong"

@main.route("/api/nl-to-sql", methods=["POST"])
def nl_to_sql():
    data = request.get_json()
    question = data.get("question", "")

    from app.llm.gemini_sql_generator import generate_sql_from_nl
    sql = generate_sql_from_nl(question)

    if sql.startswith("ERROR"):
        return jsonify({"success": False, "error": sql})

    return jsonify({"success": True, "sql": sql})
