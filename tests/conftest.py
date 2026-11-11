from datetime import date, timedelta

import pytest

from app import create_app, db
from app.models import User, Service, Availability

USERS = {
    "admin": ("Test Admin", "admin@test.com", "AdminPass12345", "admin"),
    "visitor": ("Test Visitor", "visitor@test.com", "VisitorPass1", "visitor"),
    "other": ("Other Visitor", "other@test.com", "OtherPass123", "visitor"),
}


def seed_test_data():
    for name, email, password, role in USERS.values():
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)

    hotel = Service(
        type="hotel",
        name_en="Test Hotel",
        name_hi="टेस्ट होटल",
        description_en="A hotel used only in tests.",
        description_hi="केवल टेस्ट के लिए होटल।",
        location="Hyderabad",
        price=1000,
    )
    bus = Service(
        type="bus",
        name_en="Test Bus",
        name_hi="टेस्ट बस",
        description_en="A bus used only in tests.",
        description_hi="केवल टेस्ट के लिए बस।",
        location="Vijayawada to Tirupati",
        price=200,
    )
    db.session.add_all([hotel, bus])
    db.session.flush()

    for service, capacity in ((hotel, 5), (bus, 40)):
        for day in range(3):
            db.session.add(
                Availability(
                    service_id=service.service_id,
                    date=date.today() + timedelta(days=day),
                    time_slot="Day 09:00",
                    total_capacity=capacity,
                )
            )
    db.session.commit()


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SECRET_KEY": "test-secret-key-used-only-in-tests-1234567890",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with app.app_context():
        seed_test_data()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def users():
    return {key: {"email": value[1], "password": value[2]} for key, value in USERS.items()}


@pytest.fixture
def login(client):
    def do_login(email, password):
        return client.post("/login", data={"email": email, "password": password})

    return do_login


@pytest.fixture
def slot_id(app):
    def find(service_name, offset_days=0):
        with app.app_context():
            service = Service.query.filter_by(name_en=service_name).one()
            slot = Availability.query.filter_by(
                service_id=service.service_id,
                date=date.today() + timedelta(days=offset_days),
            ).one()
            return slot.availability_id

    return find


@pytest.fixture
def booked_count(app):
    def find(availability_id):
        with app.app_context():
            return db.session.get(Availability, availability_id).booked_count

    return find