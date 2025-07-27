import sqlite3

# Connect to SQLite database (it will be created if it doesn't exist)
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# --- Create Tables ---
# Drop tables if they exist to start fresh
cursor.execute("DROP TABLE IF EXISTS employees;")
cursor.execute("DROP TABLE IF EXISTS departments;")
cursor.execute("DROP TABLE IF EXISTS salaries;")

# Create departments table
cursor.execute("""
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
""")

# Create employees table
cursor.execute("""
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    hire_date DATE NOT NULL,
    department_id INTEGER,
    FOREIGN KEY (department_id) REFERENCES departments (id)
);
""")

# Create salaries table
cursor.execute("""
CREATE TABLE salaries (
    employee_id INTEGER,
    amount INTEGER NOT NULL,
    date DATE NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees (id)
);
""")

# --- Insert Sample Data ---
# Insert departments
cursor.execute("INSERT INTO departments (name) VALUES ('Engineering'), ('Human Resources'), ('Sales');")

# Insert employees
cursor.execute("""
INSERT INTO employees (name, hire_date, department_id) VALUES
('Alice', '2020-01-15', 1),
('Bob', '2021-03-22', 1),
('Charlie', '2019-11-01', 2),
('David', '2022-05-10', 3),
('Eve', '2021-07-30', 3);
""")

# Insert salaries
cursor.execute("""
INSERT INTO salaries (employee_id, amount, date) VALUES
(1, 90000, '2024-01-01'),
(2, 80000, '2024-01-01'),
(3, 75000, '2024-01-01'),
(4, 120000, '2024-01-01'),
(5, 125000, '2024-01-01');
""")

# Commit changes and close connection
conn.commit()
conn.close()

print("Database `database.db` created and populated with sample data. ✅")