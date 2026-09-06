from database import get_db_connection

connection = get_db_connection()

if connection is None:
    print("DATABASE CONNECTION FAILED")
else:
    cursor = connection.cursor(dictionary=True)

    cursor.execute("DESCRIBE doctors")

    for row in cursor.fetchall():
        print(row)

    cursor.close()
    connection.close()