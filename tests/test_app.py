from app import app


def test_login_page_loads():
    client = app.test_client()

    response = client.get("/login")

    assert response.status_code == 200


def test_home_requires_login():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.location

def test_attendance_module_exists():
    import attendance

    assert hasattr(
        attendance,
        "mark_attendance"
    )

def test_register_rejects_short_student_id():
    client = app.test_client()

    with client.session_transaction() as session:
        session["admin_username"] = "test-admin"

    response = client.post(
        "/register",
        data={
            "student_id": "AB",
            "name": "Test Student",
            "email": "test@example.com",
            "department": "IT"
        }
    )

    assert response.status_code == 302
    assert "/register" in response.location