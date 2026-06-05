import sqlite3

def create_sample_database():
    # Connect to database (will create student.db if it doesn't exist)
    connection = sqlite3.connect("student.db")
    cursor = connection.cursor()

    # Drop tables if they already exist
    cursor.execute("DROP TABLE IF EXISTS ENROLLMENTS")
    cursor.execute("DROP TABLE IF EXISTS COURSES")
    cursor.execute("DROP TABLE IF EXISTS STUDENTS")

    # Create Students table
    cursor.execute("""
    CREATE TABLE STUDENTS (
        ROLL_NO INTEGER PRIMARY KEY,
        NAME TEXT NOT NULL,
        CLASS TEXT NOT NULL,
        SECTION TEXT NOT NULL,
        GPA REAL CHECK(GPA >= 0.0 AND GPA <= 4.0)
    )
    """)

    # Create Courses table
    cursor.execute("""
    CREATE TABLE COURSES (
        COURSE_ID TEXT PRIMARY KEY,
        COURSE_NAME TEXT NOT NULL,
        CREDITS INTEGER NOT NULL,
        INSTRUCTOR TEXT NOT NULL
    )
    """)

    # Create Enrollments table (links Students and Courses)
    cursor.execute("""
    CREATE TABLE ENROLLMENTS (
        ROLL_NO INTEGER,
        COURSE_ID TEXT,
        SEMESTER TEXT NOT NULL,
        GRADE TEXT CHECK(GRADE IN ('A', 'B', 'C', 'D', 'F')),
        PRIMARY KEY (ROLL_NO, COURSE_ID),
        FOREIGN KEY (ROLL_NO) REFERENCES STUDENTS(ROLL_NO),
        FOREIGN KEY (COURSE_ID) REFERENCES COURSES(COURSE_ID)
    )
    """)

    # Insert sample student records
    students_data = [
        (101, 'Aarav Sharma', '12th', 'A', 3.8),
        (102, 'Priya Patel', '12th', 'B', 3.9),
        (103, 'Rohan Das', '11th', 'A', 3.2),
        (104, 'Ananya Iyer', '12th', 'A', 3.7),
        (105, 'Kabir Mehta', '11th', 'B', 2.8),
        (106, 'Sneha Reddy', '12th', 'B', 3.95),
        (107, 'Arjun Verma', '11th', 'A', 3.5),
        (108, 'Diya Kapoor', '12th', 'C', 3.1)
    ]
    cursor.executemany("INSERT INTO STUDENTS VALUES (?, ?, ?, ?, ?)", students_data)

    # Insert sample course records
    courses_data = [
        ('CS101', 'Introduction to Computer Science', 4, 'Dr. Amit Sen'),
        ('MATH201', 'Calculus II', 4, 'Prof. Sarah Thomas'),
        ('PHY101', 'General Physics', 3, 'Dr. Raj Singh'),
        ('ENG102', 'English Literature', 3, 'Ms. Elena Gilbert'),
        ('CHEM101', 'General Chemistry', 4, 'Dr. Homi Bhabha')
    ]
    cursor.executemany("INSERT INTO COURSES VALUES (?, ?, ?, ?)", courses_data)

    # Insert sample enrollment records
    enrollments_data = [
        (101, 'CS101', 'Fall 2025', 'A'),
        (101, 'MATH201', 'Fall 2025', 'B'),
        (102, 'CS101', 'Fall 2025', 'A'),
        (102, 'PHY101', 'Fall 2025', 'A'),
        (103, 'MATH201', 'Fall 2025', 'C'),
        (103, 'ENG102', 'Fall 2025', 'B'),
        (104, 'CS101', 'Fall 2025', 'B'),
        (104, 'CHEM101', 'Fall 2025', 'B'),
        (105, 'ENG102', 'Fall 2025', 'D'),
        (105, 'PHY101', 'Fall 2025', 'C'),
        (106, 'CS101', 'Fall 2025', 'A'),
        (106, 'MATH201', 'Fall 2025', 'A'),
        (107, 'PHY101', 'Fall 2025', 'B'),
        (107, 'CHEM101', 'Fall 2025', 'A'),
        (108, 'CS101', 'Fall 2025', 'C'),
        (108, 'ENG102', 'Fall 2025', 'B')
    ]
    cursor.executemany("INSERT INTO ENROLLMENTS VALUES (?, ?, ?, ?)", enrollments_data)

    # Commit changes and close
    connection.commit()
    
    # Verify by printing tables
    print("Database 'student.db' created successfully with the following tables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(f" - {table[0]}")
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"   Columns: {', '.join(columns)}")
        
    connection.close()

if __name__ == "__main__":
    create_sample_database()