import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Default to bundled SQLite if not provided
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:////{os.path.abspath(os.path.join(os.path.dirname(__file__), 'mydb.sqlite3'))}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/yourdb")


    # Performance optimizations
    REQUEST_TIMEOUT = 30  # seconds
    LLM_TIMEOUT = 25  # seconds
    CACHE_TIMEOUT = 300  # 5 minutes
    
    # LLM optimization settings
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")  # Faster model
    MAX_TOKENS = 1000  # Limit response length for speed
    TEMPERATURE = 0.1  # Lower temperature for more focused responses
    
    # Database optimization
    DB_POOL_SIZE = 10
    DB_MAX_OVERFLOW = 20
    DB_POOL_TIMEOUT = 30
    
    # Security settings
    LOG_QUERY_TYPE = True  # Log query type for monitoring
    LOG_TABLE_NAMES = True  # Log accessed tables for security
    EXPOSE_SQL = False  # Never expose generated SQL to frontend
