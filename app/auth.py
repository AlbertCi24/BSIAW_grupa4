from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, limiter
from .forms import LoginForm, RegisterForm
from .models import Review, User
from .security import log_event

bp = Blueprint("auth", __name__)

# Porównanie z atrapą, gdy użytkownik nie istnieje, żeby czas odpowiedzi
# nie zdradzał, które loginy są w bazie.
_DUMMY_HASH = generate_password_hash("timing-equalizer")


def _safe_next(target):
    """Przekierowanie po logowaniu tylko na ścieżkę w obrębie aplikacji (open redirect)."""
    if target:
        parts = urlsplit(target)
        if (
            not parts.scheme
            and not parts.netloc
            and target.startswith("/")
            and not target.startswith("//")
            and "\\" not in target
        ):
            return target
    return url_for("movies.index")


def _find_user(username):
    return db.session.scalar(select(User).where(func.lower(User.username) == username.lower()))


def _redirected(response):
    return response.status_code == 302


def _not_redirected(response):
    return response.status_code != 302


# Na uczelni cała grupa wychodzi z jednego IP, więc liczymy tylko udane
# rejestracje i tylko nieudane logowania (sukces kończy się przekierowaniem).
@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"], deduct_when=_redirected)
def register():
    if current_user.is_authenticated:
        return redirect(url_for("movies.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if _find_user(form.username.data):
            form.username.errors.append("Ta nazwa jest już zajęta.")
        elif db.session.scalar(select(User).where(User.email == email)):
            form.email.errors.append("Ten e-mail jest już zarejestrowany.")
        else:
            user = User(username=form.username.data, email=email)
            user.set_password(form.password.data)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Nie udało się założyć konta, spróbuj innej nazwy lub e-maila.")
            else:
                log_event("register", username=user.username)
                flash("Konto założone, możesz się zalogować.")
                return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"], deduct_when=_not_redirected)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("movies.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = _find_user(form.username.data)
        password_ok = check_password_hash(user.password_hash if user else _DUMMY_HASH, form.password.data)
        if user is None or not password_ok:
            log_event("login_failed", username=form.username.data)
            flash("Nieprawidłowa nazwa użytkownika lub hasło.")
        elif not user.is_active:
            log_event("login_blocked", username=user.username)
            flash("To konto jest zablokowane.")
        else:
            session.clear()
            login_user(user)
            session.permanent = True
            log_event("login_success")
            return redirect(_safe_next(request.args.get("next")))
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    log_event("logout")
    logout_user()
    session.clear()
    flash("Wylogowano.")
    return redirect(url_for("movies.index"))


@bp.route("/users/<username>")
def profile(username):
    user = _find_user(username)
    if user is None:
        return render_template("errors.html", code=404, message="Nie ma takiego użytkownika."), 404
    reviews = db.session.scalars(
        select(Review).where(Review.user_id == user.id).order_by(Review.created_at.desc())
    ).all()
    return render_template("auth/profile.html", user=user, reviews=reviews)
