CREATE DATABASE IF NOT EXISTS students_db;
CREATE DATABASE IF NOT EXISTS departments_db;
CREATE DATABASE IF NOT EXISTS courses_db;
CREATE DATABASE IF NOT EXISTS faculty_db;
CREATE DATABASE IF NOT EXISTS college_admin;

\c students_db;

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INTEGER,
    major VARCHAR(50),
    enrollment_date DATE
);

INSERT INTO students (name, age, major, enrollment_date) VALUES
    ('John Doe', 20, 'Computer Science', '2023-09-01'),
    ('Jane Smith', 19, 'Mathematics', '2023-09-01'),
    ('Bob Johnson', 21, 'Physics', '2023-09-01');

\c departments_db;

CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    head_professor VARCHAR(100),
    building VARCHAR(50),
    budget DECIMAL(10,2)
);

INSERT INTO departments (name, head_professor, building, budget) VALUES
    ('Computer Science', 'Dr. Alan Turing', 'Tech Building', 1000000.00),
    ('Mathematics', 'Dr. Sophie Germain', 'Math Building', 800000.00),
    ('Physics', 'Dr. Richard Feynman', 'Science Building', 900000.00);

\c courses_db;

CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    department_id INTEGER,
    professor VARCHAR(100),
    credits INTEGER,
    semester VARCHAR(20)
);

INSERT INTO courses (name, department_id, professor, credits, semester) VALUES
    ('Introduction to Programming', 1, 'Dr. Ada Lovelace', 3, 'Fall 2023'),
    ('Calculus I', 2, 'Dr. Isaac Newton', 4, 'Fall 2023'),
    ('Quantum Mechanics', 3, 'Dr. Niels Bohr', 4, 'Fall 2023');

\c faculty_db;

CREATE TABLE IF NOT EXISTS faculty (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    department_id INTEGER,
    position VARCHAR(50),
    hire_date DATE,
    salary DECIMAL(10,2)
);

INSERT INTO faculty (name, department_id, position, hire_date, salary) VALUES
    ('Dr. Ada Lovelace', 1, 'Professor', '2020-01-01', 100000.00),
    ('Dr. Isaac Newton', 2, 'Professor', '2019-01-01', 105000.00),
    ('Dr. Niels Bohr', 3, 'Professor', '2018-01-01', 110000.00);

\c college_admin;

CREATE TABLE IF NOT EXISTS admin_staff (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    role VARCHAR(50),
    department VARCHAR(50),
    hire_date DATE
);

INSERT INTO admin_staff (name, role, department, hire_date) VALUES
    ('Sarah Connor', 'Dean', 'Administration', '2015-01-01'),
    ('James Cameron', 'Registrar', 'Student Records', '2016-01-01'),
    ('Ellen Ripley', 'Financial Aid Director', 'Financial Services', '2017-01-01');