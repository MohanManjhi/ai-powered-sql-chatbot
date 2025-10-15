import os
import json
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import psycopg2
import pymongo
from psycopg2 import sql as psql

app = Flask(__name__)
CORS(app)

# --- Database Config ---
POSTGRES = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': os.environ.get('PG_PORT', 5432),
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
mongo_client = pymongo.MongoClient(MONGO_URI)

# --- Home & Navigation ---
@app.route('/')
def home():
    return render_template('master.html')

# --- SQL Interface ---
@app.route('/sql')
def sql_page():
    return render_template('sql.html')

@app.route('/sql/execute', methods=['POST'])
def sql_execute():
    query = request.json.get('query')
    try:
        with get_pg_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    return jsonify({'columns': columns, 'rows': rows, 'error': None})
                else:
                    conn.commit()
                    return jsonify({'columns': [], 'rows': [], 'error': None})
    except Exception as e:
        return jsonify({'columns': [], 'rows': [], 'error': str(e)})

# --- NoSQL Interface ---
@app.route('/nosql')
def nosql_page():
    return render_template('nosql.html')

@app.route('/nosql/execute', methods=['POST'])
def nosql_execute():
    query = request.json.get('query')
    try:
        # Only allow find queries for safety
        if not query.strip().startswith('db.') or '.find' not in query:
            raise ValueError('Only find queries are allowed.')
        # Parse: db.collection.find({...})
        import re
        m = re.match(r'db\.([a-zA-Z0-9_]+)\.find\((.*)\)', query.strip())
        if not m:
            raise ValueError('Query format invalid. Use db.collection.find({...})')
        collection = m.group(1)
        filter_str = m.group(2)
        filter_dict = json.loads(filter_str) if filter_str.strip() else {}
        db = mongo_client[MONGO_DB]
        docs = list(db[collection].find(filter_dict, {'_id': 0}))
        return jsonify({'docs': docs, 'error': None})
    except Exception as e:
        return jsonify({'docs': [], 'error': str(e)})

# --- Master Interface (NL) ---
@app.route('/master')
def master_page():
    return render_template('master.html')

@app.route('/master/ask', methods=['POST'])
def master_ask():
    question = request.json.get('question', '')
    ql = question.lower()
    try:
        if any(word in ql for word in ['find', 'select', 'from', 'where']):
            # SQL
            sql_query = parse_nl_to_sql(question)
            with get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_query)
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    return jsonify({'columns': columns, 'rows': rows, 'type': 'sql', 'error': None})
        elif any(word in ql for word in ['db.', 'collection', 'mongo', 'document']):
            # NoSQL
            mongo_query = parse_nl_to_mongo(question)
            db = mongo_client[MONGO_DB]
            collection = mongo_query['collection']
            filter_dict = mongo_query['filter']
            docs = list(db[collection].find(filter_dict, {'_id': 0}))
            return jsonify({'docs': docs, 'type': 'mongo', 'error': None})
        else:
            # Fallback: try both
            try:
                sql_query = parse_nl_to_sql(question)
                with get_pg_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql_query)
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                        return jsonify({'columns': columns, 'rows': rows, 'type': 'sql', 'error': None})
            except Exception:
                mongo_query = parse_nl_to_mongo(question)
                db = mongo_client[MONGO_DB]
                collection = mongo_query['collection']
                filter_dict = mongo_query['filter']
                docs = list(db[collection].find(filter_dict, {'_id': 0}))
                return jsonify({'docs': docs, 'type': 'mongo', 'error': None})
    except Exception as e:
        return jsonify({'error': str(e)})

# --- NL to SQL (simple rule-based, replace with LLM for production) ---
def parse_nl_to_sql(question):
    ql = question.lower()
    if 'students' in ql and 'older than' in ql:
        import re
        m = re.search(r'older than (\d+)', ql)
        if m:
            age = int(m.group(1))
            return f"SELECT * FROM students WHERE age > {age}"
    if 'all students' in ql:
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
    if 'all images' in ql:
        return {'collection': 'images', 'filter': {}}
    raise ValueError('Could not parse NL to Mongo. Please rephrase.')


@app.route('/sql/execute', methods=['POST'])
def sql_execute():
    query = request.json.get('query')
    try:
        with get_pg_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    return jsonify({'columns': columns, 'rows': rows, 'error': None})
                else:
                    conn.commit()
                    return jsonify({'columns': [], 'rows': [], 'error': None})
    except Exception as e:
        return jsonify({'columns': [], 'rows': [], 'error': str(e)})

@app.route('/nosql/execute', methods=['POST'])
def nosql_execute():
    query = request.json.get('query')
    try:
        # Only allow find queries for safety
        if not query.strip().startswith('db.') or '.find' not in query:
            raise ValueError('Only find queries are allowed.')
        import re
        m = re.match(r'db\.([a-zA-Z0-9_]+)\.find\((.*)\)', query.strip())
        if not m:
            raise ValueError('Query format invalid. Use db.collection.find({...})')
        collection = m.group(1)
        filter_str = m.group(2)
        filter_dict = json.loads(filter_str) if filter_str.strip() else {}
        db = mongo_client[MONGO_DB]
        docs = list(db[collection].find(filter_dict, {'_id': 0}))
        return jsonify({'docs': docs, 'error': None})
    except Exception as e:
        return jsonify({'docs': [], 'error': str(e)})

    
if __name__ == '__main__':
    app.run(debug=True, port=5001)