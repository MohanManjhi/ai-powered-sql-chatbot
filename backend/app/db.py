import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from config import Config

load_dotenv()

# Load multiple database URIs from .env
DATABASES = {
    "db1": os.getenv("DATABASE_URL_1"),
    "db2": os.getenv("DATABASE_URL_2"),
    "db3": os.getenv("DATABASE_URL_3"),
    "db4": os.getenv("DATABASE_URL_4"),
    "db5": os.getenv("DATABASE_URL_5"),
}

# Create SQLAlchemy engines for all databases
engines = {name: create_engine(uri) for name, uri in DATABASES.items() if uri}
engine = engines.get("db1")  # Default engine for backward compatibility

def get_schema(db_name="db1"):
    inspector = inspect(engines[db_name])
    schema = {}
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        schema[table_name] = [col["name"] for col in columns]
    return schema

# Utility to get all schemas

def get_all_schemas():
    return {db: get_schema(db) for db in engines}

def execute_sql_on_all_databases(sql_dict):
    """
    sql_dict: {db_name: sql_query}
    Returns: {db_name: [rows]}
    """
    results = {}
    for db_name, sql_query in sql_dict.items():
        try:
            with engines[db_name].connect() as conn:
                result = conn.execute(sql_query)
                results[db_name] = [dict(row) for row in result]
        except Exception as e:
            results[db_name] = {"error": str(e)}
    return results
