import os

import click
from flask import Flask, render_template
from markupsafe import Markup, escape
from sqlalchemy import func, select
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import csrf, db, limiter, login_manager, migrate
from .security import log_event, setup_security_logger
from .storage import LocalStorage


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    if not app.config["SECRET_KEY"] or not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("Brak SECRET_KEY lub DATABASE_URL. Skopiuj .env.example do .env i uzupełnij.")

    proxies = app.config["TRUSTED_PROXIES"]
    if proxies:
        # Za load balancerem prawdziwe IP klienta jest w X-Forwarded-For.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Zaloguj się, żeby zobaczyć tę stronę."
    # Sesja jest unieważniana, gdy zmieni się IP lub przeglądarka (utrudnia przejęcie ciasteczka).
    login_manager.session_protection = "strong"

    setup_security_logger()
    upload_folder = app.config["UPLOAD_FOLDER"] or os.path.join(app.instance_path, "uploads")
    app.extensions["storage"] = LocalStorage(upload_folder)

    from . import admin, auth, main, models, movies  # noqa: F401

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(movies.bp)
    app.register_blueprint(admin.bp)

    app.add_template_filter(nl2br)
    app.add_template_filter(format_dt, "dt")
    _register_error_handlers(app)
    _register_cli(app)
    return app


def nl2br(text):
    """Zamienia nowe linie na <br>, escapując całą resztę tekstu."""
    if not text:
        return ""
    return Markup("<br>\n").join(escape(line) for line in text.splitlines())


def format_dt(value):
    return value.strftime("%Y-%m-%d %H:%M") if value else ""


ERROR_MESSAGES = {
    400: "Niepoprawne żądanie (np. wygasł formularz, odśwież stronę).",
    403: "Brak uprawnień.",
    404: "Nie znaleziono strony.",
    413: "Plik jest za duży (max 2 MB).",
    429: "Za dużo prób. Odczekaj chwilę i spróbuj ponownie.",
    500: "Błąd serwera.",
}


def _register_error_handlers(app):
    def handler(error):
        code = getattr(error, "code", 500) or 500
        if code == 500:
            db.session.rollback()
        elif code == 429:
            log_event("rate_limited")
        return render_template("errors.html", code=code, message=ERROR_MESSAGES.get(code, "Błąd.")), code

    for code in ERROR_MESSAGES:
        app.register_error_handler(code, handler)


def _register_cli(app):
    from .models import User

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("email")
    @click.password_option()
    def create_admin(username, email, password):
        """Tworzy konto administratora albo nadaje rolę admina istniejącemu kontu."""
        user = db.session.scalar(select(User).where(func.lower(User.username) == username.lower()))
        if user is None:
            if len(password) < 8:
                raise click.ClickException("Hasło musi mieć co najmniej 8 znaków.")
            user = User(username=username, email=email.strip().lower())
            user.set_password(password)
            db.session.add(user)
        user.role = "admin"
        db.session.commit()
        click.echo(f"Admin: {user.username}")
