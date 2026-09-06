from database import get_db_connection
from werkzeug.security import generate_password_hash

connection = get_db_connection()

cursor = connection.cursor()

new_password = "Kartik@123"

cursor.execute("""
    UPDATE users
    SET password_hash = %s
    WHERE user_id = 4
      AND role = 'doctor'
""", (generate_password_hash(new_password),))

connection.commit()

print("Password reset successfully.")
print("Email: kartik@gmail.com")
print("Password: Kartik@123")

cursor.close()
connection.close()