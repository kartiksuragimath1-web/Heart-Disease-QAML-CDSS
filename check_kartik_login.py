from database import get_db_connection

connection = get_db_connection()

cursor = connection.cursor(dictionary=True)

cursor.execute("""
    SELECT user_id, full_name, email, role, is_active
    FROM users
    WHERE user_id = 4
""")

print(cursor.fetchone())

cursor.close()
connection.close()