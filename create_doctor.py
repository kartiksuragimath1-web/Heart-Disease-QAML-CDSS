from database import get_db_connection
from werkzeug.security import generate_password_hash

full_name = "John Smith"
email = "doctor@heartqaml.com"
password = "Doctor@123"

password_hash = generate_password_hash(password)

connection = get_db_connection()

if connection is None:
    print("Database connection failed.")
    exit()

cursor = connection.cursor()

try:
    cursor.execute(
        """
        INSERT INTO users
        (
            full_name,
            email,
            password_hash,
            phone,
            role,
            is_active
        )
        VALUES
        (%s, %s, %s, %s, %s, %s)
        """,
        (
            full_name,
            email,
            password_hash,
            "9876543210",
            "doctor",
            1
        )
    )

    connection.commit()

    print("Doctor account created successfully!")
    print("Email:", email)
    print("Password:", password)

except Exception as e:
    connection.rollback()
    print("Error:", e)

finally:
    cursor.close()
    connection.close()