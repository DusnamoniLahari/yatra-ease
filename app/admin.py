from datetime import date, timedelta
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.models import User, Service, Availability, Booking
from app.forms import ServiceForm
from app.auth import log_action

admin = Blueprint("admin", __name__, url_prefix="/admin")

STATUSES = ("confirmed", "cancelled")
DEFAULT_SLOT = "Day 09:00"
DEFAULT_CAPACITY = 20
DAYS_AHEAD = 14


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@admin.route("/")
@admin_required
def index():
    return redirect(url_for("dashboard.overview"))


@admin.route("/bookings")
@admin_required
def bookings_list():
    q = request.args.get("q", "").strip()[:100]
    status = request.args.get("status", "")
    if status not in STATUSES:
        status = ""

    query = Booking.query.join(User, Booking.user_id == User.user_id)

    if q:
        pattern = f"%{q}%"
        conditions = [User.name.ilike(pattern), User.email.ilike(pattern)]
        if q.isdigit() and len(q) <= 9:
            conditions.append(Booking.booking_id == int(q))
        query = query.filter(or_(*conditions))

    if status:
        query = query.filter(Booking.status == status)

    results = query.order_by(Booking.created_at.desc()).limit(200).all()

    return render_template(
        "admin_bookings.html",
        bookings=results,
        q=q,
        status=status,
        statuses=STATUSES,
        today=date.today(),
    )


@admin.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@admin_required
def cancel_booking(booking_id):
    booking = db.get_or_404(Booking, booking_id)

    if booking.slot.date < date.today():
        flash("Past bookings cannot be cancelled.", "error")
        return redirect(url_for("admin.bookings_list"))

    changed = Booking.query.filter(
        Booking.booking_id == booking_id,
        Booking.status == "confirmed",
    ).update({Booking.status: "cancelled"}, synchronize_session=False)

    if changed != 1:
        db.session.rollback()
        flash("This booking is already cancelled.", "error")
        return redirect(url_for("admin.bookings_list"))

    Availability.query.filter(
        Availability.availability_id == booking.availability_id,
        Availability.booked_count >= booking.quantity,
    ).update(
        {Availability.booked_count: Availability.booked_count - booking.quantity},
        synchronize_session=False,
    )
    db.session.commit()

    log_action(f"Admin cancelled booking {booking_id}", current_user.user_id)
    flash(f"Booking #{booking_id} cancelled.", "success")
    return redirect(url_for("admin.bookings_list"))


@admin.route("/services")
@admin_required
def services_list():
    services = Service.query.order_by(Service.service_id).all()
    return render_template("admin_services.html", services=services)


@admin.route("/services/new", methods=["GET", "POST"])
@admin_required
def service_new():
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(
            type=form.type.data,
            name_en=form.name_en.data.strip(),
            name_hi=form.name_hi.data.strip(),
            description_en=form.description_en.data.strip(),
            description_hi=form.description_hi.data.strip(),
            location=form.location.data.strip(),
            price=form.price.data,
        )
        db.session.add(service)
        db.session.flush()

        for day in range(DAYS_AHEAD):
            db.session.add(
                Availability(
                    service_id=service.service_id,
                    date=date.today() + timedelta(days=day),
                    time_slot=DEFAULT_SLOT,
                    total_capacity=DEFAULT_CAPACITY,
                )
            )
        db.session.commit()

        log_action(f"Admin created service {service.service_id}", current_user.user_id)
        flash("Service created with default slots for the next 14 days.", "success")
        return redirect(url_for("admin.services_list"))

    return render_template("admin_service_form.html", form=form, title="Add service")


@admin.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@admin_required
def service_edit(service_id):
    service = db.get_or_404(Service, service_id)
    form = ServiceForm(obj=service)

    if form.validate_on_submit():
        service.type = form.type.data
        service.name_en = form.name_en.data.strip()
        service.name_hi = form.name_hi.data.strip()
        service.description_en = form.description_en.data.strip()
        service.description_hi = form.description_hi.data.strip()
        service.location = form.location.data.strip()
        service.price = form.price.data
        db.session.commit()

        log_action(f"Admin updated service {service_id}", current_user.user_id)
        flash("Service updated.", "success")
        return redirect(url_for("admin.services_list"))

    return render_template("admin_service_form.html", form=form, title="Edit service")