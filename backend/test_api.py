import requests
import json

def test_query():
    url = "http://localhost:5001/api/nl-to-sql"  # The correct endpoint
    data = {
        "question": "Show me all books",
        "db_type": "sql"
    }
    response = requests.post(url, json=data)
    print("Status code:", response.status_code)
    print("\nResponse:")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_query()