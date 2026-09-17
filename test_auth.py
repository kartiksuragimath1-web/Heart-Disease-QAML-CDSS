from auth import authenticate_user


print("=" * 50)
print("PATIENT LOGIN TEST")
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