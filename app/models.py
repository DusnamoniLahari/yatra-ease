from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="visitor")
    preferred_language = db.Column(db.String(2), nullable=False, default="en")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Service(db.Model):
    __tablename__ = "services"

    service_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    name_en = db.Column(db.String(150), nullable=False)
    name_hi = db.Column(db.String(150), nullable=False)
    description_en = db.Column(db.Text, nullable=False)
    description_hi = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)

    availability = db.relationship("Availability", backref="service", lazy=True)


class Availability(db.Model):
    __tablename__ = "availability"

    availability_id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.service_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(30), nullable=False)
    total_capacity = db.Column(db.Integer, nullable=False)
    booked_count = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("service_id", "date", "time_slot", name="uq_service_date_slot"),
    )

    bookings = db.relationship("Booking", backref="slot", lazy=True)

    @property
    def remaining(self):
        return self.total_capacity - self.booked_count


class Booking(db.Model):
    __tablename__ = "bookings"

    booking_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    availability_id = db.Column(db.Integer, db.ForeignKey("availability.availability_id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(15), nullable=False, default="confirmed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)