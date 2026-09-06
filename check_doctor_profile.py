from database import get_db_connection

connection = get_db_connection()

if connection is None:
    print("DATABASE CONNECTION FAILED")
else:
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            d.doctor_id,
            d.user_id,
            u.full_name,
            d.specialization,
            d.medical_license_number,
            d.verification_status
        FROM doctors d
        JOIN users u ON d.user_id = u.user_id
    """)

    print(cursor.fetchall())

    cursor.close()
    connection.close()