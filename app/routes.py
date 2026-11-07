from flask import Blueprint, render_template, redirect, url_for, session, request
from flask_login import current_user
from sqlalchemy import or_
from app import db
from app.models import Service
from app.translations import SUPPORTED_LANGUAGES
from app.auth import is_safe_url

main = Blueprint("main", __name__)

SERVICE_TYPES = ("bus", "hotel", "campsite", "attraction")

SORT_OPTIONS = {
    "default": Service.service_id.asc(),
    "price_low": Service.price.asc(),
    "price_high": Service.price.desc(),
    "name": Service.name_en.asc(),
}


@main.route("/")
def home():
    services = Service.query.order_by(Service.service_id).all()
    return render_template("home.html", services=services)


@main.route("/services")
def services():
    q = request.args.get("q", "").strip()[:100]
    selected_type = request.args.get("type", "")
    selected_sort = request.args.get("sort", "default")

    if selected_type not in SERVICE_TYPES:
        selected_type = ""
    if selected_sort not in SORT_OPTIONS:
        selected_sort = "default"

    query = Service.query

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Service.name_en.ilike(pattern),
                Service.name_hi.ilike(pattern),
                Service.location.ilike(pattern),
            )
        )

    if selected_type:
        query = query.filter(Service.type == selected_type)

    results = query.order_by(SORT_OPTIONS[selected_sort]).all()

    return render_template(
        "services.html",
        services=results,
        q=q,
        selected_type=selected_type,
        selected_sort=selected_sort,
        service_types=SERVICE_TYPES,
    )


@main.route("/set-language/<lang>")
def set_language(lang):
    if lang in SUPPORTED_LANGUAGES:
        session["lang"] = lang
        if current_user.is_authenticated:
            current_user.preferred_language = lang
            db.session.commit()

    next_page = request.args.get("next")
    if not is_safe_url(next_page):
        next_page = url_for("main.home")
    return redirect(next_page)