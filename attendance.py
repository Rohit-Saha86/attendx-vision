from datetime import datetime

from database import get_connection


def mark_attendance(student_id, name):

    connection = get_connection()
    cursor = connection.cursor()

    today = datetime.now().date()
    current_time = datetime.now().time()

    # Check today's attendance
    cursor.execute("""
        SELECT id
        FROM attendance
        WHERE student_id = %s
        AND attendance_date = %s
    """, (student_id, today))

    existing_record = cursor.fetchone()

    if existing_record:

        cursor.close()
        connection.close()

        print(
            f"Attendance already marked for "
            f"{student_id} today."
        )

        return False

    # Insert attendance
    cursor.execute("""
        INSERT INTO attendance
        (
            student_id,
            name,
            attendance_date,
            attendance_time,
            status
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        student_id,
        name,
        today,
        current_time,
        "Present"
    ))

    connection.commit()

    cursor.close()
    connection.close()

    print(
        f"Attendance marked for "
        f"{name} ({student_id})."
    )

    return True