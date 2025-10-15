# app/schema_inspector.py
from sqlalchemy import inspect
from app.db import engine, engines  # Import the engines dictionary

def get_all_db_schemas(engines):
    """Return schemas for all databases as {db_name: {table: [columns]}}"""
    all_schemas = {}
    for db_name, engine in engines.items():
        inspector = inspect(engine)
        schema = {}
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            schema[table_name] = [col['name'] for col in columns]
        all_schemas[db_name] = schema
    return all_schemas

def get_db_schema():
    return get_all_db_schemas(engines)["db1"]
