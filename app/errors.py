from flask import Blueprint, render_template
from flask_wtf.csrf import CSRFError
from app import db

errors = Blueprint("errors", __name__)


def show(code, title, message):
    return render_template("error.html", code=code, title=title, message=message), code


@errors.app_errorhandler(400)
def bad_request(error):
    return show(400, "Bad request", "The request could not be understood. Please go back and try again.")


@errors.app_errorhandler(CSRFError)
def csrf_failed(error):
    return show(400, "Session expired", "Your form expired or was invalid. Please go back, refresh the page and try again.")


@errors.app_errorhandler(403)
def forbidden(error):
    return show(403, "Access denied", "You do not have permission to view this page.")


@errors.app_errorhandler(404)
def not_found(error):
    return show(404, "Page not found", "The page you are looking for does not exist.")


@errors.app_errorhandler(405)
def method_not_allowed(error):
    return show(405, "Not allowed", "This action is not allowed from this address.")


@errors.app_errorhandler(500)
def server_error(error):
    db.session.rollback()
    return show(500, "Something went wrong", "An unexpected error occurred. Please try again later.")