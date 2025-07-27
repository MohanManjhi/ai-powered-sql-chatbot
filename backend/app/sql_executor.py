from sqlalchemy import create_engine, text
from config import Config
import re

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

def is_safe_query(sql):
    # Allow only SELECT queries
    sql = sql.strip().lower()
    return sql.startswith("select") and not re.search(r"\b(update|delete|insert|drop|alter|create)\b", sql)

def execute_safe_sql(sql):
    if not is_safe_query(sql):
        return {"success": False, "error": "Only safe SELECT queries are allowed."}

    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            rows = [dict(row._mapping) for row in result]
            return {"success": True, "rows": rows}
    except Exception as e:
        return {"success": False, "error": str(e)}
