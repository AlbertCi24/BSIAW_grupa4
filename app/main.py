from flask import Blueprint
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db, limiter

bp = Blueprint("main", __name__)


@bp.route("/health")
@limiter.exempt
def health():
    """Health check dla load balancera: 200 gdy baza odpowiada, 503 gdy nie."""
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        return {"status": "db_error"}, 503
    return {"status": "ok"}
