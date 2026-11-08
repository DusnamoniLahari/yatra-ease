import io
from datetime import timedelta

import pandas as pd
from flask import Blueprint, render_template, request, send_file
from flask_login import current_user

from app import reports
from app.admin import admin_required
from app.auth import log_action

dashboard = Blueprint("dashboard", __name__, url_prefix="/admin")

MAX_RANGE_DAYS = 366

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def report_range():
    default_start, default_end = reports.default_range()
    start = reports.parse_date(request.args.get("start"), default_start)
    end = reports.parse_date(request.args.get("end"), default_end)
    if end < start:
        start, end = end, start
    if (end - start).days > MAX_RANGE_DAYS:
        end = start + timedelta(days=MAX_RANGE_DAYS)
    return start, end


def safe_cell(value):
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def protect(df):
    out = df.copy()
    for col in out.columns:
        if not pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].map(safe_cell)
    return out


@dashboard.route("/dashboard")
@admin_required
def overview():
    start, end = report_range()
    df = reports.bookings_dataframe(start, end)
    return render_template(
        "admin_dashboard.html",
        start=start,
        end=end,
        totals=reports.summary(df),
        by_type=reports.revenue_by_type(df),
        daily=reports.daily_totals(df),
        occupancy=reports.occupancy_by_service(start, end),
    )


@dashboard.route("/report.xlsx")
@admin_required
def report_xlsx():
    start, end = report_range()
    df = reports.bookings_dataframe(start, end)
    totals = reports.summary(df)

    summary_df = pd.DataFrame(
        [
            ("Period", f"{start} to {end}"),
            ("Confirmed bookings", totals["bookings"]),
            ("Cancelled bookings", totals["cancelled"]),
            ("Seats sold", totals["seats"]),
            ("Revenue (INR)", totals["revenue"]),
        ],
        columns=["Metric", "Value"],
    )

    occupancy_df = pd.DataFrame(
        reports.occupancy_by_service(start, end),
        columns=["name", "type", "booked", "capacity", "percent"],
    ).rename(
        columns={
            "name": "Service",
            "type": "Type",
            "booked": "Booked seats",
            "capacity": "Total capacity",
            "percent": "Occupancy %",
        }
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        protect(df).to_excel(writer, sheet_name="Bookings", index=False)
        protect(occupancy_df).to_excel(writer, sheet_name="Occupancy", index=False)

        for sheet in writer.sheets.values():
            for column_cells in sheet.columns:
                longest = max(
                    len(str(cell.value)) if cell.value is not None else 0
                    for cell in column_cells
                )
                letter = column_cells[0].column_letter
                sheet.column_dimensions[letter].width = min(longest + 2, 45)

    buffer.seek(0)
    log_action(f"Admin downloaded Excel report {start} to {end}", current_user.user_id)
    return send_file(
        buffer,
        mimetype=XLSX_MIME,
        as_attachment=True,
        download_name=f"yatraease-report-{start}-to-{end}.xlsx",
    )


@dashboard.route("/report.csv")
@admin_required
def report_csv():
    start, end = report_range()
    df = reports.bookings_dataframe(start, end)

    csv_text = protect(df).to_csv(index=False)
    buffer = io.BytesIO(csv_text.encode("utf-8-sig"))

    log_action(f"Admin downloaded CSV report {start} to {end}", current_user.user_id)
    return send_file(
        buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"yatraease-report-{start}-to-{end}.csv",
    )