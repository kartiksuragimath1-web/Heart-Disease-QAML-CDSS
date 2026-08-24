from database import get_db_connection

connection = get_db_connection()

if connection and connection.is_connected():
    print("=" * 50)
    print("DATABASE CONNECTION SUCCESSFUL")
    print("=" * 50)

    cursor = connection.cursor()

    cursor.execute("SELECT DATABASE();")
    database = cursor.fetchone()

    print("Connected Database:", database[0])

    print("\nTables:")
    cursor.execute("SHOW TABLES;")

    tables = cursor.fetchall()

    for table in tables:
        print("-", table[0])

    cursor.close()
    connection.close()

    print("\nDatabase connection closed successfully.")

else:
    print("DATABASE CONNECTION FAILED")