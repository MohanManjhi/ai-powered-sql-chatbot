from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

uri = os.getenv('DATABASE_URL_1') or os.getenv('DATABASE_URL_2') or os.getenv('DATABASE_URL_3')
if not uri:
    print('No DATABASE_URL_* found in .env')
    raise SystemExit(1)

print('Using:', uri)
engine = create_engine(uri)
with engine.connect() as conn:
    try:
        res = conn.execute(text('SELECT * FROM students LIMIT 5'))
        rows = [dict(r._mapping) for r in res]
        print('rows:', rows)
    except Exception as e:
        print('Error executing test query:', e)
