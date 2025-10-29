import urllib.request
import json

def test_query(query):
    print(f"\nTesting query: {query}")
    try:
        data = json.dumps({'sql': query, 'db_type': 'sql'}).encode('utf-8')
        req = urllib.request.Request(
            'http://localhost:5001/api/query',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            print("Success!")
            print("Response:", json.dumps(result, indent=2))
            return result
    except Exception as e:
        print("Error:", e)
        if hasattr(e, 'read'):
            print("Response body:", e.read().decode())
        return None

# Test simple SELECT
test_query("SELECT * FROM books")

# Test column names
test_query("SELECT title, author FROM books")

# Test WHERE clause
test_query("SELECT * FROM books WHERE year > 1900")