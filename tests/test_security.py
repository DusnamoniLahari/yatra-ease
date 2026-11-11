import re

import pytest

from app import create_app, db
from app.models import User, Service, Availability
from conftest import seed_test_data

ADMIN_PAGES = [
    "/admin/",
    "/admin/bookings",
    "/admin/services",
    "/admin/services/new",
    "/admin/services/1/edit",
    "/admin/dashboard",
    "/admin/report.xlsx",
    "/admin/report.csv",
]

SERVICE_FORM = {
    "type": "bus",
    "name_en": "Admin Added",
    "name_hi": "एडमिन जोड़ा",
    "description_en": "Added during a test.",
    "description_hi": "टेस्ट में जोड़ा गया।",
    "location": "Hyderabad",
    "price": "500",
}


def logged_in(app, users, who):
    client = app.test_client()
    response = client.post(
        "/login",
        data={"email": users[who]["email"], "password": users[who]["password"]},
    )
    assert response.status_code == 302
    return client


def get_token(client, url="/login"):
    html = client.get(url).get_data(as_text=True)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert match, "no CSRF token found on the page"
    return match.group(1)


@pytest.fixture
def csrf_client():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SECRET_KEY": "test-secret-key-used-only-in-tests-1234567890",
            "WTF_CSRF_ENABLED": True,
        }
    )
    with app.app_context():
        seed_test_data()
    return app.test_client()


# ---------- headers, cookies, caching ----------

def test_security_headers_are_present(client):
    response = client.get("/")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


def test_content_security_policy_blocks_inline_scripts(client):
    csp = client.get("/").headers["Content-Security-Policy"]
    assert "script-src 'self';" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "unsafe-eval" not in csp


@pytest.mark.parametrize("url", ["/", "/services", "/login", "/register", "/service/1"])
def test_pages_contain_no_inline_scripts(client, url):
    html = client.get(url).get_data(as_text=True).lower()
    assert "onclick=" not in html
    assert "onsubmit=" not in html
    assert "onload=" not in html
    assert html.count("<script") == html.count("<script src=")


def test_session_cookie_flags(client, login, users):
    response = login(users["visitor"]["email"], users["visitor"]["password"])
    cookies = " ".join(response.headers.getlist("Set-Cookie"))
    assert "session=" in cookies
    assert "HttpOnly" in cookies
    assert "SameSite=Lax" in cookies


def test_logged_in_pages_are_not_cached(client, login, users):
    login(users["visitor"]["email"], users["visitor"]["password"])
    assert "no-store" in client.get("/my-bookings").headers["Cache-Control"]


def test_production_refuses_a_weak_secret_key():
    with pytest.raises(RuntimeError):
        create_app(
            {
                "APP_ENV": "production",
                "SECRET_KEY": "short",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
            }
        )


# ---------- injection and XSS ----------

def test_search_is_safe_from_sql_injection(client):
    response = client.get("/services", query_string={"q": "' OR 1=1 --"})
    assert response.status_code == 200
    assert b"0 services found" in response.data


def test_login_is_safe_from_sql_injection(client, login, users):
    login("' OR '1'='1' --", "anything")
    assert client.get("/my-bookings").status_code == 302

    login(users["visitor"]["email"], "' OR '1'='1")
    assert client.get("/my-bookings").status_code == 302


def test_search_text_is_escaped(client):
    payload = "<script>alert(1)</script>"
    html = client.get("/services", query_string={"q": payload}).get_data(as_text=True)
    assert payload not in html
    assert "&lt;script&gt;" in html


def test_user_name_is_escaped_in_the_navbar(client, login):
    client.post(
        "/register",
        data={
            "name": "<script>alert(1)</script>",
            "email": "xss@test.com",
            "password": "XssPass12345",
            "confirm_password": "XssPass12345",
        },
    )
    login("xss@test.com", "XssPass12345")
    html = client.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_invalid_filter_values_fall_back_to_defaults(client):
    response = client.get("/services?type=hacker&sort=anything")
    assert response.status_code == 200
    assert b"2 services found" in response.data


@pytest.mark.parametrize(
    "target",
    ["https://evil.example.com", "//evil.example.com", "javascript:alert(1)"],
)
def test_language_switch_never_redirects_off_site(client, target):
    response = client.get("/set-language/hi", query_string={"next": target})
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "evil" not in location
    assert "javascript" not in location


# ---------- access control ----------

@pytest.mark.parametrize("url", ADMIN_PAGES)
def test_anonymous_visitor_is_sent_to_login_for_admin_pages(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@pytest.mark.parametrize("url", ADMIN_PAGES)
def test_normal_visitor_gets_403_on_admin_pages(app, users, url):
    client = logged_in(app, users, "visitor")
    assert client.get(url).status_code == 403


@pytest.mark.parametrize(
    "url",
    [
        "/admin/bookings",
        "/admin/services",
        "/admin/services/new",
        "/admin/services/1/edit",
        "/admin/dashboard",
        "/admin/report.xlsx",
        "/admin/report.csv",
    ],
)
def test_admin_can_open_admin_pages(app, users, url):
    client = logged_in(app, users, "admin")
    assert client.get(url).status_code == 200


def test_visitor_cannot_create_or_edit_services(app, users):
    client = logged_in(app, users, "visitor")
    assert client.post("/admin/services/new", data=SERVICE_FORM).status_code == 403
    assert client.post("/admin/services/1/edit", data=SERVICE_FORM).status_code == 403
    with app.app_context():
        assert Service.query.count() == 2


def test_admin_service_form_rejects_a_zero_price(app, users):
    client = logged_in(app, users, "admin")
    data = dict(SERVICE_FORM, price="0")
    response = client.post("/admin/services/new", data=data)
    assert response.status_code == 200
    with app.app_context():
        assert Service.query.count() == 2


def test_admin_can_add_a_service_with_default_slots(app, users):
    client = logged_in(app, users, "admin")
    response = client.post("/admin/services/new", data=SERVICE_FORM)
    assert response.status_code == 302
    with app.app_context():
        service = Service.query.filter_by(name_en="Admin Added").one()
        assert Availability.query.filter_by(service_id=service.service_id).count() == 14


# ---------- reports ----------

@pytest.mark.parametrize(
    "query",
    [
        "start=abc&end=xyz",
        "start=2026-12-31&end=2026-11-01",
        "start=2000-01-01&end=2099-01-01",
    ],
)
def test_dashboard_handles_bad_dates(app, users, query):
    client = logged_in(app, users, "admin")
    assert client.get(f"/admin/dashboard?{query}").status_code == 200


def test_excel_report_is_a_real_workbook(app, users):
    client = logged_in(app, users, "admin")
    response = client.get("/admin/report.xlsx")
    assert response.status_code == 200
    assert response.data[:2] == b"PK"
    assert "attachment" in response.headers["Content-Disposition"]


def test_csv_report_neutralises_spreadsheet_formulas(app, users, slot_id):
    with app.app_context():
        evil = User(name="=1+1", email="evil@test.com", role="visitor")
        evil.set_password("EvilPass12345")
        db.session.add(evil)
        db.session.commit()
        hotel_id = Service.query.filter_by(name_en="Test Hotel").one().service_id

    client = app.test_client()
    client.post("/login", data={"email": "evil@test.com", "password": "EvilPass12345"})
    client.post(
        f"/service/{hotel_id}",
        data={"availability_id": slot_id("Test Hotel"), "quantity": 1},
    )

    admin = logged_in(app, users, "admin")
    text = admin.get("/admin/report.csv").get_data(as_text=True)
    assert "'=1+1" in text
    assert ",=1+1," not in text


# ---------- CSRF (these tests switch the protection ON) ----------

def test_login_without_csrf_token_is_refused(csrf_client):
    response = csrf_client.post(
        "/login", data={"email": "visitor@test.com", "password": "VisitorPass1"}
    )
    assert response.status_code == 400
    assert b"Session expired" in response.data


def test_forged_csrf_token_is_refused(csrf_client):
    csrf_client.get("/login")
    response = csrf_client.post(
        "/login",
        data={
            "email": "visitor@test.com",
            "password": "VisitorPass1",
            "csrf_token": "forged-token",
        },
    )
    assert response.status_code == 400


def test_register_without_csrf_token_is_refused(csrf_client):
    response = csrf_client.post(
        "/register",
        data={
            "name": "No Token",
            "email": "notoken@test.com",
            "password": "NoTokenPass123",
            "confirm_password": "NoTokenPass123",
        },
    )
    assert response.status_code == 400


def test_login_with_a_valid_token_works(csrf_client):
    token = get_token(csrf_client)
    response = csrf_client.post(
        "/login",
        data={
            "email": "visitor@test.com",
            "password": "VisitorPass1",
            "csrf_token": token,
        },
    )
    assert response.status_code == 302
    assert csrf_client.get("/my-bookings").status_code == 200


def test_logout_without_token_is_refused_and_keeps_the_session(csrf_client):
    token = get_token(csrf_client)
    csrf_client.post(
        "/login",
        data={
            "email": "visitor@test.com",
            "password": "VisitorPass1",
            "csrf_token": token,
        },
    )

    assert csrf_client.post("/logout").status_code == 400
    assert csrf_client.get("/my-bookings").status_code == 200

    page_token = get_token(csrf_client, "/")
    assert csrf_client.post("/logout", data={"csrf_token": page_token}).status_code == 302
    assert csrf_client.get("/my-bookings").status_code == 302