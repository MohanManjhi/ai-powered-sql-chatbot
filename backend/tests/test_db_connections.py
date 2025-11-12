
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine
import os

# Add the backend directory to the sys.path to allow for absolute imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import db

class TestDBConnections(unittest.TestCase):

    @patch.dict(os.environ, {"DATABASE_URL_1": "sqlite:///test.db"})
    def test_sqlite_connection_creation(self):
        """
        Test Case UT-DB-001: SQLite Connection Creation
        """
        # Reload the db module to pick up the patched environment variable
        import importlib
        importlib.reload(db)

        self.assertIn("db1", db.engines)
        engine = db.engines["db1"]
        self.assertEqual(engine.url.drivername, "sqlite")
        self.assertEqual(engine.url.database, "test.db")

    @patch.dict(os.environ, {"DATABASE_URL_2": "postgresql://user:password@host:5432/testdb"})
    @patch('app.db.create_engine')
    def test_postgresql_connection_with_pooling(self, mock_create_engine):
        """
        Test Case UT-DB-002: PostgreSQL Connection with Pooling
        """
        import importlib
        importlib.reload(db)

        self.assertIn("db2", db.engines)
        mock_create_engine.assert_called_with(
            "postgresql://user:password@host:5432/testdb",
            pool_size=10,
            max_overflow=20,
            pool_timeout=30
        )

    @patch.dict(os.environ, {"DATABASE_URL_3": "postgresql://invalid_user:invalid_password@host:5432/testdb"})
    def test_connection_failure_handling(self):
        """
        Test Case UT-DB-004: Connection Failure Handling
        """
        import importlib
        importlib.reload(db)
        
        # The engine creation itself does not raise an error for bad credentials, 
        # but the connection will.
        with self.assertRaises(Exception):
            db.engines["db3"].connect()

if __name__ == '__main__':
    unittest.main()
