import os
import re
from urllib.parse import urlparse
from typing import Any


def _default_db_from_env():
    """Extract default database name from MONGODB_URI if present."""
    mongo_uri = os.environ.get('MONGODB_URI') or os.environ.get('MONGODB_URI_6') or os.environ.get('MONGO_URI')
    if not mongo_uri:
        return None
    try:
        parsed = urlparse(mongo_uri)
        db = parsed.path.strip('/')
        return db or None
    except Exception:
        return None


def generate_mongo_query_from_nl(question: str) -> dict:
    """Simple, deterministic NL->Mongo query converter used as a safe fallback.

    This function does not call any LLM; it's a heuristic parser that extracts
    `db_name`, `collection`, `filter`, `projection`, and `limit` from the question.
    Replace this with your LLM call when you integrate a model.
    """
    q = (question or '').strip()
    ql = q.lower()

    def _normalize_val(v: str) -> Any:
        v = v.strip().strip('"\'')
        # integer
        if re.fullmatch(r"\d+", v):
            try:
                return int(v)
            except Exception:
                pass
        return v

    # Try to extract collection name: look for 'X collection' or 'collection X'
    coll = None
    m = re.search(r"([a-zA-Z0-9_]+)\s+collection", ql)
    if m:
        coll = m.group(1)
    else:
        m = re.search(r"collection\s+([a-zA-Z0-9_]+)", ql)
        if m:
            coll = m.group(1)

    # Try to extract database name: 'in the X database' or 'X database'
    db = None
    m = re.search(r"in the ([a-zA-Z0-9_]+) database", ql)
    if m:
        db = m.group(1)
    else:
        m = re.search(r"([a-zA-Z0-9_]+) database", ql)
        if m:
            db = m.group(1)

    # If no collection explicitly found from schema, try to find common collection keywords
    if not coll:
        # Map common terms to collection names
        term_to_collection = {
            'photo': 'photos',
            'image': 'photos',
            'picture': 'photos',
            'file': 'files',
            'car': 'cars',
            'vehicle': 'cars',
            'product': 'products',
            'user': 'users'
        }
        
        for term, collection in term_to_collection.items():
            if term in ql:
                coll = collection
                break

    # First, try to determine the collection from available collections
    try:
        from app.db_mongo import get_mongo_collections_schema
        schema = get_mongo_collections_schema() or {}
        all_collections = set()
        for db_cols in schema.values():
            all_collections.update(db_cols.keys())
        
        # If collection is in the question, use it
        for collection in all_collections:
            if collection.lower() in ql:
                coll = collection
                break
    except Exception:
        pass

    # Basic filter extraction: look for quoted strings or 'name is', 'filename is' etc.
    filter_q = {}
    # quoted values: "..." or '...'
    mq = re.search(r"\"([^\"]+)\"", q) or re.search(r"'([^']+)'", q)
    if mq:
        token = mq.group(1).strip()
        # heuristics: if the question mentions filename, use filename
        if 'filename' in ql or 'file name' in ql or token.lower().endswith(('.jpg', '.jpeg', '.png')):
            filter_q = {"filename": _normalize_val(token)}
        elif 'name' in ql or 'model' in ql:
            filter_q = {"name": _normalize_val(token)}
        else:
            # default to name
            filter_q = {"name": _normalize_val(token)}
    else:
        # explicit patterns
        mname = re.search(r"filename\s+(?:is|=)\s*([a-zA-Z0-9_\-\.]+)", ql)
        if mname:
            filter_q = {"filename": _normalize_val(mname.group(1))}
        else:
            mname = re.search(r"name\s+(?:is|=)\s*([a-zA-Z0-9_\-]+)", ql)
            if mname:
                filter_q = {"name": _normalize_val(mname.group(1))}
            else:
                # common tokens
                m = re.search(r"\b(nano|mini|alto|swift|baleno|tata)\b", ql)
                if m:
                    filter_q = {"name": _normalize_val(m.group(1))}

    # If question explicitly mentions a database name that's present on the server, use it.
    if not db:
        try:
            from app.db_mongo import get_mongo_collections_schema
            server_schema = get_mongo_collections_schema() or {}
            # If any database name appears verbatim in the question, prefer it
            for candidate_db in server_schema.keys():
                if candidate_db.lower() in ql:
                    db = candidate_db
                    break
        except Exception:
            pass

    # Final fallbacks and smarter db resolution using server schema
    if not db:
        # Consult server to see which DBs contain this collection
        try:
            from app.db_mongo import get_mongo_collections_schema, execute_mongo_query
            schema = get_mongo_collections_schema() or {}
            # Find DBs that contain the collection
            candidate_dbs = [d for d, cols in schema.items() if coll in cols]
            if len(candidate_dbs) == 1:
                db = candidate_dbs[0]
            elif len(candidate_dbs) > 1:
                # If filter specifies an identifying value, probe each DB for matching documents
                probed_db = None
                if filter_q:
                    for d in candidate_dbs:
                        try:
                            res = execute_mongo_query(db_name=d, collection=coll, filter_query=filter_q, projection={}, limit=1)
                            if isinstance(res, list) and len(res) > 0:
                                probed_db = d
                                break
                        except Exception:
                            continue
                # Prefer 'cardb' if present and no probe match
                if probed_db:
                    db = probed_db
                elif 'cardb' in candidate_dbs:
                    db = 'cardb'
                else:
                    # fallback to first candidate or env default
                    db = candidate_dbs[0]
            else:
                db = _default_db_from_env() or 'cardb'
        except Exception:
            db = _default_db_from_env() or 'cardb'
    if not coll:
        coll = 'images'

    return {
        "db_name": db,
        "collection": coll,
        "filter": filter_q or {},
        "projection": {},
        "limit": 50
    }