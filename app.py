from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
    session,
    jsonify
)

from werkzeug.security import generate_password_hash

from functools import wraps

from auth import verify_admin, verify_student

from database import get_connection

from mysql.connector import Error

import re
import secrets
import hashlib
import time
import subprocess
import sys
import os
import json
import time
import pandas as pd
import cv2
import numpy as np
from attendance import mark_attendance

from database import (
    add_student,
    get_students,
    get_attendance,
    search_students,
    delete_student
)

from dashboard import (
    get_dashboard_stats,
    get_daily_attendance,
    get_department_attendance
)

app = Flask(__name__)

app.secret_key = "face-attendance-local-key"

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

        return route_function(*args, **kwargs)

    return wrapper


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "admin_username" in session:
        return redirect(url_for("dashboard"))

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

    return render_template("login.html")

@app.route("/admin-register", methods=["GET", "POST"])
def admin_register():

    # Registration code for creating admin accounts

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Check required fields
        if (
            not username
            or not phone
            or not password
            or not confirm_password
        ):
            flash(
                "Please fill in all fields.",
                "error"
            )
            return render_template(
                "admin_register.html"
            )

        # Check phone number
        if not re.fullmatch(r"\d{10}", phone):
            flash(
                "Phone number must contain exactly 10 digits.",
                "error"
            )
            return render_template(
                "admin_register.html"
            )

        # Check password length
        if len(password) < 8 or len(password) > 11:
            flash(
                "Password must be between 8 and 11 characters.",
                "error"
            )
            return render_template(
                "admin_register.html"
            )

        # Check for alphabet
        if not re.search(r"[A-Za-z]", password):
            flash(
                "Password must contain at least one alphabet.",
                "error"
            )
            return render_template(
                "admin_register.html"
            )

        # Check for number
        if not re.search(r"\d", password):
            flash(
                "Password must contain at least one number.",
                "error"
            )
            return render_template(
                "admin_register.html"
            )

        # Check for special character
        if not re.search(r"[^A-Za-z0-9]", password):
            flash(
                "Password must contain at least one special character.",
                "error"
            )
            return render_template(
                "admin_register.html"
            )

        # Check password confirmation
        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "error"
            )
            return render_template(
                "admin_register.html"
            )

        connection = get_connection()
        cursor = connection.cursor(
            dictionary=True
        )

        # Check whether username already exists
        cursor.execute(
            """
            SELECT username
            FROM admins
            WHERE username = %s
            """,
            (username,)
        )

        existing_admin = cursor.fetchone()

        if existing_admin:
            cursor.close()
            connection.close()

            flash(
                "This admin username already exists.",
                "error"
            )

            return render_template(
                "admin_register.html"
            )

        # Check whether phone already exists
        cursor.execute(
            """
            SELECT username
            FROM admins
            WHERE phone = %s
            """,
            (phone,)
        )

        existing_phone = cursor.fetchone()

        if existing_phone:
            cursor.close()
            connection.close()

            flash(
                "This phone number is already registered.",
                "error"
            )

            return render_template(
                "admin_register.html"
            )

        # Hash password
        password_hash = generate_password_hash(
            password
        )

        # Create admin account
        cursor.execute(
            """
            INSERT INTO admins
            (
                username,
                phone,
                password_hash
            )
            VALUES (%s, %s, %s)
            """,
            (
                username,
                phone,
                password_hash
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            "Admin account created successfully. Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "admin_register.html"
    )

# ==========================================
# ADMIN FORGOT PASSWORD - OTP RESET
# ==========================================

@app.route("/admin-forgot-password", methods=["GET", "POST"])
def admin_forgot_password():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        # Validate fields
        if not username or not phone:
            flash(
                "Username and phone number are required.",
                "error"
            )

            return redirect(
                url_for("admin_forgot_password")
            )

        # Validate phone
        if not re.fullmatch(r"\d{10}", phone):
            flash(
                "Phone number must contain exactly 10 digits.",
                "error"
            )

            return redirect(
                url_for("admin_forgot_password")
            )

        connection = get_connection()
        cursor = connection.cursor(
            dictionary=True
        )

        # Verify username + phone
        cursor.execute(
            """
            SELECT username, phone
            FROM admins
            WHERE username = %s
              AND phone = %s
            """,
            (
                username,
                phone
            )
        )

        admin = cursor.fetchone()

        cursor.close()
        connection.close()

        if not admin:
            flash(
                "Username and phone number do not match.",
                "error"
            )

            return redirect(
                url_for("admin_forgot_password")
            )

        # Generate secure 6-digit OTP
        otp = str(
            secrets.randbelow(900000) + 100000
        )

        # Store only OTP hash
        otp_hash = hashlib.sha256(
            otp.encode()
        ).hexdigest()

        # OTP valid for 5 minutes
        expiry = time.time() + 300

        session["admin_reset"] = {
            "username": username,
            "phone": phone,
            "otp_hash": otp_hash,
            "expires": expiry,
            "attempts": 0
        }

        # DEVELOPMENT ONLY
        # Later this will be replaced with real SMS delivery.
        print("")
        print("=" * 50)
        print("ATTENDX VISION - ADMIN PASSWORD RESET")
        print(f"Username : {username}")
        print(f"Phone    : ******{phone[-4:]}")
        print(f"OTP      : {otp}")
        print("Valid for: 5 minutes")
        print("=" * 50)
        print("")

        return redirect(
            url_for("admin_verify_otp")
        )

    return render_template(
        "admin_forgot_password.html"
    )


# ==========================================
# ADMIN VERIFY OTP
# ==========================================

@app.route(
    "/admin-verify-otp",
    methods=["GET", "POST"]
)
def admin_verify_otp():

    reset_data = session.get(
        "admin_reset"
    )

    if not reset_data:
        flash(
            "Please request a new OTP.",
            "error"
        )

        return redirect(
            url_for("admin_forgot_password")
        )

    # Check OTP expiry
    if time.time() > reset_data["expires"]:

        session.pop(
            "admin_reset",
            None
        )

        flash(
            "OTP has expired. Please request a new OTP.",
            "error"
        )

        return redirect(
            url_for("admin_forgot_password")
        )

    if request.method == "POST":

        entered_otp = request.form.get(
            "otp",
            ""
        ).strip()

        # OTP must be exactly 6 digits
        if not re.fullmatch(
            r"\d{6}",
            entered_otp
        ):
            flash(
                "Enter a valid 6-digit OTP.",
                "error"
            )

            return redirect(
                url_for("admin_verify_otp")
            )

        # Limit incorrect attempts
        if reset_data["attempts"] >= 5:

            session.pop(
                "admin_reset",
                None
            )

            flash(
                "Too many incorrect attempts. Please request a new OTP.",
                "error"
            )

            return redirect(
                url_for("admin_forgot_password")
            )

        entered_hash = hashlib.sha256(
            entered_otp.encode()
        ).hexdigest()

        if not secrets.compare_digest(
            entered_hash,
            reset_data["otp_hash"]
        ):

            reset_data["attempts"] += 1

            session["admin_reset"] = reset_data

            flash(
                "Incorrect OTP.",
                "error"
            )

            return redirect(
                url_for("admin_verify_otp")
            )

        # OTP verified
        reset_data["verified"] = True

        session["admin_reset"] = reset_data

        return redirect(
            url_for("admin_reset_password")
        )

    return render_template(
        "admin_verify_otp.html",
        phone=reset_data["phone"]
    )


# ==========================================
# ADMIN RESET PASSWORD
# ==========================================

@app.route(
    "/admin-reset-password",
    methods=["GET", "POST"]
)
def admin_reset_password():

    reset_data = session.get(
        "admin_reset"
    )

    if not reset_data:
        flash(
            "Please start the password reset process again.",
            "error"
        )

        return redirect(
            url_for("admin_forgot_password")
        )

    if not reset_data.get("verified"):
        flash(
            "Please verify the OTP first.",
            "error"
        )

        return redirect(
            url_for("admin_verify_otp")
        )

    if time.time() > reset_data["expires"]:

        session.pop(
            "admin_reset",
            None
        )

        flash(
            "Password reset session expired.",
            "error"
        )

        return redirect(
            url_for("admin_forgot_password")
        )

    if request.method == "POST":

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Password length
        if len(new_password) < 8 or len(new_password) > 11:

            flash(
                "Password must be between 8 and 11 characters.",
                "error"
            )

            return redirect(
                url_for("admin_reset_password")
            )

        # Alphabet
        if not re.search(
            r"[A-Za-z]",
            new_password
        ):

            flash(
                "Password must contain at least one alphabet.",
                "error"
            )

            return redirect(
                url_for("admin_reset_password")
            )

        # Number
        if not re.search(
            r"\d",
            new_password
        ):

            flash(
                "Password must contain at least one number.",
                "error"
            )

            return redirect(
                url_for("admin_reset_password")
            )

        # Special character
        if not re.search(
            r"[^A-Za-z0-9]",
            new_password
        ):

            flash(
                "Password must contain at least one special character.",
                "error"
            )

            return redirect(
                url_for("admin_reset_password")
            )

        # Confirm password
        if new_password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("admin_reset_password")
            )

        password_hash = generate_password_hash(
            new_password
        )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE admins
            SET password_hash = %s
            WHERE username = %s
              AND phone = %s
            """,
            (
                password_hash,
                reset_data["username"],
                reset_data["phone"]
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        # Remove reset data
        session.pop(
            "admin_reset",
            None
        )

        flash(
            "Password reset successfully. Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "admin_reset_password.html"
    )

# ==========================================
# STUDENT LOGIN
# ==========================================

@app.route("/student-login", methods=["GET", "POST"])
def student_login():

    # If already logged in, go directly to dashboard
    if "student_id" in session:
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        # Validate fields
        if not student_id or not password:
            flash(
                "Student ID and password are required.",
                "error"
            )
            return redirect(
                url_for("student_login")
            )

        # Verify student account
        student = verify_student(
            student_id,
            password
        )

        if student:

            # Create student session
            session.clear()

            session["student_id"] = student["student_id"]

            flash(
                "Student login successful.",
                "success"
            )

            # IMPORTANT:
            # Always open the new Student Dashboard
            return redirect(
                url_for("student_dashboard")
            )

        flash(
            "Invalid Student ID or password.",
            "error"
        )

    return render_template(
        "student_login.html"
    )

# =========================================================
# STUDENT FORGOT PASSWORD - SEND OTP
# =========================================================

@app.route("/student-forgot-password", methods=["GET", "POST"])
def student_forgot_password():

    if request.method == "POST":

        student_id = request.form.get("student_id", "").strip()
        phone = request.form.get("phone", "").strip()

        if not student_id or not phone:
            flash("Student ID and phone number are required.", "error")
            return redirect(url_for("student_forgot_password"))

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT s.student_id, s.name, s.phone
            FROM students s
            INNER JOIN student_accounts sa
                ON s.student_id = sa.student_id
            WHERE s.student_id = %s
              AND s.phone = %s
            """,
            (student_id, phone)
        )

        student = cursor.fetchone()

        cursor.close()
        connection.close()

        if not student:
            flash(
                "Student ID and registered phone number do not match.",
                "error"
            )
            return redirect(url_for("student_forgot_password"))

        otp = str(secrets.randbelow(900000) + 100000)

        otp_hash = hashlib.sha256(
            otp.encode()
        ).hexdigest()

        session["student_reset_id"] = student["student_id"]
        session["student_reset_otp_hash"] = otp_hash
        session["student_reset_otp_expiry"] = time.time() + 300
        session["student_reset_otp_attempts"] = 0
        session["student_reset_verified"] = False

        print("\n====================================")
        print("STUDENT PASSWORD RESET OTP")
        print("Student ID:", student["student_id"])
        print("OTP:", otp)
        print("Expires in: 5 minutes")
        print("====================================\n")

        return redirect(
            url_for("student_verify_otp")
        )

    return render_template(
        "student_forgot_password.html"
    )

# =========================================================
# STUDENT VERIFY OTP
# =========================================================

@app.route("/student-verify-otp", methods=["GET", "POST"])
def student_verify_otp():

    student_id = session.get("student_reset_id")
    otp_hash = session.get("student_reset_otp_hash")
    expiry = session.get("student_reset_otp_expiry")

    if not student_id or not otp_hash or not expiry:
        flash(
            "Password reset session expired. Please request a new OTP.",
            "error"
        )
        return redirect(
            url_for("student_forgot_password")
        )

    if time.time() > expiry:

        session.pop("student_reset_otp_hash", None)
        session.pop("student_reset_otp_expiry", None)
        session.pop("student_reset_otp_attempts", None)

        flash(
            "OTP has expired. Please request a new OTP.",
            "error"
        )

        return redirect(
            url_for("student_forgot_password")
        )

    if request.method == "POST":

        entered_otp = request.form.get(
            "otp",
            ""
        ).strip()

        attempts = session.get(
            "student_reset_otp_attempts",
            0
        )

        if attempts >= 5:

            session.pop(
                "student_reset_otp_hash",
                None
            )

            session.pop(
                "student_reset_otp_expiry",
                None
            )

            session.pop(
                "student_reset_otp_attempts",
                None
            )

            flash(
                "Too many incorrect OTP attempts. Please request a new OTP.",
                "error"
            )

            return redirect(
                url_for("student_forgot_password")
            )

        entered_hash = hashlib.sha256(
            entered_otp.encode()
        ).hexdigest()

        if secrets.compare_digest(
            entered_hash,
            otp_hash
        ):

            session["student_reset_verified"] = True

            session.pop(
                "student_reset_otp_hash",
                None
            )

            session.pop(
                "student_reset_otp_expiry",
                None
            )

            session.pop(
                "student_reset_otp_attempts",
                None
            )

            flash(
                "OTP verified successfully.",
                "success"
            )

            return redirect(
                url_for("student_reset_password")
            )

        session["student_reset_otp_attempts"] = (
            attempts + 1
        )

        remaining = 4 - attempts

        flash(
            f"Invalid OTP. {remaining} attempts remaining.",
            "error"
        )

    return render_template(
        "student_verify_otp.html"
    )

# =========================================================
# STUDENT RESET PASSWORD
# =========================================================

@app.route("/student-reset-password", methods=["GET", "POST"])
def student_reset_password():

    student_id = session.get("student_reset_id")
    verified = session.get("student_reset_verified")

    if not student_id or not verified:
        flash(
            "Please verify your OTP first.",
            "error"
        )
        return redirect(
            url_for("student_forgot_password")
        )

    if request.method == "POST":

        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if len(password) < 8 or len(password) > 11:
            flash(
                "Password must be 8 to 11 characters long.",
                "error"
            )
            return redirect(
                url_for("student_reset_password")
            )

        if not any(char.isalpha() for char in password):
            flash(
                "Password must contain at least one letter.",
                "error"
            )
            return redirect(
                url_for("student_reset_password")
            )

        if not any(char.isdigit() for char in password):
            flash(
                "Password must contain at least one number.",
                "error"
            )
            return redirect(
                url_for("student_reset_password")
            )

        if not any(
            not char.isalnum()
            for char in password
        ):
            flash(
                "Password must contain at least one special character.",
                "error"
            )
            return redirect(
                url_for("student_reset_password")
            )

        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "error"
            )
            return redirect(
                url_for("student_reset_password")
            )

        password_hash = generate_password_hash(
            password
        )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE student_accounts
            SET password_hash = %s
            WHERE student_id = %s
            """,
            (password_hash, student_id)
        )

        connection.commit()

        cursor.close()
        connection.close()

        # Clear password reset session
        session.pop("student_reset_id", None)
        session.pop("student_reset_verified", None)
        session.pop("student_reset_otp_hash", None)
        session.pop("student_reset_otp_expiry", None)
        session.pop("student_reset_otp_attempts", None)

        flash(
            "Password reset successfully. Please login.",
            "success"
        )

        return redirect(
            url_for("student_login")
        )

    return render_template(
        "student_reset_password.html"
    )


@app.route("/student-register", methods=["GET", "POST"])
def student_register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

                        # Check required fields
        if not name or not department or not phone or not password or not confirm_password:
            flash(
                "Please fill in all fields.",
                "error"
            )
            return render_template(
                "student_register.html"
            )

               # Check phone number
        if not re.fullmatch(r"\d{10}", phone):
            flash(
                "Phone number must contain exactly 10 digits.",
                "error"
            )
            return render_template(
                "student_register.html"
            )

        # Check password length
        if len(password) < 8 or len(password) > 11:
            flash(
                "Password must be between 8 and 11 characters.",
                "error"
            )
            return render_template(
                "student_register.html"
            )

        # Check for alphabet
        if not re.search(r"[A-Za-z]", password):
            flash(
                "Password must contain at least one alphabet.",
                "error"
            )
            return render_template(
                "student_register.html"
            )

        # Check for number
        if not re.search(r"\d", password):
            flash(
                "Password must contain at least one number.",
                "error"
            )
            return render_template(
                "student_register.html"
            )

        # Check for special character
        if not re.search(r"[^A-Za-z0-9]", password):
            flash(
                "Password must contain at least one special character.",
                "error"
            )
            return render_template(
                "student_register.html"
            )

        # Check passwords
        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "error"
            )
            return render_template(
                "student_register.html"
            )

        connection = None
        cursor = None

        try:

            connection = get_connection()
            cursor = connection.cursor()

            # Generate Student ID automatically
            from datetime import datetime

            student_id = datetime.now().strftime(
                "STU%Y%m%d%H%M%S%f"
            )

            # Create student
            cursor.execute(
                """
                INSERT INTO students
                (student_id, name, department, phone)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    student_id,
                    name,
                    department,
                    phone
                )
            )

            # ------------------------------------------
# STORE REGISTRATION TEMPORARILY
# ------------------------------------------

            password_hash = generate_password_hash(
                password
            )

            _PENDING_REGISTRATIONS[student_id] = {
                "name": name,
                "department": department,
                "phone": phone,
                "password_hash": password_hash
            }

            # Keep the student ID in session temporarily
            session["student_id"] = student_id

            flash(
                "Registration successful. Please scan your face.",
                "success"
            )

            return redirect(
                url_for(
                    "face_enrollment",
                    student_id=student_id
                )
            )
        except Exception as error:

            if connection:
                connection.rollback()

            print("Student registration error:", error)

            error_message = str(error).lower()

            if "unique_student_email" in error_message:
                flash(
                    "This email is already registered.",
                    "error"
                )

            elif "unique_student_phone" in error_message:
                flash(
                    "This phone number is already registered.",
                    "error"
                )

            else:
                flash(
                    "Unable to complete registration. Please try again.",
                    "error"
                )

            return render_template(
                "student_register.html"
            )

    return render_template(
        "student_register.html"
    )



      
# ==========================================
# STUDENT DASHBOARD
# ==========================================

@app.route("/student-dashboard")
def student_dashboard():

    if "student_id" not in session:
        flash(
            "Please login as a student first.",
            "error"
        )
        return redirect(
            url_for("student_login")
        )

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        student_id = session["student_id"]

        # ------------------------------------------
        # STUDENT INFORMATION
        # ------------------------------------------

        cursor.execute(
            """
            SELECT
                student_id,
                name,
                department,
                phone
            FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )

        student = cursor.fetchone()

        if not student:

            session.pop(
                "student_id",
                None
            )

            flash(
                "Student account not found.",
                "error"
            )

            return redirect(
                url_for("student_login")
            )

        # ------------------------------------------
        # MINIMUM ATTENDANCE SETTING
        # ------------------------------------------

        cursor.execute(
            """
            SELECT minimum_attendance
            FROM system_settings
            WHERE id = 1
            """
        )

        settings = cursor.fetchone()

        minimum_attendance = (
            int(settings["minimum_attendance"])
            if settings
            else 75
        )

        # ------------------------------------------
        # TOTAL WORKING DAYS
        #
        # Since the current system does not have
        # an academic calendar table, working days
        # are calculated from unique attendance dates.
        # ------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(DISTINCT attendance_date)
            AS working_days
            FROM attendance
            """
        )

        working_result = cursor.fetchone()

        working_days = (
            working_result["working_days"]
            or 0
        )

        # ------------------------------------------
        # STUDENT PRESENT DAYS
        # ------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(DISTINCT attendance_date)
            AS present_days
            FROM attendance
            WHERE student_id = %s
            AND LOWER(status) = 'present'
            """,
            (student_id,)
        )

        present_result = cursor.fetchone()

        present_days = (
            present_result["present_days"]
            or 0
        )

        # ------------------------------------------
        # ATTENDANCE PERCENTAGE
        # ------------------------------------------

        if working_days > 0:

            attendance_percentage = round(
                (
                    present_days
                    / working_days
                ) * 100
            )

        else:

            attendance_percentage = 0

        # ------------------------------------------
        # ELIGIBILITY
        # ------------------------------------------

        eligible_for_exams = (
            attendance_percentage
            >= minimum_attendance
        )

        # ------------------------------------------
        # TODAY'S ATTENDANCE
        # ------------------------------------------

        cursor.execute(
            """
            SELECT
                attendance_time,
                status
            FROM attendance
            WHERE student_id = %s
            AND attendance_date = CURDATE()
            ORDER BY attendance_time ASC
            LIMIT 1
            """,
            (student_id,)
        )

        today_record = cursor.fetchone()

        today_entry = (
            today_record["attendance_time"]
            if today_record
            else None
        )

        today_status = (
            today_record["status"]
            if today_record
            else "Absent"
        )

        # ------------------------------------------
        # RECENT HISTORY
        #
        # Last 3 working dates available in the
        # attendance table.
        # ------------------------------------------

        cursor.execute(
            """
            SELECT DISTINCT attendance_date
            FROM attendance
            ORDER BY attendance_date DESC
            LIMIT 3
            """
        )

        recent_dates = cursor.fetchall()

        recent_history = []

        for date_row in recent_dates:

            current_date = (
                date_row["attendance_date"]
            )

            cursor.execute(
                """
                SELECT
                    attendance_time,
                    status
                FROM attendance
                WHERE student_id = %s
                AND attendance_date = %s
                ORDER BY attendance_time ASC
                LIMIT 1
                """,
                (
                    student_id,
                    current_date
                )
            )

            record = cursor.fetchone()

            if record:

                recent_history.append({
                    "date": current_date,
                    "entry": record[
                        "attendance_time"
                    ],
                    "status": record[
                        "status"
                    ]
                })

            else:

                recent_history.append({
                    "date": current_date,
                    "entry": None,
                    "status": "Absent"
                })

        return render_template(
            "student_dashboard.html",

            student=student,

            minimum_attendance=(
                minimum_attendance
            ),

            working_days=(
                working_days
            ),

            present_days=(
                present_days
            ),

            attendance_percentage=(
                attendance_percentage
            ),

            eligible_for_exams=(
                eligible_for_exams
            ),

            today_entry=(
                today_entry
            ),

            today_status=(
                today_status
            ),

            recent_history=(
                recent_history
            )
        )

    except Exception as error:

        print(
            "Student dashboard error:",
            error
        )

        flash(
            "Unable to load student dashboard.",
            "error"
        )

        return redirect(
            url_for("student_login")
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()

@app.route("/student-profile")
def student_profile():

    if "student_id" not in session:
        flash(
            "Please login as a student first.",
            "error"
        )
        return redirect(
            url_for("student_login")
        )

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                student_id,
                name,
                email,
                department,
                phone
            FROM students
            WHERE student_id = %s
            """,
            (session["student_id"],)
        )

        student = cursor.fetchone()

        if not student:
            session.pop(
                "student_id",
                None
            )

            flash(
                "Student account not found.",
                "error"
            )

            return redirect(
                url_for("student_login")
            )

        return render_template(
            "student_profile.html",
            student=student
        )

    except Exception as error:

        print(
            "Student profile error:",
            error
        )

        flash(
            "Unable to load your profile.",
            "error"
        )

        return redirect(
            url_for("student_dashboard")
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()

# ==========================================
# STUDENT MY FACE ID
# ==========================================

@app.route("/student-face-id")
def student_face_id():

    if "student_id" not in session:
        flash("Please login as a student first.", "error")
        return redirect(url_for("student_login"))

    student_id = session["student_id"]

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT student_id, name, department
            FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )

        student = cursor.fetchone()

        if not student:
            session.pop("student_id", None)
            flash("Student account not found.", "error")
            return redirect(url_for("student_login"))

        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        dataset_dir = os.path.join(
            base_dir,
            "dataset"
        )

        sample_count = 0

        if os.path.exists(dataset_dir):

            prefix = f"User.{student_id}."

            for filename in os.listdir(dataset_dir):

                if (
                    filename.startswith(prefix)
                    and filename.lower().endswith(".jpg")
                ):
                    sample_count += 1

        face_registered = sample_count > 0

        face_status = (
            "Registered"
            if face_registered
            else "Not Registered"
        )

        registration_date = None

        if face_registered:

            latest_file = None
            latest_time = None

            for filename in os.listdir(dataset_dir):

                if (
                    filename.startswith(
                        f"User.{student_id}."
                    )
                    and filename.lower().endswith(".jpg")
                ):

                    file_path = os.path.join(
                        dataset_dir,
                        filename
                    )

                    file_time = os.path.getmtime(
                        file_path
                    )

                    if (
                        latest_time is None
                        or file_time > latest_time
                    ):
                        latest_time = file_time
                        latest_file = file_path

            if latest_file:

                from datetime import datetime

                registration_date = datetime.fromtimestamp(
                    latest_time
                ).strftime(
                    "%d %b %Y, %I:%M %p"
                )

        return render_template(
            "student_face_id.html",
            student=student,
            sample_count=sample_count,
            face_registered=face_registered,
            face_status=face_status,
            registration_date=registration_date
        )

    except Exception as error:

        print(
            "Student Face ID error:",
            error
        )

        flash(
            "Unable to load Face ID information.",
            "error"
        )

        return redirect(
            url_for("student_dashboard")
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()



# ==========================================
# STUDENT ATTENDANCE HISTORY
# ==========================================

@app.route("/student-attendance")
def student_attendance():

    if "student_id" not in session:
        flash(
            "Please login as a student first.",
            "error"
        )
        return redirect(
            url_for("student_login")
        )

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor(
            dictionary=True
        )

        student_id = session["student_id"]

        # Get student information
        cursor.execute(
            """
            SELECT
                student_id,
                name,
                department
            FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )

        student = cursor.fetchone()

        if not student:
            session.pop(
                "student_id",
                None
            )

            flash(
                "Student account not found.",
                "error"
            )

            return redirect(
                url_for("student_login")
            )

        # Get all attendance records
        cursor.execute(
            """
            SELECT
                attendance_date,
                attendance_time,
                status
            FROM attendance
            WHERE student_id = %s
            ORDER BY
                attendance_date DESC,
                attendance_time DESC
            """,
            (student_id,)
        )

        records = cursor.fetchall()

        # Convert database dates/times
        # into JSON-friendly values
        attendance_data = []

        for record in records:

            attendance_date = record[
                "attendance_date"
            ]

            attendance_time = record[
                "attendance_time"
            ]

            status = str(
                record["status"] or ""
            ).strip().lower()

            if attendance_date:

                date_string = (
                    attendance_date.strftime(
                        "%Y-%m-%d"
                    )
                )

            else:

                continue

            if attendance_time:

                try:
                    time_string = (
                        attendance_time.strftime(
                            "%I:%M %p"
                        )
                    )

                except AttributeError:

                    time_string = str(
                        attendance_time
                    )

            else:

                time_string = "—"

            attendance_data.append({

                "date":
                    date_string,

                "time":
                    time_string,

                "status":
                    status

            })

        return render_template(
            "student_attendance.html",
            student=student,
            attendance_records=attendance_data
        )

    except Exception as error:

        print(
            "Student attendance error:",
            error
        )

        flash(
            "Unable to load attendance history.",
            "error"
        )

        return redirect(
            url_for("student_dashboard")
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()
# ==========================================
# STUDENT ATTENDANCE SUMMARY
# ==========================================

@app.route("/student-summary")
def student_summary():

    if "student_id" not in session:
        flash("Please login as a student first.", "error")
        return redirect(url_for("student_login"))

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    # Get student information
    cursor.execute(
        """
        SELECT student_id, name, email, department
        FROM students
        WHERE student_id = %s
        """,
        (session["student_id"],)
    )

    student = cursor.fetchone()

    # Get total attendance records
    cursor.execute(
        """
        SELECT COUNT(*) AS total_records
        FROM attendance
        WHERE student_id = %s
        """,
        (session["student_id"],)
    )

    total_result = cursor.fetchone()
    total_records = total_result["total_records"] or 0

    # Get present records
    cursor.execute(
        """
        SELECT COUNT(*) AS present_count
        FROM attendance
        WHERE student_id = %s
        AND LOWER(status) = 'present'
        """,
        (session["student_id"],)
    )

    present_result = cursor.fetchone()
    present_count = present_result["present_count"] or 0

    cursor.close()
    connection.close()

    # Calculate attendance percentage
    if total_records > 0:
        attendance_percentage = round(
            (present_count / total_records) * 100,
            1
        )
    else:
        attendance_percentage = 0

    if not student:
        session.pop("student_id", None)
        flash("Student account not found.", "error")
        return redirect(url_for("student_login"))

    return render_template(
        "student_summary.html",
        student=student,
        total_records=total_records,
        present_count=present_count,
        attendance_percentage=attendance_percentage
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
def home():
    return render_template("index.html")


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
# UPDATE / RE-SUBMIT FACE ID
# ==========================================

@app.route("/update-face-id/<student_id>")
def update_face_id(student_id):

    # Only the logged-in student or admin can update it
    is_admin = "admin_username" in session
    is_student = session.get("student_id") == student_id

    if not is_admin and not is_student:
        flash(
            "Please login first.",
            "error"
        )
        return redirect(
            url_for("student_login")
        )

    connection = None
    cursor = None

    try:

        # ------------------------------
        # Verify student
        # ------------------------------

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT student_id, name
            FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )

        student = cursor.fetchone()

        cursor.close()
        connection.close()

        if not student:

            flash(
                "Student not found.",
                "error"
            )

            if is_student:
                return redirect(
                    url_for("student_dashboard")
                )

            return redirect(
                url_for("students")
            )

        # ------------------------------
        # Remove old face samples
        # ------------------------------

        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        dataset_dir = os.path.join(
            base_dir,
            "dataset"
        )

        removed_count = 0

        if os.path.exists(dataset_dir):

            prefix = f"User.{student_id}."

            for filename in os.listdir(
                dataset_dir
            ):

                if (
                    filename.startswith(prefix)
                    and filename.lower().endswith(".jpg")
                ):

                    file_path = os.path.join(
                        dataset_dir,
                        filename
                    )

                    try:

                        os.remove(file_path)

                        removed_count += 1

                    except OSError as error:

                        print(
                            "Unable to remove old face:",
                            error
                        )

        # ------------------------------
        # Remove old trained model
        # ------------------------------
        #
        # It will be recreated after
        # the new face is captured.
        #

        trainer_dir = os.path.join(
            base_dir,
            "trainer"
        )

        model_path = os.path.join(
            trainer_dir,
            "trainer.yml"
        )

        mapping_path = os.path.join(
            trainer_dir,
            "student_mapping.txt"
        )

        # Only remove the model when it exists.
        # The new registration will rebuild it.

        try:

            if os.path.exists(model_path):
                os.remove(model_path)

            if os.path.exists(mapping_path):
                os.remove(mapping_path)

        except OSError as error:

            print(
                "Unable to reset face model:",
                error
            )

        # ------------------------------
        # Reset browser recognition
        # ------------------------------

        global _BROWSER_RECOGNIZER
        global _BROWSER_LABEL_TO_STUDENT
        global _BROWSER_STUDENT_DATA

        _BROWSER_RECOGNIZER = None
        _BROWSER_LABEL_TO_STUDENT = {}
        _BROWSER_STUDENT_DATA = {}

        # ------------------------------
        # Reset enrollment duplicate state
        # ------------------------------

        global _ENROLLMENT_MATCHES

        _ENROLLMENT_MATCHES.pop(
            student_id,
            None
        )

        # ------------------------------
        # Continue to face enrollment
        # ------------------------------

        flash(
            "Old Face ID removed. Please register your new face.",
            "success"
        )

        return redirect(
            url_for(
                "face_enrollment",
                student_id=student_id
            )
        )

    except Exception as error:

        print(
            "Update Face ID error:",
            error
        )

        flash(
            "Unable to update Face ID.",
            "error"
        )

        return redirect(
            url_for("student_dashboard")
        )

@app.route("/face-enrollment/<student_id>")
def face_enrollment(student_id):

    # Allow either:
    # 1. The student themselves
    # 2. A logged-in admin

    is_admin = "admin_username" in session
    is_student = session.get("student_id") == student_id

    if not is_admin and not is_student:
        flash("Please login or register first.", "error")
        return redirect(url_for("student_login"))

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT student_id, name
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    cursor.close()
    connection.close()

    # ------------------------------------------
    # Check pending registration
    # ------------------------------------------

    if not student:

        pending = _PENDING_REGISTRATIONS.get(
            student_id
        )

        if pending:

            student = {
                "student_id": student_id,
                "name": pending["name"]
            }

        else:

            flash(
                "Student registration not found.",
                "error"
            )

            session.pop(
                "student_id",
                None
            )

            return redirect(
                url_for("student_login")
            )

    # Student always goes to Student Dashboard
    # Admin goes to Admin Students page
    if is_student:
        finish_url = url_for("student_dashboard")
        back_url = url_for("student_login")
    else:
        finish_url = url_for("students")
        back_url = url_for("students")

    return render_template(
    "face_capture.html",
    student_id=student["student_id"],
    student_name=student["name"],
    finish_url=finish_url,
    back_url=back_url
)


@app.route(
    "/capture-face/<student_id>",
    methods=["POST"]
)
def capture_face(student_id):

    is_admin = "admin_username" in session
    is_student = session.get("student_id") == student_id

    if not is_admin and not is_student:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 403

    try:

        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        dataset_dir = os.path.join(
            base_dir,
            "dataset"
        )

        cascade_path = os.path.join(
            base_dir,
            "haarcascade_frontalface_default.xml"
        )

        os.makedirs(
            dataset_dir,
            exist_ok=True
        )

               # ----------------------------------
        # Verify student or pending registration
        # ----------------------------------

        connection = get_connection()
        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT student_id
            FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )

        student = cursor.fetchone()

        cursor.close()
        connection.close()

        # A newly registering student may not
        # exist in the database yet.
        if not student:

            if student_id not in _PENDING_REGISTRATIONS:

                return jsonify({
                    "status": "error",
                    "message": "Student registration not found."
                }), 404

        # ----------------------------------
        # Read image
        # ----------------------------------

        raw_data = request.get_data()

        if not raw_data:

            return jsonify({
                "status": "error",
                "message": "No camera image received."
            }), 400

        image_array = np.frombuffer(
            raw_data,
            dtype=np.uint8
        )

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if frame is None:

            return jsonify({
                "status": "error",
                "message": "Invalid camera image."
            }), 400

        # ----------------------------------
        # Load face detector
        # ----------------------------------

        detector = cv2.CascadeClassifier(
            cascade_path
        )

        if detector.empty():

            return jsonify({
                "status": "error",
                "message": "Face detector could not be loaded."
            }), 500

        # ----------------------------------
        # Convert to grayscale
        # ----------------------------------

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        gray = cv2.equalizeHist(
            gray
        )

        # ----------------------------------
        # Detect faces
        # ----------------------------------

        faces = detector.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(100, 100)
        )

        if len(faces) == 0:

            return jsonify({
                "status": "no_face",
                "message": "No face detected. Keep your face inside the guide."
            })

        # ----------------------------------
        # Select largest face
        # ----------------------------------

        x, y, w, h = max(
            faces,
            key=lambda face: face[2] * face[3]
        )

        face_image = gray[
            y:y + h,
            x:x + w
        ]

        # ----------------------------------
        # Find next sample number
        # ----------------------------------

        existing_files = []

        for filename in os.listdir(
            dataset_dir
        ):

            if filename.startswith(
                f"User.{student_id}."
            ) and filename.endswith(
                ".jpg"
            ):

                existing_files.append(
                    filename
                )

                # ----------------------------------
        # Find next sample number
        # ----------------------------------

        sample_numbers = []

        for filename in existing_files:

            try:

                number = int(
                    filename
                    .rsplit(".", 2)[1]
                )

                sample_numbers.append(
                    number
                )

            except (ValueError, IndexError):

                continue

        next_number = (
            max(sample_numbers) + 1
            if sample_numbers
            else 1
        )

        # Do not capture more than 30 samples
        if next_number > 30:

            return jsonify({
                "status": "complete",
                "count": 30,
                "message": "30 face samples already exist."
            })

        # ----------------------------------
        # Save face sample
        # ----------------------------------

        filename = (
            f"User.{student_id}.{next_number}.jpg"
        )

        filepath = os.path.join(
            dataset_dir,
            filename
        )

        saved = cv2.imwrite(
            filepath,
            face_image
        )

        if not saved:
            return jsonify({
                "status": "error",
                "message": "Unable to save face sample."
            }), 500

        current_count = next_number

# ----------------------------------
# Automatically train model
# after 30 samples
# ----------------------------------

        if current_count == 30:

            try:

                train_script = os.path.join(
                    base_dir,
                    "train_model.py"
                )

                result = subprocess.run(
                    [sys.executable, train_script],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode != 0:

                    print("Training failed:")
                    print(result.stdout)
                    print(result.stderr)

                    return jsonify({
                        "status": "training_error",
                        "count": current_count,
                        "message": (
                            "Face samples captured, "
                            "but model training failed."
                        )
                    }), 500

                print(
                    "Face recognition model "
                    "trained successfully."
                )

            except Exception as training_error:

                print(
                    "Automatic training error:",
                    training_error
                )

                return jsonify({
                    "status": "training_error",
                    "count": current_count,
                    "message": (
                        "Face samples captured, "
                        "but model training failed."
                    )
                }), 500

        # ----------------------------------
        # COMPLETE STUDENT REGISTRATION
        # ----------------------------------

        if current_count == 30:

            pending = _PENDING_REGISTRATIONS.get(
                student_id
            )

            if pending:

                connection = None
                cursor = None

                try:

                    connection = get_connection()
                    cursor = connection.cursor()

                    # Create student record
                    cursor.execute(
                        """
                        INSERT INTO students
                        (
                            student_id,
                            name,
                            department,
                            phone
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            student_id,
                            pending["name"],
                            pending["department"],
                            pending["phone"]
                        )
                    )

                    # Create student login account
                    cursor.execute(
                        """
                        INSERT INTO student_accounts
                        (
                            student_id,
                            password_hash
                        )
                        VALUES (%s, %s)
                        """,
                        (
                            student_id,
                            pending["password_hash"]
                        )
                    )

                    connection.commit()

                    # Remove temporary registration
                    _PENDING_REGISTRATIONS.pop(
                        student_id,
                        None
                    )

                    print(
                        "Student registration completed:",
                        student_id
                    )

                except Exception as registration_error:

                    if connection:
                        connection.rollback()

                    print(
                        "Student database creation error:",
                        registration_error
                    )

                    return jsonify({
                        "status": "error",
                        "message": (
                            "Face scan completed, "
                            "but student registration could not "
                            "be completed."
                        )
                    }), 500

                finally:

                    if cursor:
                        cursor.close()

                    if connection:
                        connection.close()

# ----------------------------------
# Return capture result
# ----------------------------------

        return jsonify({
            "status": (
                "complete"
                if current_count == 30
                else "captured"
            ),
            "count": current_count,
            "message": (
                "Face registration completed successfully."
                if current_count == 30
                else (
                    "Face sample captured."
                )
            )
        })

    except Exception as error:

        print(
            "Face enrollment error:",
            error
        )

        return jsonify({
            "status": "error",
            "message": "Unable to capture face sample."
        }), 500

# ==========================================
# DELETE STUDENT
# ==========================================

@app.route(
    "/delete-student",
    methods=["POST"]
)
@login_required
def delete_student_route():

    global _BROWSER_RECOGNIZER
    global _BROWSER_FACE_DETECTOR
    global _BROWSER_LABEL_TO_STUDENT
    global _BROWSER_STUDENT_DATA
    global _BROWSER_ATTENDANCE_MARKED

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

        # ------------------------------------------
        # DELETE STUDENT DATA + FACE FILES
        # ------------------------------------------

        deleted = delete_student(
            student_id
        )

        if not deleted:

            flash(
                "Student not found.",
                "error"
            )

            return redirect(
                url_for("students")
            )


        # ------------------------------------------
        # RESET BROWSER RECOGNITION CACHE
        # ------------------------------------------

        _BROWSER_RECOGNIZER = None
        _BROWSER_FACE_DETECTOR = None
        _BROWSER_LABEL_TO_STUDENT = {}
        _BROWSER_STUDENT_DATA = {}
        _BROWSER_ATTENDANCE_MARKED.discard(
            student_id
        )

                # ------------------------------------------
        # DELETE THIS STUDENT'S FACE SAMPLES
        # ------------------------------------------

        if os.path.exists(dataset_dir):

            deleted_face_files = [
                filename
                for filename in os.listdir(
                    dataset_dir
                )
                if (
                    filename.lower().endswith(".jpg")
                    and
                    filename.startswith(
                        f"User.{student_id}."
                    )
                )
            ]

            for filename in deleted_face_files:

                try:

                    os.remove(
                        os.path.join(
                            dataset_dir,
                            filename
                        )
                    )

                    print(
                        "Deleted face sample:",
                        filename
                    )

                except OSError as face_error:

                    print(
                        "Face file deletion error:",
                        face_error
                    )


        # ------------------------------------------
        # CHECK REMAINING FACE DATA
        # ------------------------------------------

        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        dataset_dir = os.path.join(
            base_dir,
            "dataset"
        )

        trainer_dir = os.path.join(
            base_dir,
            "trainer"
        )

        model_path = os.path.join(
            trainer_dir,
            "trainer.yml"
        )

        mapping_path = os.path.join(
            trainer_dir,
            "student_mapping.txt"
        )

        remaining_face_files = []

        if os.path.exists(dataset_dir):

            remaining_face_files = [
                filename
                for filename in os.listdir(
                    dataset_dir
                )
                if (
                    filename.lower().endswith(".jpg")
                    and filename.startswith("User.")
                )
            ]


        # ------------------------------------------
        # RETRAIN OR REMOVE OLD MODEL
        # ------------------------------------------

        if remaining_face_files:

            train_script = os.path.join(
                base_dir,
                "train_model.py"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    train_script
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:

                print(
                    "Model retraining failed:"
                )

                print(
                    result.stdout
                )

                print(
                    result.stderr
                )

                flash(
                    "Student deleted, but face model retraining failed. "
                    "Run train_model.py manually.",
                    "error"
                )

                return redirect(
                    url_for("students")
                )

        else:

            # No students/face data remain.
            # Remove the old recognition model.

            try:

                if os.path.exists(
                    model_path
                ):
                    os.remove(
                        model_path
                    )

                if os.path.exists(
                    mapping_path
                ):
                    os.remove(
                        mapping_path
                    )

            except OSError as model_error:

                print(
                    "Model cleanup error:",
                    model_error
                )


        flash(
            "Student information, attendance, face images, and recognition data deleted successfully.",
            "success"
        )

    except Error:

        flash(
            "Unable to delete student.",
            "error"
        )

    except Exception as error:

        print(
            "Student deletion error:",
            error
        )

        flash(
            "Unable to complete student deletion.",
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
    return render_template("recognition.html")


# ==========================================
# START FACE RECOGNITION
# ==========================================

@app.route("/start-recognition")
@login_required
def start_recognition():
    return redirect(url_for("recognition"))

# ==========================================
# BROWSER FACE RECOGNITION
# ==========================================

_BROWSER_RECOGNIZER = None
_BROWSER_FACE_DETECTOR = None
_BROWSER_LABEL_TO_STUDENT = {}
_BROWSER_STUDENT_DATA = {}
_BROWSER_ATTENDANCE_MARKED = {}


# ==========================================
# FACE ENROLLMENT DUPLICATE CHECK
# ==========================================

_ENROLLMENT_MATCHES = {}
_PENDING_REGISTRATIONS = {}



def load_browser_recognition():

    global _BROWSER_RECOGNIZER
    global _BROWSER_FACE_DETECTOR
    global _BROWSER_LABEL_TO_STUDENT
    global _BROWSER_STUDENT_DATA

    if _BROWSER_RECOGNIZER is not None:
        return

    base_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    model_path = os.path.join(
        base_dir,
        "trainer",
        "trainer.yml"
    )

    mapping_path = os.path.join(
        base_dir,
        "trainer",
        "student_mapping.txt"
    )

    cascade_path = os.path.join(
        base_dir,
        "haarcascade_frontalface_default.xml"
    )

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            "trainer.yml not found. Run train_model.py first."
        )

    if not os.path.exists(mapping_path):
        raise FileNotFoundError(
            "student_mapping.txt not found."
        )

    if not os.path.exists(cascade_path):
        raise FileNotFoundError(
            "haarcascade_frontalface_default.xml not found."
        )

    detector = cv2.CascadeClassifier(
        cascade_path
    )

    if detector.empty():
        raise RuntimeError(
            "Could not load face detector."
        )

    recognizer = (
        cv2.face.LBPHFaceRecognizer_create()
    )

    recognizer.read(model_path)

    label_to_student = {}

    with open(
        mapping_path,
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            label, student_id = (
                line.split(",", 1)
            )

            label_to_student[
                int(label)
            ] = student_id.strip()

    students = get_students()

    student_data = {
        student["student_id"]: student
        for student in students
    }

    _BROWSER_FACE_DETECTOR = detector
    _BROWSER_RECOGNIZER = recognizer
    _BROWSER_LABEL_TO_STUDENT = label_to_student
    _BROWSER_STUDENT_DATA = student_data


def write_browser_status(
    status,
    message="",
    student_id="",
    name="",
    attendance_marked=False
):

    base_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    status_path = os.path.join(
        base_dir,
        "trainer",
        "recognition_status.json"
    )

    data = {
        "status": status,
        "message": message,
        "student_id": student_id,
        "name": name,
        "attendance_marked": attendance_marked
    }

    try:

        with open(
            status_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(data, file)

    except OSError:

        pass


@app.route(
    "/recognition-frame",
    methods=["POST"]
)
@login_required
def recognition_frame():

    try:

        load_browser_recognition()

        raw_data = request.get_data()

        if not raw_data:

            return jsonify({
                "status": "error",
                "message": "Empty camera frame."
            }), 400

        image_array = np.frombuffer(
            raw_data,
            np.uint8
        )

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if frame is None:

            return jsonify({
                "status": "error",
                "message": "Invalid camera frame."
            }), 400

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        gray = cv2.equalizeHist(
            gray
        )

        faces = _BROWSER_FACE_DETECTOR.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(70, 70)
        )

        if len(faces) == 0:

            write_browser_status(
                "scanning",
                "Looking for a face..."
            )

            return jsonify({
                "status": "scanning",
                "message": "Looking for a face..."
            })

        # Use the largest detected face
        face = max(
            faces,
            key=lambda item: item[2] * item[3]
        )

        x, y, w, h = face

        face_image = gray[
            y:y + h,
            x:x + w
        ]

        label, confidence = (
            _BROWSER_RECOGNIZER.predict(
                face_image
            )
        )

        display_score = max(
            0,
            min(
                100,
                round(100 - confidence)
            )
        )

        recognized = (
            label in _BROWSER_LABEL_TO_STUDENT
            and confidence < 100
        )

        if not recognized:

            write_browser_status(
                "unknown",
                "Unknown face detected."
            )

            return jsonify({
                "status": "unknown",
                "message": "Unknown face detected.",
                "score": display_score
            })

        student_id = (
            _BROWSER_LABEL_TO_STUDENT[label]
        )

        student = (
            _BROWSER_STUDENT_DATA.get(
                student_id
            )
        )

        if not student:

            write_browser_status(
                "unknown",
                "Student is not registered."
            )

            return jsonify({
                "status": "unknown",
                "message": "Student is not registered."
            })

        name = student["name"]

        attendance_marked = False

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT duplicate_cooldown
                FROM system_settings
                WHERE id = 1
                """
            )

            settings_data = cursor.fetchone()

            duplicate_cooldown = (
                int(settings_data["duplicate_cooldown"])
                if settings_data
                else 30
            )

        finally:
            if cursor:
                cursor.close()

            if connection:
                connection.close()



        current_time = time.time()

        last_marked_time = _BROWSER_ATTENDANCE_MARKED.get(
            student_id
        )

        if (
            last_marked_time is None
            or current_time - last_marked_time >= duplicate_cooldown
        ):

            marked = mark_attendance(
                student_id,
                name
            )

            _BROWSER_ATTENDANCE_MARKED[
                student_id
            ] = current_time

            attendance_marked = bool(marked)

        write_browser_status(
            "recognized",
            f"{name} - PRESENT",
            student_id,
            name,
            attendance_marked
        )

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT recognition_sound
                FROM system_settings
                WHERE id = 1
                """
            )

            sound_settings = cursor.fetchone()

            recognition_sound = bool(
                sound_settings["recognition_sound"]
            ) if sound_settings else True

        finally:
            if cursor:
                cursor.close()

            if connection:
                connection.close()

        return jsonify({
            "status": "recognized",
            "student_id": student_id,
            "name": name,
            "message": f"{name} - PRESENT",
            "attendance_marked": attendance_marked,
            "score": display_score,
            "recognition_sound": recognition_sound
        })

    except Exception as error:

        write_browser_status(
            "error",
            str(error)
        )

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

@app.route("/recognition-status")
@login_required
def recognition_status():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    status_path = os.path.join(
        base_dir, "trainer", "recognition_status.json"
    )

    if not os.path.exists(status_path):
        return {
            "status": "idle",
            "message": "Face recognition is not running."
        }

    try:
        with open(status_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {
            "status": "scanning",
            "message": "Starting face recognition..."
        }


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    stats = get_dashboard_stats()

    daily_attendance = get_daily_attendance()

    department_attendance = get_department_attendance()


    daily_labels = [
        str(record["attendance_date"])
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

# ==========================================
# SETTINGS
# ==========================================

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        if request.method == "POST":

            attendance_mode = request.form.get(
                "attendance_mode",
                "entrance"
            )

            duplicate_cooldown = int(
                request.form.get(
                    "duplicate_cooldown",
                    30
                )
            )

            recognition_sound = (
                1
                if request.form.get(
                    "recognition_sound"
                )
                else 0
            )

            unknown_face_alert = (
                1
                if request.form.get(
                    "unknown_face_alert"
                )
                else 0
            )

            dashboard_refresh = int(
                request.form.get(
                    "dashboard_refresh",
                    0
                )
            )

            minimum_attendance = int(
                request.form.get(
                    "minimum_attendance",
                    75
                )
            )

            cursor.execute(
                """
                UPDATE system_settings
                SET
                    attendance_mode = %s,
                    duplicate_cooldown = %s,
                    recognition_sound = %s,
                    unknown_face_alert = %s,
                    dashboard_refresh = %s,
                    minimum_attendance = %s
                WHERE id = 1
                """,
                (
                    attendance_mode,
                    duplicate_cooldown,
                    recognition_sound,
                    unknown_face_alert,
                    dashboard_refresh,
                    minimum_attendance
                )
            )

            connection.commit()

            flash(
                "Settings saved successfully.",
                "success"
            )

        cursor.execute(
            """
            SELECT
                attendance_mode,
                duplicate_cooldown,
                recognition_sound,
                unknown_face_alert,
                dashboard_refresh,
                minimum_attendance
            FROM system_settings
            WHERE id = 1
            """
        )

        settings_data = cursor.fetchone()

        return render_template(
            "settings.html",
            settings=settings_data
        )

    except Exception as error:

        print(
            "Settings error:",
            error
        )

        if connection:
            connection.rollback()

        flash(
            "Unable to load settings.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()

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


    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        # ==========================================
        # GET ALL REGISTERED STUDENTS
        # ==========================================

        student_query = """
            SELECT
                student_id,
                name,
                department
            FROM students
        """

        student_params = []

        if search:

            student_query += """
                WHERE
                    student_id LIKE %s
                    OR name LIKE %s
                    OR department LIKE %s
            """

            search_value = f"%{search}%"

            student_params = [
                search_value,
                search_value,
                search_value
            ]


        student_query += """
            ORDER BY name ASC
        """


        cursor.execute(
            student_query,
            tuple(student_params)
        )

        students = cursor.fetchall()


        # ==========================================
        # GET ATTENDANCE RECORDS
        # ==========================================

        attendance_query = """
            SELECT
                student_id,
                attendance_date,
                status
            FROM attendance
        """

        attendance_params = []


        if attendance_date:

            attendance_query += """
                WHERE attendance_date = %s
            """

            attendance_params.append(
                attendance_date
            )


        attendance_query += """
            ORDER BY attendance_date ASC
        """


        cursor.execute(
            attendance_query,
            tuple(attendance_params)
        )

        attendance_records = cursor.fetchall()


        # ==========================================
        # FIND UNIQUE WORKING DAYS
        # ==========================================

        working_dates = set()

        for record in attendance_records:

            if record["attendance_date"]:

                working_dates.add(
                    str(record["attendance_date"])
                )


        working_days = len(
            working_dates
        )


        # ==========================================
        # CALCULATE EACH STUDENT
        # ==========================================

        report_students = []


        for student in students:

            student_id = student["student_id"]


            # Store unique dates for this student

            present_dates = set()


            for record in attendance_records:

                if (
                    record["student_id"]
                    == student_id
                    and str(
                        record["status"]
                    ).lower()
                    == "present"
                ):

                    if record["attendance_date"]:

                        present_dates.add(
                            str(
                                record["attendance_date"]
                            )
                        )


            days_present = len(
                present_dates
            )


            # ==========================================
            # ATTENDANCE PERCENTAGE
            # ==========================================

            if working_days > 0:

                attendance_percentage = round(
                    (
                        days_present
                        / working_days
                    ) * 100,
                    2
                )

            else:

                attendance_percentage = 0


            # ==========================================
            # STATUS
            # ==========================================

            if attendance_percentage >= 75:

                status = "Good"

            elif attendance_percentage >= 60:

                status = "Warning"

            else:

                status = "At risk"


            report_students.append({

                "student_id":
                    student_id,

                "name":
                    student["name"],

                "department":
                    student.get(
                        "department",
                        ""
                    ),

                "days_present":
                    days_present,

                "working_days":
                    working_days,

                "attendance_percentage":
                    attendance_percentage,

                "status":
                    status

            })


        # ==========================================
        # BELOW 75%
        # ==========================================

        below_threshold = sum(

            1

            for student
            in report_students

            if student[
                "attendance_percentage"
            ] < 75

        )


        # ==========================================
        # CLOSE DATABASE
        # ==========================================

        cursor.close()
        connection.close()


        # ==========================================
        # SEND DATA TO REPORTS PAGE
        # ==========================================

        return render_template(

            "reports.html",

            attendance=
                report_students,

            search=
                search,

            attendance_date=
                attendance_date,

            total_records=
                working_days,

            present_count=
                sum(
                    student[
                        "days_present"
                    ]
                    for student
                    in report_students
                ),

            working_days=
                working_days,

            below_threshold=
                below_threshold

        )


    except Exception as error:

        print(
            "Reports error:",
            error
        )


        if cursor:

            cursor.close()


        if connection:

            connection.close()


        flash(
            "Unable to generate attendance report.",
            "error"
        )


        return redirect(
            url_for("dashboard")
        )

# ==========================================
# EXPORT ATTENDANCE CSV
# ==========================================

@app.route("/export-attendance")
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

        data.append({
            "ID": record["id"],
            "Student ID": record["student_id"],
            "Name": record["name"],
            "Date": record["attendance_date"],
            "Time": record["attendance_time"],
            "Status": record["status"]
        })


    dataframe = pd.DataFrame(data)


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
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )