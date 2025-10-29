from dotenv import load_dotenv
import os
import pymongo

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

uri = os.getenv('MONGODB_URI') or os.getenv('MONGODB_URI_6') or os.getenv('MONGODB_URI_7')
if not uri:
    print('No MONGODB_URI found in .env')
    raise SystemExit(1)

print('Trying', uri)
client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
try:
    info = client.server_info()
    print('Mongo server info retrieved, ok')
    dbs = [d for d in client.list_database_names() if d not in ('admin','local','config')]
    print('Databases visible:', dbs)
except Exception as e:
    print('Mongo connection failed:', e)
