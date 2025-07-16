import pyodbc

# Connection string settings
server = '.'  # Replace with your SQL Server name (e.g., localhost or server name)
database = 'People'  # Replace with your database name
username = 'sa'  # Replace with your SQL Server username
password = 'your_password'  # Replace with your SQL Server password
driver = '{ODBC Driver 17 for SQL Server}'  # Replace with your installed ODBC driver

# Check available ODBC drivers
try:
    print("Available ODBC drivers:")
    print(pyodbc.drivers())
except NameError:
    print("Error: pyodbc is not installed. Please install it using 'conda install pyodbc' or 'pip install pyodbc'.")
    exit()


try:
    conn = pyodbc.connect(f'DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes')
    print("Successfully connected to the database.")
    
    # Create a cursor for executing queries
    cursor = conn.cursor()

    # Create a sample table
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Students')
        CREATE TABLE Students (
            StudentID INT PRIMARY KEY IDENTITY(1,1),
            FirstName NVARCHAR(50),
            LastName NVARCHAR(50),
            Major NVARCHAR(50)
        )
    ''')
    
    conn.commit()
    print("Table 'Students' created successfully.")


#     cursor.execute("SELECT * FROM Students")
#     rows = cursor.fetchall()
#     for row in rows:
#        print(f"ID: {row.StudentID}, First Name: {row.FirstName}, Last Name: {row.LastName}, Major: {row.Major}")


    # Insert sample data
    cursor.execute('''
        INSERT INTO Students (FirstName, LastName, Major)
        VALUES (?, ?, ?)
    ''', ('Reza', 'Rezaei', 'Computer Engineering'))
    cursor.execute('''
        INSERT INTO Students (FirstName, LastName, Major)
        VALUES (?, ?, ?)
    ''', ('Maryam', 'Karimi', 'Data Science'))
    conn.commit()
    print("Data inserted successfully.")

    # Retrieve and display data
    cursor.execute('SELECT * FROM Students')
    rows = cursor.fetchall()
    print("\nData in 'Students' table:")
    for row in rows:
        print(f"ID: {row.StudentID}, First Name: {row.FirstName}, Last Name: {row.LastName}, Major: {row.Major}")

        
except pyodbc.Error as e:
    print(f"Error during query execution: {e}")
    print("Please verify connection details and ODBC driver installation.")
finally:
    # Close cursor and connection
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
        print("Database connection closed.")