from database import get_db_connection

connection = get_db_connection()

if connection is None:
    print("DATABASE CONNECTION FAILED")
else:
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO doctors
        (
            user_id,
            specialization,
            medical_license_number,
            qualification,
            hospital_name,
            experience_years,
            verification_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        4,
        "Cardiology",
        "TEMP-LICENSE-004",
        "MBBS",
        "HeartQAML Demo Hospital",
        5,
        "VERIFIED"
    ))

    connection.commit()

    print("Doctor profile created successfully.")

    cursor.close()
    connection.close()