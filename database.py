import os
import mysql.connector
from config import DB_CONFIG


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def add_student(student_id, name, email, department):

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        INSERT INTO students
        (student_id, name, email, department)
        VALUES (%s, %s, %s, %s)
    """

    values = (
        student_id,
        name,
        email,
        department
    )

    cursor.execute(query, values)

    connection.commit()

    cursor.close()
    connection.close()


def get_students():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            student_id,
            name,
            email,
            department,
            created_at
        FROM students
        ORDER BY id DESC
    """)

    students = cursor.fetchall()

    cursor.close()
    connection.close()

    return students

def get_attendance(search="", attendance_date=""):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            id,
            student_id,
            name,
            attendance_date,
            attendance_time,
            status
        FROM attendance
        WHERE 1=1
    """

    values = []


    # Search by Student ID or Name
    if search:

        query += """
            AND (
                student_id LIKE %s
                OR name LIKE %s
            )
        """

        search_value = f"%{search}%"

        values.extend([
            search_value,
            search_value
        ])


    # Filter by date
    if attendance_date:

        query += """
            AND attendance_date = %s
        """

        values.append(attendance_date)


    # Latest records first
    query += """
        ORDER BY attendance_date DESC,
                 attendance_time DESC
    """


    cursor.execute(
        query,
        values
    )


    attendance = cursor.fetchall()


    cursor.close()
    connection.close()


    return attendance

def get_student_by_id(student_id):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            student_id,
            name,
            email,
            department
        FROM students
        WHERE student_id = %s
    """, (student_id,))

    student = cursor.fetchone()

    cursor.close()
    connection.close()

    return student


def search_students(search=""):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            id,
            student_id,
            name,
            email,
            department,
            created_at
        FROM students
        WHERE student_id LIKE %s
           OR name LIKE %s
        ORDER BY id DESC
    """

    search_value = f"%{search}%"

    cursor.execute(
        query,
        (search_value, search_value)
    )

    students = cursor.fetchall()

    cursor.close()
    connection.close()

    return students


def delete_student(student_id):

    connection = None
    cursor = None

    try:

        # ------------------------------------------
        # DELETE FACE IMAGE FILES
        # ------------------------------------------

        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        dataset_dir = os.path.join(
            base_dir,
            "dataset"
        )

        deleted_face_files = 0

        if os.path.exists(dataset_dir):

            for filename in os.listdir(dataset_dir):

                if (
                    filename.startswith(
                        f"User.{student_id}."
                    )
                    and
                    filename.lower().endswith(".jpg")
                ):

                    filepath = os.path.join(
                        dataset_dir,
                        filename
                    )

                    try:

                        os.remove(filepath)

                        deleted_face_files += 1

                    except OSError as error:

                        print(
                            "Face file deletion error:",
                            error
                        )


        # ------------------------------------------
        # DELETE DATABASE INFORMATION
        # ------------------------------------------

        connection = get_connection()
        cursor = connection.cursor()

        # Delete attendance records
        cursor.execute(
            """
            DELETE FROM attendance
            WHERE student_id = %s
            """,
            (student_id,)
        )

        # Delete student login account
        cursor.execute(
            """
            DELETE FROM student_accounts
            WHERE student_id = %s
            """,
            (student_id,)
        )

        # Delete student information
        cursor.execute(
            """
            DELETE FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )

        deleted = cursor.rowcount > 0

        connection.commit()

        print(
            f"Deleted student: {student_id}"
        )

        print(
            f"Deleted face files: {deleted_face_files}"
        )

        return deleted

    except Exception:

        if connection:
            connection.rollback()

        raise

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()