"""Log zdarzeń bezpieczeństwa (logowania, blokady, odmowy dostępu)."""

import logging
from functools import wraps

from flask import abort, request
from flask_login import current_user

logger = logging.getLogger("kinoteka.security")


def setup_security_logger():
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s SECURITY %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_event(event, **details):
    user = current_user.get_id() if current_user.is_authenticated else "-"
    # repr() escapuje znaki nowej linii, więc dane od użytkownika nie podrobią wpisów w logu.
    extra = " ".join(f"{key}={value!r}" for key, value in details.items())
    logger.info("event=%s user=%s ip=%s %s", event, user, request.remote_addr, extra)


def forbid():
    log_event("forbidden", path=request.path)
    abort(403)


def require_owner_or_admin(owner_id):
    if not (current_user.is_admin or current_user.id == owner_id):
        forbid()


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            forbid()
        return view(*args, **kwargs)

    return wrapped
