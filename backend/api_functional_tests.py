import unittest
import requests
import json

class TestApiFunctional(unittest.TestCase):

    BASE_URL = "http://localhost:5001"

    def test_sql_query_success(self):
        """
        Test Case IT-API-001: End-to-End SQL Query Flow (Happy Path)
        """
        url = self.BASE_URL + "/api/nl-to-sql"
        data = {"question": "Show me all books", "db_type": "sql"}
        response = requests.post(url, json=data)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("answer", response_data)
        self.assertIn("summary", response_data)
        self.assertIn("data", response_data)

    def test_mongo_query_success(self):
        """
        Test Case IT-API-002: MongoDB Query Endpoint (Happy Path)
        """
        url = self.BASE_URL + "/api/nl-to-mongodb"
        data = {"question": "Show me all photos"}
        response = requests.post(url, json=data)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("answer", response_data)
        self.assertIn("summary", response_data)
        self.assertIn("data", response_data)

    def test_schema_endpoint(self):
        """
        Test Case IT-API-003: Schema Endpoint Integration
        """
        url = self.BASE_URL + "/api/schema"
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIsInstance(response_data, dict)

    # def test_health_check_endpoint(self):
    #     """
    #     Test Case IT-API-004: Health Check Endpoint
    #     """
    #     url = self.BASE_URL + "/api/health-details"
    #     response = requests.get(url)
    #     self.assertEqual(response.status_code, 200)
    #     response_data = response.json()
    #     self.assertIn("sql", response_data)
    #     self.assertIn("mongo", response_data)

    def test_invalid_db_type(self):
        """
        Test error handling for invalid db_type
        """
        url = self.BASE_URL + "/api/nl-to-sql"
        data = {"question": "Show me all books", "db_type": "invalid_db"}
        response = requests.post(url, json=data)
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("error", response_data)

if __name__ == '__main__':
    print("--- Starting API Functional Tests ---")
    print("Make sure your Flask application is running.")
    
    # You can run this script directly to execute the tests.
    # The output will be printed to the console with detailed results.
    unittest.main(verbosity=2)
