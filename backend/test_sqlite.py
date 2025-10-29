import sqlite3
import os

def get_db_path():
    """Get the absolute path to the SQLite database"""
    return os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        'mydb.sqlite3'
    ))

def test_direct_sqlite():
    """Test direct SQLite connection"""
    db_path = get_db_path()
    print(f"Testing SQLite database at: {db_path}")
    print(f"File exists: {os.path.exists(db_path)}")
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Test tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        print("\nTables found:", [t[0] for t in tables])
        
        # Test books query
        c.execute("SELECT * FROM books")
        books = c.fetchall()
        print("\nBooks found:", len(books))
        for book in books:
            print(book)
            
        conn.close()
        print("\nSQLite test successful!")
        return True
        
    except Exception as e:
        print(f"\nSQLite test failed: {e}")
        return False

if __name__ == '__main__':
    test_direct_sqlite()