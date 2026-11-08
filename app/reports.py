from datetime import date, timedelta

import pandas as pd
from sqlalchemy import func

from app import db
from app.models import Booking, Availability, Service, User

COLUMNS = [
    "Booking ID", "Customer", "Email", "Service", "Type", "Service date",
    "Time slot", "Quantity", "Total (INR)", "Status", "Booked at",
]


def default_range():
    today = date.today()
    return today, today + timedelta(days=13)


def parse_date(value, fallback):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


def bookings_dataframe(start, end):
    rows = (
        db.session.query(
            Booking.booking_id,
            User.name,
            User.email,
            Service.name_en,
            Service.type,
            Availability.date,
            Availability.time_slot,
            Booking.quantity,
            Booking.total_price,
            Booking.status,
            Booking.created_at,
        )
        .join(User, Booking.user_id == User.user_id)
        .join(Availability, Booking.availability_id == Availability.availability_id)
        .join(Service, Availability.service_id == Service.service_id)
        .filter(Availability.date >= start, Availability.date <= end)
        .order_by(Availability.date, Booking.booking_id)
        .all()
    )
    data = [
        (
            r[0], r[1], r[2], r[3], r[4],
            r[5].isoformat(), r[6], r[7], r[8], r[9],
            r[10].strftime("%Y-%m-%d %H:%M"),
        )
        for r in rows
    ]
    return pd.DataFrame(data, columns=COLUMNS)


def confirmed_only(df):
    return df[df["Status"] == "confirmed"]


def summary(df):
    confirmed = confirmed_only(df)
    return {
        "bookings": int(len(confirmed)),
        "cancelled": int(len(df) - len(confirmed)),
        "seats": int(confirmed["Quantity"].sum()),
        "revenue": int(confirmed["Total (INR)"].sum()),
    }


def revenue_by_type(df):
    confirmed = confirmed_only(df)
    if confirmed.empty:
        return []
    grouped = (
        confirmed.groupby("Type")
        .agg(bookings=("Booking ID", "count"), revenue=("Total (INR)", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    return [
        {
            "type": row["Type"],
            "bookings": int(row["bookings"]),
            "revenue": int(row["revenue"]),
        }
        for _, row in grouped.iterrows()
    ]


def daily_totals(df):
    confirmed = confirmed_only(df)
    if confirmed.empty:
        return []
    grouped = (
        confirmed.groupby("Service date")
        .agg(bookings=("Booking ID", "count"), revenue=("Total (INR)", "sum"))
        .reset_index()
        .sort_values("Service date")
    )
    top = int(grouped["bookings"].max())
    return [
        {
            "date": row["Service date"],
            "bookings": int(row["bookings"]),
            "revenue": int(row["revenue"]),
            "bar": round(100 * int(row["bookings"]) / top),
        }
        for _, row in grouped.iterrows()
    ]


def occupancy_by_service(start, end):
    rows = (
        db.session.query(
            Service.name_en,
            Service.type,
            func.sum(Availability.booked_count),
            func.sum(Availability.total_capacity),
        )
        .join(Availability, Availability.service_id == Service.service_id)
        .filter(Availability.date >= start, Availability.date <= end)
        .group_by(Service.service_id, Service.name_en, Service.type)
        .order_by(Service.service_id)
        .all()
    )
    result = []
    for name, stype, booked, capacity in rows:
        booked = int(booked or 0)
        capacity = int(capacity or 0)
        percent = round(100 * booked / capacity, 1) if capacity else 0
        result.append(
            {
                "name": name,
                "type": stype,
                "booked": booked,
                "capacity": capacity,
                "percent": percent,
            }
        )
    return result