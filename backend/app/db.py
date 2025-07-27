from sqlalchemy import create_engine, inspect
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

def get_schema():
    inspector = inspect(engine)
    schema = {}

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        schema[table_name] = [col["name"] for col in columns]

    return schema
