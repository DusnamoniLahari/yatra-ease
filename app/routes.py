from flask import Blueprint, render_template
from app.models import Service

main = Blueprint("main", __name__)


@main.route("/")
def home():
    services = Service.query.order_by(Service.service_id).all()
    return render_template("home.html", services=services)