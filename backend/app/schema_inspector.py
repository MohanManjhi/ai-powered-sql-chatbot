# app/schema_inspector.py
from sqlalchemy import inspect
from app.db import engine

def get_db_schema():
    inspector = inspect(engine)
    schema = {}

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        schema[table_name] = [col['name'] for col in columns]

    return schema
