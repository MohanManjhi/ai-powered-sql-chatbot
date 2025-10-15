import os
import json
from pymongo import MongoClient

uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
client = MongoClient(uri, serverSelectionTimeoutMS=5000)
collection = 'images'
filter_query = {'filename': 'tata'}

print('Using URI:', uri)
for dbname in client.list_database_names():
    if dbname in ('admin', 'local', 'config'):
        continue
    db = client[dbname]
    try:
        if collection in db.list_collection_names():
            try:
                cnt = db[collection].count_documents(filter_query)
            except Exception as e:
                print(f"{dbname}.{collection} -> error counting: {e}")
                continue
            print(f"{dbname}.{collection} -> {cnt} matches")
            if cnt:
                doc = db[collection].find_one(filter_query, {'_id': 0})
                print(' sample:', json.dumps(doc, default=str))
        else:
            print(f"{dbname}.{collection} -> collection not present")
    except Exception as e:
        print(f"{dbname} -> error listing collections: {e}")
