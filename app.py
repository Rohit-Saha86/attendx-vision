from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
    session
)

from functools import wraps

from auth import verify_admin

from mysql.connector import Error

import subprocess
import sys
import json
import pandas as pd
import os

from dotenv import load_dotenv

from database import (
    get_connection,
    add_student,
    get_students,
    get_attendance,
    get_student_by_id,
    search_students,
    delete_student
)

from dashboard import (
    get_dashboard_stats,
    get_daily_attendance,
    get_department_attendance,
    get_attendance_streak
)


# ==========================================
# ENVIRONMENT
# ==========================================

load_dotenv()


# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY"
)


# ==========================================
# LOGIN REQUIRED
# ==========================================

def login_required(route_function):

    @wraps(route_function)
    def wrapper(*args, **kwargs):

        if "admin_username" not in session:

            flash(
                "Please login to continue.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        return route_function(
            *args,
            **kwargs
        )

    return wrapper


# ==========================================
# LOGIN
# ==========================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if "admin_username" in session:

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:

            flash(
                "Username and password are required.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        admin = verify_admin(
            username,
            password
        )

        if admin:

            session["admin_username"] = (
                admin["username"]
            )

            flash(
                "Login successful.",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid username or password.",
            "error"
        )

    return render_template(
        "login.html"
    )


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ==========================================
# HOME
# ==========================================

@app.route("/")
@login_required
def home():

    return render_template(
        "index.html"
    )


# ==========================================
# REGISTER STUDENT
# ==========================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
@login_required
def register():

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        department = request.form.get(
            "department",
            ""
        ).strip()

        # ------------------------------
        # Validation
        # ------------------------------

        if len(student_id) < 3:

            flash(
                "Student ID must contain at least 3 characters.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if not name:

            flash(
                "Student name is required.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # ------------------------------
        # Add student
        # ------------------------------

        try:

            add_student(
                student_id,
                name,
                email,
                department
            )

            flash(
                "Student registered successfully.",
                "success"
            )

            return redirect(
                url_for("students")
            )

        except Error as error:

            if error.errno == 1062:

                flash(
                    "Student ID already exists.",
                    "error"
                )

                return redirect(
                    url_for("register")
                )

            flash(
                "Database error occurred.",
                "error"
            )

            return redirect(
                url_for("register")
            )

    return render_template(
        "register.html"
    )


# ==========================================
# STUDENTS
# ==========================================

@app.route("/students")
@login_required
def students():

    search = request.args.get(
        "search",
        ""
    ).strip()

    if search:

        all_students = search_students(
            search
        )

    else:

        all_students = get_students()

    return render_template(
        "students.html",
        students=all_students,
        search=search
    )


# ==========================================
# DELETE STUDENT
# ==========================================

@app.route(
    "/delete-student",
    methods=["POST"]
)
@login_required
def delete_student_route():

    student_id = request.form.get(
        "student_id",
        ""
    ).strip()

    if not student_id:

        flash(
            "Student ID is missing.",
            "error"
        )

        return redirect(
            url_for("students")
        )

    try:

        deleted = delete_student(
            student_id
        )

        if deleted:

            flash(
                "Student deleted successfully.",
                "success"
            )

        else:

            flash(
                "Student not found.",
                "error"
            )

    except Error:

        flash(
            "Unable to delete student.",
            "error"
        )

    return redirect(
        url_for("students")
    )


# ==========================================
# ATTENDANCE
# ==========================================

@app.route("/attendance")
@login_required
def attendance():

    search = request.args.get(
        "search",
        ""
    ).strip()

    attendance_date = request.args.get(
        "date",
        ""
    ).strip()

    all_attendance = get_attendance(
        search,
        attendance_date
    )

    return render_template(
        "attendance.html",
        attendance=all_attendance,
        search=search,
        attendance_date=attendance_date
    )
# ==========================================
# RECOGNITION PAGE
# ==========================================

@app.route("/recognition")
@login_required
def recognition():

    return render_template(
        "recognition.html"
    )



# ==========================================
# START FACE RECOGNITION
# ==========================================

@app.route("/start-recognition")
@login_required
def start_recognition():

    try:

        subprocess.Popen(
            [
                sys.executable,
                "recognize_face.py"
            ]
        )

        flash(
            "Face recognition started. Check your webcam.",
            "success"
        )

    except Exception:

        flash(
            "Unable to start face recognition.",
            "error"
        )

    return redirect(
        url_for("home")
    )


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    stats = get_dashboard_stats()

    daily_attendance = get_daily_attendance()

    department_attendance = (
        get_department_attendance()
    )

    daily_labels = [
        str(
            record["attendance_date"]
        )
        for record in daily_attendance
    ]

    daily_values = [
        record["total"]
        for record in daily_attendance
    ]

    department_labels = [
        record["department"]
        for record in department_attendance
    ]

    department_values = [
        record["total"]
        for record in department_attendance
    ]

    return render_template(
        "dashboard.html",
        stats=stats,
        daily_labels=daily_labels,
        daily_values=daily_values,
        department_labels=department_labels,
        department_values=department_values
    )


# ==========================================
# ATTENDANCE REPORTS
# ==========================================

@app.route("/reports")
@login_required
def reports():

    search = request.args.get(
        "search",
        ""
    ).strip()

    attendance_date = request.args.get(
        "date",
        ""
    ).strip()

    records = get_attendance(
        search,
        attendance_date
    )

    total_records = len(records)

    present_count = sum(
        1
        for record in records
        if record["status"] == "Present"
    )

    return render_template(
        "reports.html",
        attendance=records,
        search=search,
        attendance_date=attendance_date,
        total_records=total_records,
        present_count=present_count
    )


# ==========================================
# EXPORT ATTENDANCE CSV
# ==========================================

@app.route("/export-attendance")
@login_required
def export_attendance():

    search = request.args.get(
        "search",
        ""
    ).strip()

    attendance_date = request.args.get(
        "date",
        ""
    ).strip()

    records = get_attendance(
        search,
        attendance_date
    )

    if not records:

        flash(
            "No attendance records available for export.",
            "error"
        )

        return redirect(
            url_for("reports")
        )

    data = []

    for record in records:

        data.append(
            {
                "ID": record["id"],
                "Student ID": record["student_id"],
                "Name": record["name"],
                "Date": record["attendance_date"],
                "Time": record["attendance_time"],
                "Status": record["status"]
            }
        )

    dataframe = pd.DataFrame(
        data
    )

    csv_data = dataframe.to_csv(
        index=False
    )

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=attendance_report.csv"
        }
    )


# ==========================================
# ATTENDANCE COUNT
# ==========================================

@app.route("/attendance-count")
@login_required
def attendance_count():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            """
        )

        total_attendance = (
            cursor.fetchone()[0]
        )

        return {
            "count": total_attendance
        }

    except Error:

        return {
            "count": 0
        }

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# ATTENDANCE STREAK
# ==========================================

@app.route("/attendance-streak")
@login_required
def attendance_streak():

    student_id = request.args.get(
        "student_id"
    )

    if not student_id:

        return {
            "streak": 0,
            "error": "student_id is required"
        }, 400

    try:

        streak = get_attendance_streak(
            student_id
        )

        return {
            "streak": streak
        }

    except Exception:

        return {
            "streak": 0
        }


# ==========================================
# RECOGNITION STATUS
# ==========================================

@app.route("/recognition-status")
@login_required
def recognition_status():

    try:

        with open(
            "recognition_status.json",
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        return data

    except Exception:

        return {
            "status": "waiting",
            "student_id": "",
            "name": "",
            "attendance_marked": False
        }


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )