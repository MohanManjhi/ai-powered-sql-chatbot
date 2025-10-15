import os
import pymongo

_mongo_client = None

def _initialize_mongo_client():
    global _mongo_client
    if _mongo_client:
        return
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    _mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    # Test connection
    _mongo_client.admin.command('ping')
    print(f"✅ Connected to MongoDB server at {mongo_uri}")

def get_mongo_collections_schema():
    """
    Returns a dict of all databases and their collections' sample schema.
    """
    _initialize_mongo_client()
    schema = {}
    for db_name in _mongo_client.list_database_names():
        if db_name in ("admin", "local", "config"):
            continue
        db = _mongo_client[db_name]
        db_schema = {}
        for coll_name in db.list_collection_names():
            sample_doc = db[coll_name].find_one(projection={"_id": 0})
            if sample_doc:
                db_schema[coll_name] = {k: type(v).__name__ for k, v in sample_doc.items()}
            else:
                db_schema[coll_name] = {}
        schema[db_name] = db_schema
    return schema

def execute_mongo_query(db_name, collection, filter_query=None, projection=None, limit=50):
    """
    Executes a query on the specified database and collection.
    """
    _initialize_mongo_client()
    db = _mongo_client[db_name]
    default_projection = {"_id": 0}
    if isinstance(projection, dict):
        final_projection = {**projection, **default_projection}
    else:
        final_projection = default_projection
    cursor = db[collection].find(filter_query or {}, final_projection).limit(limit)
    results = [doc for doc in cursor]
    print(f"Executed Mongo Query: {db_name}.{collection}.find({filter_query}, {final_projection}).limit({limit}) -> {len(results)} results")
    return results


def execute_mongo_query_across_dbs(collection=None, filter_query=None, projection=None, limit=50):
    """
    Execute the same query across all non-system databases on the connected server.
    Returns a dict mapping db_name -> list of documents (may be empty lists).
    """
    _initialize_mongo_client()
    aggregated = {}
    for db_name in _mongo_client.list_database_names():
        if db_name in ("admin", "local", "config"):
            continue
        try:
            db = _mongo_client[db_name]
            # If a specific collection requested, only query that collection if present
            collections = [collection] if collection and collection in db.list_collection_names() else db.list_collection_names()
            results = []
            for coll in collections:
                # Build safe projection
                default_projection = {"_id": 0}
                final_projection = projection if isinstance(projection, dict) else default_projection
                cur = db[coll].find(filter_query or {}, final_projection).limit(limit)
                docs = [doc for doc in cur]
                if docs:
                    # include db and collection info
                    for d in docs:
                        d['_db'] = db_name
                        d['_collection'] = coll
                    results.extend(docs)
            aggregated[db_name] = results
        except Exception as e:
            aggregated[db_name] = {"error": str(e)}
    return aggregated


def find_db_for_collection(collection, filter_query=None, probe_limit=1):
    """
    Heuristic: find the most appropriate database name that contains the given collection
    and (optionally) matches the provided filter_query. Returns the db_name string or None.
    Steps:
      - List DBs that contain the collection.
      - If only one, return it.
      - If multiple and filter_query provided, probe each DB using execute_mongo_query with limit=probe_limit.
      - Return the first DB that yields results.
      - If none matched, return None.
    """
    _initialize_mongo_client()
    try:
        candidate_dbs = []
        for db_name in _mongo_client.list_database_names():
            if db_name in ("admin", "local", "config"):
                continue
            db = _mongo_client[db_name]
            try:
                if collection in db.list_collection_names():
                    candidate_dbs.append(db_name)
            except Exception:
                # ignore databases we can't list
                continue

        if not candidate_dbs:
            return None
        if len(candidate_dbs) == 1:
            return candidate_dbs[0]

        # Multiple candidates: probe if filter provided
        if filter_query:
            for db_name in candidate_dbs:
                try:
                    res = execute_mongo_query(db_name, collection, filter_query, {}, probe_limit)
                    if isinstance(res, list) and len(res) > 0:
                        return db_name
                except Exception:
                    continue

        # no probe match; prefer 'cardb' if available, else return first candidate
        if 'cardb' in candidate_dbs:
            return 'cardb'
        return candidate_dbs[0]
    except Exception:
        return None

def execute_nl_query(question):
    """
    Handles the entire process: NL -> LLM JSON -> Mongo Execution.
    """
    from app.llm.gemini_mongo_generator import generate_mongo_query_from_nl

    print("🔎 Attempting Mongo NL-to-Query conversion...")
    llm_query_dict = generate_mongo_query_from_nl(question)
    
    if 'error' in llm_query_dict:
        print(f"❌ LLM Query Generation failed: {llm_query_dict['error']}")
        return {"error": llm_query_dict['error']}

    target_db_name = llm_query_dict.get('db_name')
    target_collection = llm_query_dict.get('collection')

    # Try to infer collection from the question if LLM omitted it (common case)
    if not target_collection:
        q = (question or "").lower()
        if 'image' in q or 'photo' in q or 'images' in q or 'photos' in q:
            target_collection = 'images'

    # If we have both db and collection, execute directly
    if target_db_name and target_collection:
        print(f"🔎 Attempting Mongo Execution. DB: {target_db_name}, Collection: {target_collection}")
        try:
            results = execute_mongo_query(
                db_name=target_db_name,
                collection=target_collection,
                filter_query=llm_query_dict.get('filter', {}),
                projection=llm_query_dict.get('projection'),
                limit=llm_query_dict.get('limit', 50)
            )
            return results
        except Exception as e:
            print(f"❌ MongoDB Execution failed: {str(e)}")
            return {"error": f"MongoDB Execution failed: {str(e)}"}

    # If collection present but db missing, try to resolve the DB using heuristics/probing
    if target_collection and not target_db_name:
        print(f"🔎 LLM omitted db_name; attempting to resolve DB for collection '{target_collection}'")
        try:
            resolved = find_db_for_collection(target_collection, llm_query_dict.get('filter', {}))
            if resolved:
                try:
                    results = execute_mongo_query(
                        db_name=resolved,
                        collection=target_collection,
                        filter_query=llm_query_dict.get('filter', {}),
                        projection=llm_query_dict.get('projection'),
                        limit=llm_query_dict.get('limit', 50)
                    )
                    if results:
                        # annotate which DB was used
                        return {"db_name_used": resolved, "rows": results}
                except Exception:
                    pass

            # If resolving didn't return data, scan all DBs for matching docs and return first non-empty
            aggregated = execute_mongo_query_across_dbs(collection=target_collection, filter_query=llm_query_dict.get('filter', {}), projection=llm_query_dict.get('projection'), limit=llm_query_dict.get('limit', 50))
            # aggregated: {db_name: [docs] or {error:...}}
            summary = {}
            for dbn, res in aggregated.items():
                if isinstance(res, list) and res:
                    # return the first non-empty set we find
                    return {"db_name_used": dbn, "rows": res}
                # collect small summary for debugging
                if isinstance(res, dict) and 'error' in res:
                    summary[dbn] = {"error": res['error']}
                else:
                    summary[dbn] = {"count": len(res) if isinstance(res, list) else 0}

            # Nothing found across DBs
            return {"error": "No matching documents found across databases.", "db_probe_summary": summary}
        except Exception as e:
            return {"error": f"DB resolution failed: {str(e)}"}

    # If we still don't know what to query, return a helpful message (don't dump full schemas by default)
    return {"error": "LLM did not specify db_name or collection, and collection could not be inferred. Please ask specifically (e.g., 'Find images where name = \"nano\" in db cardb')."}