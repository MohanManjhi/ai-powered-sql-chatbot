import unittest
import sqlite3
import os

class TestDataValidation(unittest.TestCase):

    def setUp(self):
        """Set up a connection to the database."""
        db_path = os.path.join(os.path.dirname(__file__), 'mydb.sqlite3')
        if not os.path.exists(db_path):
            self.skipTest(f"Database file not found at: {db_path}")
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        """Close the database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()

    def test_no_null_values_in_important_columns(self):
        """
        Test that there are no null values in the 'title' and 'author' columns of the 'books' table.
        """
        self.cursor.execute("SELECT COUNT(*) FROM books WHERE title IS NULL OR author IS NULL")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 0, "Found null values in 'title' or 'author' columns.")

    def test_year_column_is_integer(self):
        """
        Test that the 'year' column in the 'books' table contains only integer values.
        """
        self.cursor.execute("SELECT year FROM books")
        years = self.cursor.fetchall()
        for year in years:
            # The year can be None, so we only check the type if it's not None
            if year[0] is not None:
                self.assertIsInstance(year[0], int, f"Found non-integer value in 'year' column: {year[0]}")

    def test_no_duplicate_books(self):
        """
        Test that there are no duplicate books (based on title and author).
        """
        self.cursor.execute("SELECT title, author, COUNT(*) FROM books GROUP BY title, author HAVING COUNT(*) > 1")
        duplicates = self.cursor.fetchall()
        self.assertEqual(len(duplicates), 0, f"Found duplicate books: {duplicates}")


if __name__ == '__main__':
    print("--- Starting Data Validation Tests ---")
    unittest.main(verbosity=2)
