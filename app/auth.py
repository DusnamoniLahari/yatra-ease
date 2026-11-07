from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.forms import RegisterForm, LoginForm
from app.models import User, AuditLog

auth = Blueprint("auth", __name__)


def log_action(action, user_id=None):
    db.session.add(AuditLog(user_id=user_id, action=action[:200]))
    db.session.commit()


def is_safe_url(target):
    if not target or target.startswith("//"):
        return False
    parts = urlparse(target)
    return parts.scheme == "" and parts.netloc == "" and target.startswith("/")


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        log_action("User registered", user.user_id)
        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            log_action("User logged in", user.user_id)
            next_page = request.args.get("next")
            if not is_safe_url(next_page):
                next_page = url_for("main.home")
            return redirect(next_page)

        log_action(f"Failed login attempt for {email}")
        flash("Invalid email or password.", "error")

    return render_template("login.html", form=form)


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    log_action("User logged out", current_user.user_id)
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))