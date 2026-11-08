from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import Service, Availability, Booking
from app.forms import BookingForm
from app.auth import log_action

bookings = Blueprint("bookings", __name__)


def open_slots(service_id):
    return (
        Availability.query.filter(
            Availability.service_id == service_id,
            Availability.date >= date.today(),
            Availability.booked_count < Availability.total_capacity,
        )
        .order_by(Availability.date, Availability.time_slot)
        .all()
    )


@bookings.route("/service/<int:service_id>", methods=["GET", "POST"])
def service_detail(service_id):
    service = db.get_or_404(Service, service_id)
    slots = open_slots(service_id)

    form = BookingForm()
    form.availability_id.choices = [
        (s.availability_id, f"{s.date.strftime('%d %b %Y')} - {s.time_slot} ({s.remaining} left)")
        for s in slots
    ]

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("Please log in to book.", "error")
            return redirect(url_for("auth.login", next=request.path))

        slot_id = form.availability_id.data
        quantity = form.quantity.data

        updated = (
            Availability.query.filter(
                Availability.availability_id == slot_id,
                Availability.service_id == service_id,
                Availability.booked_count + quantity <= Availability.total_capacity,
            ).update(
                {Availability.booked_count: Availability.booked_count + quantity},
                synchronize_session=False,
            )
        )

        if updated != 1:
            db.session.rollback()
            flash("Sorry, not enough seats are left for that slot.", "error")
            return redirect(url_for("bookings.service_detail", service_id=service_id))

        booking = Booking(
            user_id=current_user.user_id,
            availability_id=slot_id,
            quantity=quantity,
            total_price=service.price * quantity,
            status="confirmed",
        )
        db.session.add(booking)
        db.session.commit()

        log_action(f"Booking {booking.booking_id} created", current_user.user_id)
        flash("Booking confirmed!", "success")
        return redirect(url_for("bookings.confirmation", booking_id=booking.booking_id))

    return render_template("service_detail.html", service=service, form=form, has_slots=bool(slots))


@bookings.route("/booking/<int:booking_id>/confirmation")
@login_required
def confirmation(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    if booking.user_id != current_user.user_id:
        abort(404)
    return render_template("confirmation.html", booking=booking, service=booking.slot.service)