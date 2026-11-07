from flask import Blueprint, render_template, redirect, url_for, session, request
from flask_login import current_user
from app import db
from app.models import Service
from app.translations import SUPPORTED_LANGUAGES
from app.auth import is_safe_url

main = Blueprint("main", __name__)


@main.route("/")
def home():
    services = Service.query.order_by(Service.service_id).all()
    return render_template("home.html", services=services)


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