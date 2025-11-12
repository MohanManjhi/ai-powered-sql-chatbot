
import unittest
from unittest.mock import patch
import os
import sys

# Add the backend directory to the sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils import llm_handler

class TestLlmInterface(unittest.TestCase):

    @patch('app.llm.gemini_sql_generator.generate_sql_from_nl')
    def test_query_generation_from_natural_language(self, mock_generate_sql):
        """
        Test Case UT-LLM-001: Query Generation from Natural Language
        """
        mock_generate_sql.return_value = "SELECT * FROM users"
        schema = {"users": ["id", "name", "email"]}
        user_query = "Show all users from database"

        sql_query = llm_handler.generate_sql_query(user_query, schema)

        self.assertEqual(sql_query, "SELECT * FROM users")
        mock_generate_sql.assert_called_once()

if __name__ == '__main__':
    unittest.main()
