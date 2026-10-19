from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import IntegerField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, Regexp

REQUIRED = "To pole jest wymagane."


class RegisterForm(FlaskForm):
    username = StringField(
        "Nazwa użytkownika",
        validators=[
            DataRequired(REQUIRED),
            Length(3, 32, "Od 3 do 32 znaków."),
            Regexp(r"^[A-Za-z0-9_]+$", message="Dozwolone są litery, cyfry i znak _."),
        ],
    )
    email = StringField(
        "E-mail",
        validators=[DataRequired(REQUIRED), Email("Niepoprawny adres e-mail."), Length(max=255)],
    )
    password = PasswordField(
        "Hasło (min. 8 znaków)", validators=[DataRequired(REQUIRED), Length(8, 128, "Od 8 do 128 znaków.")]
    )
    password2 = PasswordField(
        "Powtórz hasło", validators=[DataRequired(REQUIRED), EqualTo("password", "Hasła się różnią.")]
    )
    submit = SubmitField("Załóż konto")


class LoginForm(FlaskForm):
    username = StringField("Nazwa użytkownika", validators=[DataRequired(REQUIRED), Length(max=32)])
    password = PasswordField("Hasło", validators=[DataRequired(REQUIRED), Length(max=128)])
    submit = SubmitField("Zaloguj")


class MovieForm(FlaskForm):
    title = StringField("Tytuł", validators=[DataRequired(REQUIRED), Length(max=200)])
    year = IntegerField(
        "Rok produkcji", validators=[Optional(), NumberRange(1888, 2100, "Rok spoza zakresu.")]
    )
    description = TextAreaField("Opis", validators=[Optional(), Length(max=5000)])
    poster = FileField(
        "Plakat (JPG, PNG lub WEBP, max 2 MB)",
        validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Dozwolone formaty: JPG, PNG, WEBP.")],
    )
    submit = SubmitField("Dodaj film")


class ReviewForm(FlaskForm):
    rating = IntegerField(
        "Ocena (1-10)", validators=[DataRequired(REQUIRED), NumberRange(1, 10, "Ocena od 1 do 10.")]
    )
    content = TextAreaField(
        "Recenzja", validators=[DataRequired(REQUIRED), Length(max=5000, message="Maksymalnie 5000 znaków.")]
    )
    submit = SubmitField("Zapisz recenzję")


class CommentForm(FlaskForm):
    content = TextAreaField(
        "Komentarz", validators=[DataRequired(REQUIRED), Length(max=2000, message="Maksymalnie 2000 znaków.")]
    )
    submit = SubmitField("Dodaj komentarz")
