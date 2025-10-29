from bson import ObjectId
from json import JSONEncoder
from datetime import datetime

class MongoJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return JSONEncoder.default(self, obj)