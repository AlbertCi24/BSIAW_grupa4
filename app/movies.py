from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .extensions import db
from .forms import CommentForm, MovieForm, ReviewForm
from .models import Comment, Movie, Review
from .security import forbid, log_event, require_owner_or_admin
from .storage import InvalidImage, sanitize_image

bp = Blueprint("movies", __name__)

PER_PAGE = 20


def _storage():
    return current_app.extensions["storage"]


def _flash_errors(form):
    for errors in form.errors.values():
        for error in errors:
            flash(error)


@bp.route("/")
def index():
    q = request.args.get("q", "").strip()[:100]
    page = max(request.args.get("page", 1, type=int), 1)
    stmt = (
        select(Movie, func.avg(Review.rating).label("avg_rating"), func.count(Review.id).label("review_count"))
        .outerjoin(Review, Review.movie_id == Movie.id)
        .group_by(Movie.id)
        .order_by(Movie.created_at.desc(), Movie.id.desc())
    )
    if q:
        # Parametr zapytania + autoescape znaków % i _. Zero sklejania SQL ze stringów.
        stmt = stmt.where(Movie.title.icontains(q, autoescape=True))
    rows = db.session.execute(stmt.limit(PER_PAGE + 1).offset((page - 1) * PER_PAGE)).all()
    has_next = len(rows) > PER_PAGE
    return render_template("movies/index.html", rows=rows[:PER_PAGE], q=q, page=page, has_next=has_next)


@bp.route("/movies/new", methods=["GET", "POST"])
@login_required
def new():
    form = MovieForm()
    if form.validate_on_submit():
        poster_filename = None
        if form.poster.data:
            try:
                data, extension = sanitize_image(form.poster.data.stream)
            except InvalidImage as exc:
                log_event("poster_rejected", filename=form.poster.data.filename)
                form.poster.errors.append(str(exc))
                return render_template("movies/new.html", form=form)
            poster_filename = _storage().save(data, extension)
        movie = Movie(
            title=form.title.data.strip(),
            year=form.year.data,
            description=form.description.data,
            poster_filename=poster_filename,
            added_by=current_user,
        )
        db.session.add(movie)
        db.session.commit()
        flash("Film dodany.")
        return redirect(url_for("movies.detail", movie_id=movie.id))
    return render_template("movies/new.html", form=form)


@bp.route("/movies/<int:movie_id>")
def detail(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    reviews = db.session.scalars(
        select(Review)
        .where(Review.movie_id == movie.id)
        .options(selectinload(Review.author), selectinload(Review.comments).selectinload(Comment.author))
        .order_by(Review.created_at.desc())
    ).all()
    avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else None
    own_review = None
    if current_user.is_authenticated:
        own_review = next((r for r in reviews if r.user_id == current_user.id), None)
    return render_template(
        "movies/detail.html",
        movie=movie,
        reviews=reviews,
        avg_rating=avg_rating,
        own_review=own_review,
        review_form=ReviewForm(),
        comment_form=CommentForm(),
    )


@bp.post("/movies/<int:movie_id>/delete")
@login_required
def delete(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    require_owner_or_admin(movie.added_by_id)
    poster = movie.poster_filename
    db.session.delete(movie)
    db.session.commit()
    _storage().delete(poster)
    log_event("movie_deleted", movie_id=movie_id)
    flash("Film usunięty.")
    return redirect(url_for("movies.index"))


@bp.route("/posters/<filename>")
def poster(filename):
    return _storage().send(filename)


@bp.post("/movies/<int:movie_id>/reviews")
@login_required
def add_review(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    form = ReviewForm()
    if not form.validate_on_submit():
        _flash_errors(form)
        return redirect(url_for("movies.detail", movie_id=movie.id))
    review = Review(author=current_user, movie=movie, rating=form.rating.data, content=form.content.data)
    db.session.add(review)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Masz już recenzję tego filmu, możesz ją edytować.")
    else:
        flash("Recenzja dodana.")
    return redirect(url_for("movies.detail", movie_id=movie.id))


@bp.route("/reviews/<int:review_id>/edit", methods=["GET", "POST"])
@login_required
def edit_review(review_id):
    review = db.get_or_404(Review, review_id)
    # Edytować może tylko autor (admin może usuwać, ale nie przepisywać cudzych recenzji).
    if review.user_id != current_user.id:
        forbid()
    form = ReviewForm(obj=review)
    if form.validate_on_submit():
        review.rating = form.rating.data
        review.content = form.content.data
        db.session.commit()
        flash("Recenzja zapisana.")
        return redirect(url_for("movies.detail", movie_id=review.movie_id))
    return render_template("movies/edit_review.html", form=form, review=review)


@bp.post("/reviews/<int:review_id>/delete")
@login_required
def delete_review(review_id):
    review = db.get_or_404(Review, review_id)
    require_owner_or_admin(review.user_id)
    movie_id = review.movie_id
    db.session.delete(review)
    db.session.commit()
    log_event("review_deleted", review_id=review_id)
    flash("Recenzja usunięta.")
    return redirect(url_for("movies.detail", movie_id=movie_id))


@bp.post("/reviews/<int:review_id>/comments")
@login_required
def add_comment(review_id):
    review = db.get_or_404(Review, review_id)
    form = CommentForm()
    if form.validate_on_submit():
        db.session.add(Comment(author=current_user, review=review, content=form.content.data))
        db.session.commit()
        flash("Komentarz dodany.")
    else:
        _flash_errors(form)
    return redirect(url_for("movies.detail", movie_id=review.movie_id, _anchor=f"review-{review.id}"))


@bp.post("/comments/<int:comment_id>/delete")
@login_required
def delete_comment(comment_id):
    comment = db.get_or_404(Comment, comment_id)
    require_owner_or_admin(comment.user_id)
    movie_id = comment.review.movie_id
    db.session.delete(comment)
    db.session.commit()
    log_event("comment_deleted", comment_id=comment_id)
    flash("Komentarz usunięty.")
    return redirect(url_for("movies.detail", movie_id=movie_id))
