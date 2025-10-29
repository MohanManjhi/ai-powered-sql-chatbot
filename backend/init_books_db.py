import sqlite3
import os

# Use the same database path as the application
db_path = 'mydb.sqlite3'  # Use current directory
print(f"Initializing database: {db_path}")

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Create books table
c.execute("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT,
    price REAL
)
""")

# Sample books data
sample_books = [
    (1, 'The Great Gatsby', 'F. Scott Fitzgerald', 1925, '978-0743273565', 9.99),
    (2, '1984', 'George Orwell', 1949, '978-0451524935', 12.99),
    (3, 'To Kill a Mockingbird', 'Harper Lee', 1960, '978-0446310789', 14.99),
    (4, 'Pride and Prejudice', 'Jane Austen', 1813, '978-0141439518', 11.99),
    (5, 'The Catcher in the Rye', 'J.D. Salinger', 1951, '978-0316769488', 10.99)
]

# Insert sample data (skip if exists)
c.execute("SELECT COUNT(*) FROM books")
if c.fetchone()[0] == 0:
    c.executemany('INSERT INTO books VALUES (?,?,?,?,?,?)', sample_books)
    print("Added sample books data")
else:
    print("Books table already has data")

conn.commit()

# Verify the data
c.execute('SELECT * FROM books')
books = c.fetchall()
print("\nBooks in database:")
for book in books:
    print(book)

conn.close()