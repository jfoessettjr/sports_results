import os
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy import extract

# ------------------------------------
# DB + Admin Config
# ------------------------------------
db = SQLAlchemy()

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")


# ------------------------------------
# Models
# ------------------------------------
class NascarRace(db.Model):
    __tablename__ = "nascar_races"

    id = db.Column(db.Integer, primary_key=True)
    race_date = db.Column(db.Date, nullable=False)
    track = db.Column(db.String(100), nullable=False)
    series = db.Column(db.String(50))
    race_name = db.Column(db.String(150))
    winner = db.Column(db.String(100), nullable=False)
    start_position = db.Column(db.Integer)
    finish_position = db.Column(db.Integer)
    laps_led = db.Column(db.Integer)
    notes = db.Column(db.Text)

    # images / car info
    car_number = db.Column(db.String(10))
    car_image_url = db.Column(db.String(255))


class PgaResult(db.Model):
    __tablename__ = "pga_results"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    tournament_name = db.Column(db.String(150), nullable=False)
    course = db.Column(db.String(150))
    finish_position = db.Column(db.Integer)
    score_to_par = db.Column(db.Integer)
    notes = db.Column(db.Text)

    # winner info
    winner = db.Column(db.String(100))
    winner_image_url = db.Column(db.String(255))


class NflGame(db.Model):
    """
    Steelers games only.
    """
    __tablename__ = "nfl_games"

    id = db.Column(db.Integer, primary_key=True)
    game_date = db.Column(db.Date, nullable=False)
    opponent = db.Column(db.String(100), nullable=False)
    home_away = db.Column(db.String(10))  # "Home" / "Away"
    steelers_score = db.Column(db.Integer)
    opponent_score = db.Column(db.Integer)
    notes = db.Column(db.Text)


class NhlGame(db.Model):
    """
    Penguins games only.
    """
    __tablename__ = "nhl_games"

    id = db.Column(db.Integer, primary_key=True)
    game_date = db.Column(db.Date, nullable=False)
    opponent = db.Column(db.String(100), nullable=False)
    home_away = db.Column(db.String(10))  # "Home" / "Away"
    penguins_score = db.Column(db.Integer)
    opponent_score = db.Column(db.Integer)
    notes = db.Column(db.Text)


# ------------------------------------
# App Factory
# ------------------------------------
def create_app():
    app = Flask(__name__)

    # Secret key for sessions (admin login)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

    # Database URL (Neon / Render)
    db_uri = os.environ.get("DATABASE_URL")
    if db_uri is None:
        # fallback for local dev if env var not set
        db_uri = "sqlite:///sports_results.db"
    # fix old postgres:// scheme if present
    if db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # --------------------------------
    # Admin decorator
    # --------------------------------
    def require_admin(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("is_admin"):
                return redirect(url_for("admin_login", next=request.path))
            return view(*args, **kwargs)

        return wrapped

    # --------------------------------
    # Auth / Admin routes
    # --------------------------------
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        error = None
        if request.method == "POST":
            password = request.form.get("password")
            if password == ADMIN_PASSWORD:
                session["is_admin"] = True
                next_url = request.args.get("next") or url_for("index")
                return redirect(next_url)
            else:
                error = "Invalid admin password"
        return render_template("admin_login.html", error=error)

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("is_admin", None)
        return redirect(url_for("index"))

    # --------------------------------
    # Helper: parse date from form
    # --------------------------------
    def parse_date(field_name):
        value = request.form.get(field_name)
        if not value:
            return None
        # Expect YYYY-MM-DD
        return datetime.strptime(value, "%Y-%m-%d").date()

    # --------------------------------
    # Index
    # --------------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    # --------------------------------
    # NASCAR
    # --------------------------------
    @app.route("/nascar")
    def nascar_list():
        series = request.args.get("series") or None
        track_filter = request.args.get("track") or ""

        query = NascarRace.query

        if series:
            query = query.filter(NascarRace.series == series)
        if track_filter:
            like_str = f"%{track_filter}%"
            query = query.filter(NascarRace.track.ilike(like_str))

        races = query.order_by(NascarRace.race_date.desc()).all()

        series_rows = (
            db.session.query(NascarRace.series)
            .distinct()
            .order_by(NascarRace.series)
            .all()
        )
        series_list = [s[0] for s in series_rows if s[0]]

        return render_template(
            "nascar_list.html",
            races=races,
            series_list=series_list,
            selected_series=series,
            track_filter=track_filter,
        )

    @app.route("/nascar/add", methods=["GET", "POST"])
    @require_admin
    def nascar_add():
        if request.method == "POST":
            race_date = parse_date("race_date")
            if race_date is None:
                # Simple guard; you can make this fancier later
                return "Race date is required", 400

            def to_int(name):
                val = request.form.get(name)
                return int(val) if val else None

            race = NascarRace(
                race_date=race_date,
                track=request.form.get("track"),
                series=request.form.get("series") or None,
                race_name=request.form.get("race_name") or None,
                winner=request.form.get("winner"),
                start_position=to_int("start_position"),
                finish_position=to_int("finish_position"),
                laps_led=to_int("laps_led"),
                notes=request.form.get("notes") or None,
                car_number=request.form.get("car_number") or None,
                car_image_url=request.form.get("car_image_url") or None,
            )
            db.session.add(race)
            db.session.commit()
            return redirect(url_for("nascar_list"))

        return render_template("nascar_add.html")

    @app.route("/nascar/<int:race_id>/edit", methods=["GET", "POST"])
    @require_admin
    def nascar_edit(race_id):
        race = NascarRace.query.get_or_404(race_id)

        if request.method == "POST":
            race_date = parse_date("race_date")
            if race_date is not None:
                race.race_date = race_date

            def to_int(name):
                val = request.form.get(name)
                return int(val) if val else None

            race.track = request.form.get("track")
            race.series = request.form.get("series") or None
            race.race_name = request.form.get("race_name") or None
            race.winner = request.form.get("winner")
            race.start_position = to_int("start_position")
            race.finish_position = to_int("finish_position")
            race.laps_led = to_int("laps_led")
            race.notes = request.form.get("notes") or None
            race.car_number = request.form.get("car_number") or None
            race.car_image_url = request.form.get("car_image_url") or None

            db.session.commit()
            return redirect(url_for("nascar_list"))

        return render_template("nascar_edit.html", race=race)

    @app.route("/nascar/<int:race_id>/delete", methods=["POST"])
    @require_admin
    def nascar_delete(race_id):
        race = NascarRace.query.get_or_404(race_id)
        db.session.delete(race)
        db.session.commit()
        return redirect(url_for("nascar_list"))

    # --------------------------------
    # PGA
    # --------------------------------
    @app.route("/pga")
    def pga_list():
        year = request.args.get("year") or None
        tournament_filter = request.args.get("tournament") or ""

        query = PgaResult.query

        if year:
            try:
                yr = int(year)
                query = query.filter(PgaResult.year == yr)
            except ValueError:
                pass

        if tournament_filter:
            like_str = f"%{tournament_filter}%"
            query = query.filter(PgaResult.tournament_name.ilike(like_str))

        results = query.order_by(
            PgaResult.year.desc(), PgaResult.tournament_name.asc()
        ).all()

        year_rows = (
            db.session.query(PgaResult.year)
            .distinct()
            .order_by(PgaResult.year.desc())
            .all()
        )
        years = [y[0] for y in year_rows if y[0]]

        return render_template(
            "pga_list.html",
            results=results,
            years=years,
            selected_year=year,
            tournament_filter=tournament_filter,
        )

    @app.route("/pga/add", methods=["GET", "POST"])
    @require_admin
    def pga_add():
        if request.method == "POST":
            def to_int(name):
                val = request.form.get(name)
                return int(val) if val else None

            result = PgaResult(
                year=to_int("year"),
                tournament_name=request.form.get("tournament_name"),
                course=request.form.get("course") or None,
                finish_position=to_int("finish_position"),
                score_to_par=to_int("score_to_par"),
                notes=request.form.get("notes") or None,
                winner=request.form.get("winner") or None,
                winner_image_url=request.form.get("winner_image_url") or None,
            )
            db.session.add(result)
            db.session.commit()
            return redirect(url_for("pga_list"))

        return render_template("pga_add.html")

    @app.route("/pga/<int:result_id>/edit", methods=["GET", "POST"])
    @require_admin
    def pga_edit(result_id):
        result = PgaResult.query.get_or_404(result_id)

        if request.method == "POST":
            def to_int(name):
                val = request.form.get(name)
                return int(val) if val else None

            result.year = to_int("year") or result.year
            result.tournament_name = request.form.get("tournament_name")
            result.course = request.form.get("course") or None
            result.finish_position = to_int("finish_position")
            result.score_to_par = to_int("score_to_par")
            result.notes = request.form.get("notes") or None
            result.winner = request.form.get("winner") or None
            result.winner_image_url = request.form.get("winner_image_url") or None

            db.session.commit()
            return redirect(url_for("pga_list"))

        return render_template("pga_edit.html", result=result)

    @app.route("/pga/<int:result_id>/delete", methods=["POST"])
    @require_admin
    def pga_delete(result_id):
        result = PgaResult.query.get_or_404(result_id)
        db.session.delete(result)
        db.session.commit()
        return redirect(url_for("pga_list"))

    # --------------------------------
    # NFL (Steelers only)
    # --------------------------------
    @app.route("/nfl")
    def nfl_list():
        opponent_filter = request.args.get("opponent") or ""
        season = request.args.get("season") or None

        query = NflGame.query

        if opponent_filter:
            like_str = f"%{opponent_filter}%"
            query = query.filter(NflGame.opponent.ilike(like_str))

        if season:
            try:
                yr = int(season)
                query = query.filter(extract("year", NflGame.game_date) == yr)
            except ValueError:
                pass

        games = query.order_by(NflGame.game_date.desc()).all()

        year_rows = (
            db.session.query(extract("year", NflGame.game_date).label("year"))
            .distinct()
            .order_by("year")
            .all()
        )
        seasons = [int(row.year) for row in year_rows if row.year is not None]

        return render_template(
            "nfl_list.html",
            games=games,
            seasons=seasons,
            selected_season=season,
            opponent_filter=opponent_filter,
        )

    @app.route("/nfl/add", methods=["GET", "POST"])
    @require_admin
    def nfl_add():
        if request.method == "POST":
            game_date = parse_date("game_date")
            if game_date is None:
                return "Game date is required", 400

            def to_int(name):
                val = request.form.get(name)
                return int(val) if val else None

            game = NflGame(
                game_date=game_date,
                opponent=request.form.get("opponent"),
                home_away=request.form.get("home_away") or None,
                steelers_score=to_int("steelers_score"),
                opponent_score=to_int("opponent_score"),
                notes=request.form.get("notes") or None,
            )
            db.session.add(game)
            db.session.commit()
            return redirect(url_for("nfl_list"))

        return render_template("nfl_add.html")

    # --------------------------------
    # NHL (Penguins only)
    # --------------------------------
    @app.route("/nhl")
    def nhl_list():
        opponent_filter = request.args.get("opponent") or ""
        season = request.args.get("season") or None

        query = NhlGame.query

        if opponent_filter:
            like_str = f"%{opponent_filter}%"
            query = query.filter(NhlGame.opponent.ilike(like_str))

        if season:
            try:
                yr = int(season)
                query = query.filter(extract("year", NhlGame.game_date) == yr)
            except ValueError:
                pass

        games = query.order_by(NhlGame.game_date.desc()).all()

        year_rows = (
            db.session.query(extract("year", NhlGame.game_date).label("year"))
            .distinct()
            .order_by("year")
            .all()
        )
        seasons = [int(row.year) for row in year_rows if row.year is not None]

        return render_template(
            "nhl_list.html",
            games=games,
            seasons=seasons,
            selected_season=season,
            opponent_filter=opponent_filter,
        )

    @app.route("/nhl/add", methods=["GET", "POST"])
    @require_admin
    def nhl_add():
        if request.method == "POST":
            game_date = parse_date("game_date")
            if game_date is None:
                return "Game date is required", 400

            def to_int(name):
                val = request.form.get(name)
                return int(val) if val else None

            game = NhlGame(
                game_date=game_date,
                opponent=request.form.get("opponent"),
                home_away=request.form.get("home_away") or None,
                penguins_score=to_int("penguins_score"),
                opponent_score=to_int("opponent_score"),
                notes=request.form.get("notes") or None,
            )
            db.session.add(game)
            db.session.commit()
            return redirect(url_for("nhl_list"))

        return render_template("nhl_add.html")

    return app


# Exposed for gunicorn: "gunicorn app:app"
app = create_app()

if __name__ == "__main__":
    # Local development only
    with app.app_context():
        db.create_all()
    app.run(debug=True)
