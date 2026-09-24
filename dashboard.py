from datetime import date

from database import get_connection


def get_dashboard_stats():

    connection = get_connection()
    cursor = connection.cursor()

    # ==========================================
    # TOTAL STUDENTS
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
    """)

    total_students = cursor.fetchone()[0]


    # ==========================================
    # TODAY'S ATTENDANCE
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_date = %s
    """, (date.today(),))

    today_attendance = cursor.fetchone()[0]


    # ==========================================
    # TOTAL ATTENDANCE RECORDS
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
    """)

    total_attendance = cursor.fetchone()[0]


    # ==========================================
    # ATTENDANCE PERCENTAGE
    # ==========================================

    if total_students > 0:

        attendance_percentage = round(
            (today_attendance / total_students) * 100,
            1
        )

    else:

        attendance_percentage = 0


    cursor.close()
    connection.close()


    return {
        "total_students": total_students,
        "today_attendance": today_attendance,
        "total_attendance": total_attendance,
        "attendance_percentage": attendance_percentage
    }


# ==========================================
# DAILY ATTENDANCE DATA
# ==========================================

def get_daily_attendance():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            attendance_date,
            COUNT(*) AS total
        FROM attendance
        GROUP BY attendance_date
        ORDER BY attendance_date ASC
    """)

    records = cursor.fetchall()

    cursor.close()
    connection.close()

    return records


# ==========================================
# DEPARTMENT ATTENDANCE DATA
# ==========================================

def get_department_attendance():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COALESCE(s.department, 'Unknown') AS department,
            COUNT(a.id) AS total
        FROM attendance a
        LEFT JOIN students s
            ON a.student_id = s.student_id
        GROUP BY s.department
        ORDER BY total DESC
    """)

    records = cursor.fetchall()

    cursor.close()
    connection.close()

    return records
# ==========================================
# STUDENT ATTENDANCE STREAK
# ==========================================

def get_attendance_streak(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT DISTINCT attendance_date
        FROM attendance
        WHERE student_id = %s
        ORDER BY attendance_date DESC
    """, (student_id,))

    records = cursor.fetchall()

    cursor.close()
    connection.close()

    if not records:
        return 0

    dates = [
        record[0]
        for record in records
    ]

    streak = 0
    current_date = date.today()

    for attendance_date in dates:

        if attendance_date == current_date:
            streak += 1

            current_date = current_date.fromordinal(
                current_date.toordinal() - 1
            )

        elif attendance_date < current_date:
            break

    return streak