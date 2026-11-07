from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "error"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models  # noqa: F401  (registers the tables)
    from app.routes import main
    from app.auth import auth
    from app.translations import translate, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

    app.register_blueprint(main)
    app.register_blueprint(auth)

    @app.context_processor
    def inject_language():
        lang = session.get("lang")
        if lang not in SUPPORTED_LANGUAGES:
            if current_user.is_authenticated and current_user.preferred_language in SUPPORTED_LANGUAGES:
                lang = current_user.preferred_language
            else:
                lang = DEFAULT_LANGUAGE
        return {"lang": lang, "t": lambda key: translate(key, lang)}

    with app.app_context():
        db.create_all()

    return app