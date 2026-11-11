from app import db
from app.models import User, AuditLog


def register(client, name="New Person", email="new@test.com",
             password="NewPass12345", confirm=None):
    return client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": confirm if confirm is not None else password,
        },
    )


def test_register_creates_account_with_hashed_password(app, client):
    response = register(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with app.app_context():
        user = User.query.filter_by(email="new@test.com").one()
        assert user.role == "visitor"
        assert user.password_hash != "NewPass12345"
        assert user.check_password("NewPass12345")
        assert not user.check_password("WrongPass12345")


def test_register_rejects_duplicate_email(client):
    response = register(client, email="visitor@test.com")
    assert response.status_code == 200
    assert b"This email is already registered." in response.data


def test_register_rejects_letters_only_password(app, client):
    response = register(client, password="abcdefgh")
    assert b"at least one letter and one number" in response.data
    with app.app_context():
        assert User.query.filter_by(email="new@test.com").first() is None


def test_register_rejects_common_password(client):
    response = register(client, password="password123")
    assert b"This password is too common." in response.data


def test_register_rejects_mismatched_passwords(client):
    response = register(client, confirm="DifferentPass123")
    assert b"Passwords must match." in response.data


def test_login_success_opens_protected_page(client, login, users):
    response = login(users["visitor"]["email"], users["visitor"]["password"])
    assert response.status_code == 302
    assert client.get("/my-bookings").status_code == 200


def test_login_wrong_password_is_rejected(client, login, users):
    response = login(users["visitor"]["email"], "WrongPass12345")
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data
    assert client.get("/my-bookings").status_code == 302


def test_unknown_email_gives_same_message(client, login):
    response = login("nobody@test.com", "WrongPass12345")
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


def test_account_locks_after_five_failed_logins(client, login, users):
    email = users["visitor"]["email"]
    for _ in range(5):
        login(email, "WrongPass12345")

    response = login(email, users["visitor"]["password"])
    assert response.status_code == 429
    assert b"Too many failed attempts" in response.data
    assert client.get("/my-bookings").status_code == 302


def test_logout_requires_post(client, login, users):
    login(users["visitor"]["email"], users["visitor"]["password"])
    assert client.get("/logout").status_code == 405
    assert client.get("/my-bookings").status_code == 200

    assert client.post("/logout").status_code == 302
    assert client.get("/my-bookings").status_code == 302


def test_login_ignores_unsafe_next_address(client, users):
    response = client.post(
        "/login?next=https://evil.example.com",
        data={
            "email": users["visitor"]["email"],
            "password": users["visitor"]["password"],
        },
    )
    assert response.status_code == 302
    assert "evil" not in response.headers["Location"]


def test_login_is_written_to_audit_log(app, login, users):
    login(users["visitor"]["email"], users["visitor"]["password"])
    with app.app_context():
        actions = [row.action for row in AuditLog.query.all()]
        assert "User logged in" in actions


def test_language_choice_is_saved_for_logged_in_user(app, client, login, users):
    login(users["visitor"]["email"], users["visitor"]["password"])
    response = client.get("/set-language/hi?next=/services")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/services")

    with app.app_context():
        user = User.query.filter_by(email=users["visitor"]["email"]).one()
        assert user.preferred_language == "hi"

    assert "लोकप्रिय सेवाएँ" in client.get("/").get_data(as_text=True)


def test_invalid_language_is_ignored(client):
    client.get("/set-language/xyz")
    assert b"Popular services" in client.get("/").data