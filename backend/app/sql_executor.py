from sqlalchemy import create_engine, text
from config import Config
import re

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)


def clean_sql(sql: str) -> str:
    """
    Remove markdown code fences and leading/trailing whitespace from SQL string.
    """
    sql = sql.strip()
    # Remove triple backticks and optional "sql" after them
    if sql.startswith("```"):
        # Remove opening ```
        sql = sql.lstrip("`")
        # Remove optional "sql" prefix
        sql = sql.lstrip("sql").strip()
        # Remove trailing ```
        if sql.endswith("```"):
            sql = sql[:-3].strip()
    return sql


def is_safe_query(sql):
    # Allow only SELECT queries
    sql = sql.strip().lower()
    # Ensure it starts with 'select' and doesn't contain dangerous keywords
    return sql.startswith("select") and not re.search(r"\b(update|delete|insert|drop|alter|create)\b", sql)


def execute_safe_sql(sql):
    # Clean markdown fences if present
    sql = clean_sql(sql)

    if not is_safe_query(sql):
        return {"success": False, "error": "Only safe SELECT queries are allowed."}

    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            rows = [dict(row._mapping) for row in result]
            return {"success": True, "rows": rows}
    except Exception as e:
        return {"success": False, "error": str(e)}

