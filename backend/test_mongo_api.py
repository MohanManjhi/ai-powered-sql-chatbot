import requests
import json

def test_mongo_query():
    url = "http://localhost:5001/api/nl-to-sql"
    data = {
        "question": "Show me all photos",
        "db_type": "mongo"
    }
    
    print("\nSending request:", json.dumps(data, indent=2))
    response = requests.post(url, json=data)
    print("\nStatus code:", response.status_code)
    print("\nResponse:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

if __name__ == "__main__":
    test_mongo_query()