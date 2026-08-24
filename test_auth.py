from auth import register_patient, authenticate_user


print("=" * 50)
print("PATIENT REGISTRATION TEST")
print("=" * 50)

success, message = register_patient(
    full_name="Test Patient",
    email="testpatient@example.com",
    password="Test@12345",
    phone="9999999999"
)

print(message)


print("\n" + "=" * 50)
print("LOGIN TEST")
print("=" * 50)

user = authenticate_user(
    email="testpatient@example.com",
    password="Test@12345"
)

if user:
    print("LOGIN SUCCESSFUL")
    print("User ID :", user["user_id"])
    print("Name    :", user["full_name"])
    print("Role    :", user["role"])
else:
    print("LOGIN FAILED")