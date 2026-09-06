from database import get_db_connection

connection = get_db_connection()

if connection is None:
    print("DATABASE CONNECTION FAILED")
else:
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT user_id, full_name, role FROM users WHERE role = %s",
        ("doctor",)
    )

    print(cursor.fetchall())

    cursor.close()
    connection.close()