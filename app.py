import os
import json
import logging
from dotenv import load_dotenv

# Ensure environment variables from backend/.env are loaded when the app
# is started from the repository root. This keeps behavior consistent when
# running `python app.py` from the project root or from other folders.
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import psycopg2
import pymongo
from psycopg2 import sql as psql

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

# --- Database Config ---
POSTGRES = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': int(os.environ.get('PG_PORT', 5432)),
    'user': os.environ.get('PG_USER', 'postgres'),
    'password': os.environ.get('PG_PASSWORD', 'postgres'),
    'dbname': os.environ.get('PG_DB', 'testdb'),
}
MONGO_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
MONGO_DB = os.environ.get('MONGO_DB', 'photodb')

# --- PostgreSQL Connection ---
def get_pg_conn():
    return psycopg2.connect(**POSTGRES)

# --- MongoDB Connection ---
try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Try a quick server_info to fail fast if unreachable
    mongo_client.server_info()
except Exception as e:
    logging.warning("Could not connect to MongoDB at startup: %s", e)
    mongo_client = None

# --- Home & Navigation ---
@app.route('/')
def home():
    return render_template('master.html')

# --- Health ---
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'pg': True, 'mongo': bool(mongo_client)}), 200

# --- SQL Interface ---
@app.route('/sql')
def sql_page():
    return render_template('sql.html')

@app.route('/sql/execute', methods=['POST'])
def sql_execute():
    if not request.is_json:
        return jsonify({'columns': [], 'rows': [], 'error': 'Expected application/json'}), 400
    query = request.json.get('query')
    if not query or not query.strip():
        return jsonify({'columns': [], 'rows': [], 'error': 'Empty query'}), 400
    try:
        with get_pg_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    # Convert rows (tuples) into lists for JSON serialization
                    rows = [list(r) for r in rows]
                    return jsonify({'columns': columns, 'rows': rows, 'error': None}), 200
                else:
                    # Non-select (INSERT/UPDATE/DELETE)
                    conn.commit()
                    return jsonify({'columns': [], 'rows': [], 'error': None}), 200
    except Exception as e:
        logging.exception("SQL execute error")
        return jsonify({'columns': [], 'rows': [], 'error': str(e)}), 500

# --- NoSQL Interface ---
@app.route('/nosql')
def nosql_page():
    return render_template('nosql.html')

@app.route('/nosql/execute', methods=['POST'])
def nosql_execute():
    if not request.is_json:
        return jsonify({'docs': [], 'error': 'Expected application/json'}), 400
    query = request.json.get('query')
    if not query or not query.strip():
        return jsonify({'docs': [], 'error': 'Empty query'}), 400
    if mongo_client is None:
        return jsonify({'docs': [], 'error': 'MongoDB client not available'}), 500
    try:
        # Only allow find queries for safety
        if not query.strip().startswith('db.') or '.find' not in query:
            raise ValueError('Only find queries are allowed. Use db.collection.find({...})')
        import re
        m = re.match(r'db\.([a-zA-Z0-9_]+)\.find\((.*)\)', query.strip())
        if not m:
            raise ValueError('Query format invalid. Use db.collection.find({...})')
        collection = m.group(1)
        filter_str = m.group(2)
        filter_dict = json.loads(filter_str) if filter_str.strip() else {}
        db = mongo_client[MONGO_DB]
        docs = list(db[collection].find(filter_dict, {'_id': 0}))
        # Ensure docs are JSON serializable
        return jsonify({'docs': docs, 'error': None}), 200
    except Exception as e:
        logging.exception("NoSQL execute error")
        return jsonify({'docs': [], 'error': str(e)}), 500

# --- Master Interface (NL) ---
@app.route('/master')
def master_page():
    return render_template('master.html')

@app.route('/master/ask', methods=['POST'])
def master_ask():
    if not request.is_json:
        return jsonify({'error': 'Expected application/json'}), 400
    question = request.json.get('question', '')
    if not question or not question.strip():
        return jsonify({'error': 'Empty question'}), 400
    ql = question.lower()
    try:
        if any(word in ql for word in ['find', 'select', 'from', 'where']):
            # SQL
            sql_query = parse_nl_to_sql(question)
            with get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_query)
                    columns = [desc[0] for desc in cur.description] if cur.description else []
                    rows = [list(r) for r in cur.fetchall()] if cur.description else []
                    return jsonify({'columns': columns, 'rows': rows, 'type': 'sql', 'error': None}), 200
        elif any(word in ql for word in ['db.', 'collection', 'mongo', 'document']):
            # NoSQL
            if mongo_client is None:
                return jsonify({'error': 'MongoDB client not available'}), 500
            mongo_query = parse_nl_to_mongo(question)
            db = mongo_client[MONGO_DB]
            collection = mongo_query['collection']
            filter_dict = mongo_query['filter']
            docs = list(db[collection].find(filter_dict, {'_id': 0}))
            return jsonify({'docs': docs, 'type': 'mongo', 'error': None}), 200
        else:
            # Fallback: try SQL then Mongo
            try:
                sql_query = parse_nl_to_sql(question)
                with get_pg_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql_query)
                        columns = [desc[0] for desc in cur.description] if cur.description else []
                        rows = [list(r) for r in cur.fetchall()] if cur.description else []
                        return jsonify({'columns': columns, 'rows': rows, 'type': 'sql', 'error': None}), 200
            except Exception:
                if mongo_client is None:
                    return jsonify({'error': 'MongoDB client not available'}), 500
                mongo_query = parse_nl_to_mongo(question)
                db = mongo_client[MONGO_DB]
                collection = mongo_query['collection']
                filter_dict = mongo_query['filter']
                docs = list(db[collection].find(filter_dict, {'_id': 0}))
                return jsonify({'docs': docs, 'type': 'mongo', 'error': None}), 200
    except Exception as e:
        logging.exception("Master ask error")
        return jsonify({'error': str(e)}), 500

# --- NL to SQL (simple rule-based, replace with LLM for production) ---
def parse_nl_to_sql(question):
    ql = question.lower()
    if 'students' in ql and 'older than' in ql:
        import re
        m = re.search(r'older than (\d+)', ql)
        if m:
            age = int(m.group(1))
            return f"SELECT * FROM students WHERE age > {age}"
    if 'all students' in ql or 'list students' in ql:
        return "SELECT * FROM students"
    raise ValueError('Could not parse NL to SQL. Please rephrase.')

# --- NL to Mongo (simple rule-based, replace with LLM for production) ---
def parse_nl_to_mongo(question):
    ql = question.lower()
    if 'images' in ql and 'older than' in ql:
        import re
        m = re.search(r'older than (\d+)', ql)
        if m:
            age = int(m.group(1))
            return {'collection': 'images', 'filter': {'age': {'$gt': age}}}
    if 'all images' in ql or 'list images' in ql:
        return {'collection': 'images', 'filter': {}}
    raise ValueError('Could not parse NL to Mongo. Please rephrase.')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)