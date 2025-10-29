import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from config import Config

load_dotenv()

# Load all database URLs from environment variables
DATABASES = {}
for i in range(1, 6):  # We have DATABASE_URL_1 through DATABASE_URL_5
    db_url = os.getenv(f'DATABASE_URL_{i}')
    if db_url:
        DATABASES[f"db{i}"] = db_url

# Create SQLAlchemy engines with pooling configuration
engines = {}
for name, uri in DATABASES.items():
    engines[name] = create_engine(
        uri,
        pool_size=Config.DB_POOL_SIZE,
        max_overflow=Config.DB_MAX_OVERFLOW,
        pool_timeout=Config.DB_POOL_TIMEOUT
    )
engine = engines.get("db2", next(iter(engines.values())))  # Use books_db (db2) as default, or first available database

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
    # If sql_dict is a string, convert it to a dict with db2 as the key
    if isinstance(sql_dict, str):
        sql_dict = {"db2": sql_dict}  # Use books_db by default
    
    for db_name, sql_query in sql_dict.items():
        try:
            if db_name not in engines:
                continue  # Skip if database is not configured
            with engines[db_name].connect() as conn:
                # Ensure we pass an executable SQL object to SQLAlchemy
                if isinstance(sql_query, str):
                    stmt = text(sql_query)
                else:
                    stmt = sql_query
                result = conn.execute(stmt)
                # Use row._mapping for robust conversion across SQLAlchemy versions
                results[db_name] = [dict(row._mapping) for row in result]
        except Exception as e:
            results[db_name] = {"error": str(e)}
    return results
