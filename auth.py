from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection


def create_admin(username, password):
    connection = get_connection()
    cursor = connection.cursor()

    password_hash = generate_password_hash(password)

    cursor.execute(
        """
        INSERT INTO admins (username, password_hash)
        VALUES (%s, %s)
        """,
        (username, password_hash)
    )

    connection.commit()

    cursor.close()
    connection.close()


def verify_admin(username, password):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT username, password_hash
        FROM admins
        WHERE username = %s
        """,
        (username,)
    )

    admin = cursor.fetchone()

    cursor.close()
    connection.close()

    if admin and check_password_hash(
        admin["password_hash"],
        password
    ):
        return admin

    return None
def verify_student(student_id, password):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            student_id,
            password_hash
        FROM student_accounts
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    cursor.close()
    connection.close()

    if student and check_password_hash(
        student["password_hash"],
        password
    ):
        return student

    return None