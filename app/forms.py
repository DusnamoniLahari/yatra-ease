from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, SelectField
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, ValidationError, NumberRange
)
from app.models import User


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=64)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Register")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("This email is already registered.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class BookingForm(FlaskForm):
    availability_id = SelectField("Date and time", coerce=int, validators=[DataRequired()])
    quantity = IntegerField(
        "Quantity",
        default=1,
        validators=[DataRequired(), NumberRange(min=1, max=10)],
    )
    submit = SubmitField("Book now")