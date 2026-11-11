from flask import Flask, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from config import Config, DEV_SECRET

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "error"

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if app.config["APP_ENV"] == "production":
        key = app.config["SECRET_KEY"]
        if key == DEV_SECRET or len(key) < 32:
            raise RuntimeError("Set a strong SECRET_KEY (32+ characters) before running in production.")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models  # noqa: F401  (registers the tables)
    from app.routes import main
    from app.auth import auth
    from app.bookings import bookings
    from app.admin import admin
    from app.dashboard import dashboard
    from app.errors import errors
    from app.translations import translate, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(bookings)
    app.register_blueprint(admin)
    app.register_blueprint(dashboard)
    app.register_blueprint(errors)

    @app.context_processor
    def inject_language():
        lang = session.get("lang")
        if lang not in SUPPORTED_LANGUAGES:
            if current_user.is_authenticated and current_user.preferred_language in SUPPORTED_LANGUAGES:
                lang = current_user.preferred_language
            else:
                lang = DEFAULT_LANGUAGE
        return {"lang": lang, "t": lambda key: translate(key, lang)}

    @app.after_request
    def set_security_headers(response):
        if not (app.debug and response.status_code >= 500):
            response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.endpoint != "static" and current_user.is_authenticated:
            response.headers["Cache-Control"] = "no-store"
        return response

    with app.app_context():
        db.create_all()

    return app