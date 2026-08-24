from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection


def register_patient(full_name, email, password, phone=None):
    connection = get_db_connection()

    if connection is None:
        return False, "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    try:
        # Check whether email already exists
        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (email,)
        )

        if cursor.fetchone():
            return False, "Email already registered."

        # Secure password hashing
        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (full_name, email, password_hash, phone, role)
            VALUES (%s, %s, %s, %s, 'patient')
            """,
            (full_name, email, password_hash, phone)
        )

        user_id = cursor.lastrowid

        # Create patient profile
        cursor.execute(
            """
            INSERT INTO patients (user_id)
            VALUES (%s)
            """,
            (user_id,)
        )

        connection.commit()

        return True, "Patient registered successfully."

    except Exception as e:
        connection.rollback()
        return False, str(e)

    finally:
        cursor.close()
        connection.close()


def authenticate_user(email, password):
    connection = get_db_connection()

    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT user_id, full_name, email,
                   password_hash, role, is_active
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        if not user:
            return None

        if not user["is_active"]:
            return None

        if not check_password_hash(user["password_hash"], password):
            return None

        # Never return password hash to caller
        user.pop("password_hash", None)

        return user

    finally:
        cursor.close()
        connection.close()