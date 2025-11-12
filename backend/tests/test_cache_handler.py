
import unittest
import time
import os
import sys

# Add the backend directory to the sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.cache_handler import CacheHandler

class TestCacheHandler(unittest.TestCase):

    def setUp(self):
        self.cache_handler = CacheHandler()
        self.cache_handler.cache_timeout = 1  # 1 second for testing expiration

    def test_cache_set_and_get(self):
        """
        Test Case UT-CA-001: Cache Set Operation
        Test Case UT-CA-002: Cache Get Operation
        """
        self.cache_handler.set("key1", "value1")
        self.assertEqual(self.cache_handler.get("key1"), "value1")

    def test_cache_expiration(self):
        """
        Test Case UT-CA-003: Cache Expiration
        """
        self.cache_handler.set("key2", "value2")
        time.sleep(1.1)
        self.assertIsNone(self.cache_handler.get("key2"))

    def tearDown(self):
        self.cache_handler.clear()

if __name__ == '__main__':
    unittest.main()
