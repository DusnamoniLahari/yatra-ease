from datetime import date, timedelta

from app import db
from app.models import User, Service, Availability, Booking


def logged_in_client(app, users, who):
    client = app.test_client()
    client.post(
        "/login",
        data={"email": users[who]["email"], "password": users[who]["password"]},
    )
    return client


def service_id(app, name):
    with app.app_context():
        return Service.query.filter_by(name_en=name).one().service_id


def book(client, sid, slot, quantity=1, **extra):
    data = {"availability_id": slot, "quantity": quantity}
    data.update(extra)
    return client.post(f"/service/{sid}", data=data)


def booking_rows(app):
    with app.app_context():
        return [
            {
                "id": b.booking_id,
                "user_id": b.user_id,
                "quantity": b.quantity,
                "total_price": b.total_price,
                "status": b.status,
            }
            for b in Booking.query.order_by(Booking.booking_id).all()
        ]


def test_logged_out_visitor_cannot_book(app, client, slot_id, booked_count):
    slot = slot_id("Test Hotel")
    response = book(client, service_id(app, "Test Hotel"), slot)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert booking_rows(app) == []
    assert booked_count(slot) == 0


def test_price_is_calculated_on_the_server(app, users, slot_id, booked_count):
    client = logged_in_client(app, users, "visitor")
    slot = slot_id("Test Hotel")

    response = book(client, service_id(app, "Test Hotel"), slot, quantity=2, total_price=1)

    rows = booking_rows(app)
    assert len(rows) == 1
    assert rows[0]["total_price"] == 2000
    assert rows[0]["quantity"] == 2
    assert rows[0]["status"] == "confirmed"
    assert booked_count(slot) == 2
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/booking/{rows[0]['id']}/confirmation")


def test_invalid_quantities_are_rejected(app, users, slot_id, booked_count):
    client = logged_in_client(app, users, "visitor")
    slot = slot_id("Test Hotel")
    sid = service_id(app, "Test Hotel")

    for bad in ("0", "11", "-3", "abc"):
        response = book(client, sid, slot, quantity=bad)
        assert response.status_code == 200

    assert booking_rows(app) == []
    assert booked_count(slot) == 0


def test_cannot_overbook_remaining_seats(app, users, slot_id, booked_count):
    client = logged_in_client(app, users, "visitor")
    slot = slot_id("Test Hotel")
    sid = service_id(app, "Test Hotel")

    assert book(client, sid, slot, quantity=3).status_code == 302
    assert booked_count(slot) == 3

    response = book(client, sid, slot, quantity=3)
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/service/{sid}")
    assert booked_count(slot) == 3
    assert len(booking_rows(app)) == 1


def test_full_slot_is_no_longer_offered(app, users, slot_id, booked_count):
    client = logged_in_client(app, users, "visitor")
    slot = slot_id("Test Hotel")
    sid = service_id(app, "Test Hotel")

    book(client, sid, slot, quantity=5)
    assert booked_count(slot) == 5

    response = book(client, sid, slot, quantity=1)
    assert response.status_code == 200
    assert booked_count(slot) == 5
    assert len(booking_rows(app)) == 1


def test_slot_of_another_service_cannot_be_used(app, users, slot_id, booked_count):
    client = logged_in_client(app, users, "visitor")
    bus_slot = slot_id("Test Bus")

    response = book(client, service_id(app, "Test Hotel"), bus_slot)

    assert response.status_code == 200
    assert booking_rows(app) == []
    assert booked_count(bus_slot) == 0


def test_confirmation_page_is_private(app, users, slot_id):
    owner = logged_in_client(app, users, "visitor")
    book(owner, service_id(app, "Test Hotel"), slot_id("Test Hotel"))
    booking_id = booking_rows(app)[0]["id"]
    url = f"/booking/{booking_id}/confirmation"

    owner_response = owner.get(url)
    assert owner_response.status_code == 200
    assert b"Booking confirmed" in owner_response.data

    other = logged_in_client(app, users, "other")
    assert other.get(url).status_code == 404

    anonymous = app.test_client()
    assert anonymous.get(url).status_code == 302


def test_my_bookings_shows_only_own_bookings(app, users, slot_id):
    owner = logged_in_client(app, users, "visitor")
    book(owner, service_id(app, "Test Bus"), slot_id("Test Bus"))

    assert b"Test Bus" in owner.get("/my-bookings").data

    other = logged_in_client(app, users, "other")
    page = other.get("/my-bookings")
    assert b"Test Bus" not in page.data
    assert b"You have no bookings yet." in page.data


def test_cancelling_returns_the_seats(app, users, slot_id, booked_count):
    client = logged_in_client(app, users, "visitor")
    slot = slot_id("Test Hotel")
    book(client, service_id(app, "Test Hotel"), slot, quantity=2)
    booking_id = booking_rows(app)[0]["id"]
    assert booked_count(slot) == 2

    response = client.post(f"/booking/{booking_id}/cancel")

    assert response.status_code == 302
    assert booking_rows(app)[0]["status"] == "cancelled"
    assert booked_count(slot) == 0


def test_cancelling_twice_does_not_refund_twice(app, users, slot_id, booked_count):
    client = logged_in_client(app, users, "visitor")
    slot = slot_id("Test Hotel")
    sid = service_id(app, "Test Hotel")
    book(client, sid, slot, quantity=2)
    book(client, sid, slot, quantity=1)
    first_id = booking_rows(app)[0]["id"]
    assert booked_count(slot) == 3

    client.post(f"/booking/{first_id}/cancel")
    assert booked_count(slot) == 1

    client.post(f"/booking/{first_id}/cancel")
    assert booked_count(slot) == 1


def test_cannot_cancel_someone_elses_booking(app, users, slot_id, booked_count):
    owner = logged_in_client(app, users, "visitor")
    slot = slot_id("Test Hotel")
    book(owner, service_id(app, "Test Hotel"), slot, quantity=2)
    booking_id = booking_rows(app)[0]["id"]

    other = logged_in_client(app, users, "other")
    response = other.post(f"/booking/{booking_id}/cancel")

    assert response.status_code == 404
    assert booking_rows(app)[0]["status"] == "confirmed"
    assert booked_count(slot) == 2


def test_cancel_requires_post(app, users, slot_id):
    client = logged_in_client(app, users, "visitor")
    book(client, service_id(app, "Test Hotel"), slot_id("Test Hotel"))
    booking_id = booking_rows(app)[0]["id"]

    assert client.get(f"/booking/{booking_id}/cancel").status_code == 405
    assert booking_rows(app)[0]["status"] == "confirmed"


def test_past_booking_cannot_be_cancelled(app, users):
    with app.app_context():
        bus = Service.query.filter_by(name_en="Test Bus").one()
        visitor = User.query.filter_by(email=users["visitor"]["email"]).one()
        past_slot = Availability(
            service_id=bus.service_id,
            date=date.today() - timedelta(days=1),
            time_slot="Day 09:00",
            total_capacity=40,
            booked_count=1,
        )
        db.session.add(past_slot)
        db.session.flush()
        booking = Booking(
            user_id=visitor.user_id,
            availability_id=past_slot.availability_id,
            quantity=1,
            total_price=200,
            status="confirmed",
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.booking_id
        past_slot_id = past_slot.availability_id

    client = logged_in_client(app, users, "visitor")
    response = client.post(f"/booking/{booking_id}/cancel")

    assert response.status_code == 302
    assert booking_rows(app)[0]["status"] == "confirmed"
    with app.app_context():
        assert db.session.get(Availability, past_slot_id).booked_count == 1


def test_admin_can_cancel_any_booking_and_seats_return(app, users, slot_id, booked_count):
    visitor = logged_in_client(app, users, "visitor")
    slot = slot_id("Test Hotel")
    book(visitor, service_id(app, "Test Hotel"), slot, quantity=2)
    booking_id = booking_rows(app)[0]["id"]

    admin = logged_in_client(app, users, "admin")
    response = admin.post(f"/admin/bookings/{booking_id}/cancel")

    assert response.status_code == 302
    assert booking_rows(app)[0]["status"] == "cancelled"
    assert booked_count(slot) == 0


def test_visitor_cannot_use_admin_cancel(app, users, slot_id, booked_count):
    visitor = logged_in_client(app, users, "visitor")
    slot = slot_id("Test Hotel")
    book(visitor, service_id(app, "Test Hotel"), slot, quantity=2)
    booking_id = booking_rows(app)[0]["id"]

    response = visitor.post(f"/admin/bookings/{booking_id}/cancel")

    assert response.status_code == 403
    assert booking_rows(app)[0]["status"] == "confirmed"
    assert booked_count(slot) == 2