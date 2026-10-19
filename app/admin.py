from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from .extensions import db
from .models import User
from .security import admin_required, log_event

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
@admin_required
def index():
    users = db.session.scalars(select(User).order_by(User.created_at)).all()
    return render_template("admin/index.html", users=users)


@bp.post("/users/<int:user_id>/toggle-active")
@login_required
@admin_required
def toggle_active(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("Nie możesz zablokować samego siebie.")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        log_event("user_blocked" if not user.is_active else "user_unblocked", target=user.username)
        flash(f"Konto {user.username} {'odblokowane' if user.is_active else 'zablokowane'}.")
    return redirect(url_for("admin.index"))
