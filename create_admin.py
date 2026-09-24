from auth import create_admin


username = input("Enter admin username: ").strip()
password = input("Enter admin password: ").strip()

if not username or not password:
    print("Username and password are required.")
    exit()

try:
    create_admin(username, password)
    print("Admin account created successfully.")

except Exception as error:
    print("Unable to create admin.")
    print(error)