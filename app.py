import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

from models import db, NascarRace, NflGame, PgaResult, NhlGame


def create_app():
    app = Flask(__name__)

    # --- Config: DB + secrets ---
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL env var is not set")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "changeme")

    db.init_app(app)

    # ---------- Admin helper ----------

    def require_admin(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not session.get("is_admin"):
                next_url = request.path
                return redirect(url_for("admin_login", next=next_url))
            return view_func(*args, **kwargs)

        return wrapper

    # ---------- Routes ----------

    @app.route("/")
    def index():
        return render_template("index.html")

    # ---------- Admin login/logout ----------

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            password = request.form.get("password", "")
            if password == app.config["ADMIN_PASSWORD"]:
                session["is_admin"] = True
                flash("Logged in as admin.", "success")
                next_url = request.args.get("next") or url_for("index")
                return redirect(next_url)
            else:
                flash("Incorrect admin password.", "danger")

        return render_template("admin_login.html")

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("is_admin", None)
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    # ---------- NASCAR ----------

    @app.route("/nascar")
    def nascar_list():
        series = request.args.get("series") or None
        track = request.args.get("track") or None

        query = NascarRace.query

        if series:
            query = query.filter(NascarRace.series == series)
        if track:
            query = query.filter(NascarRace.track.ilike(f"%{track}%"))

        races = query.order_by(NascarRace.race_date.desc()).all()

        # For dropdown of series
        series_list = (
            db.session.query(NascarRace.series)
            .filter(NascarRace.series.isnot(None))
            .distinct()
            .order_by(NascarRace.series)
            .all()
        )
        series_list = [s[0] for s in series_list]

        return render_template(
            "nascar_list.html",
            races=races,
            series_list=series_list,
            selected_series=series,
            track_filter=track or "",
        )

    @app.route("/nascar/add", methods=["GET", "POST"])
    @require_admin
    def nascar_add():
        if request.method == "POST":
            race_date = datetime.strptime(request.form["race_date"], "%Y-%m-%d").date()
            race = NascarRace(
                race_date=race_date,
                track=request.form["track"],
                series=request.form.get("series") or None,
                race_name=request.form.get("race_name") or None,
                winner=request.form["winner"],
                start_position=int(request.form["start_position"])
                if request.form.get("start_position")
                else None,
                finish_position=int(request.form["finish_position"])
                if request.form.get("finish_position")
                else None,
                laps_led=int(request.form["laps_led"])
                if request.form.get("laps_led")
                else None,
                notes=request.form.get("notes") or None,
            )
            db.session.add(race)
            db.session.commit()
            flash("NASCAR race added.", "success")
            return redirect(url_for("nascar_list"))

        return render_template("nascar_add.html")
    
        @app.route("/nascar/<int:race_id>/edit", methods=["GET", "POST"])
    @require_admin
    def nascar_edit(race_id):
        race = NascarRace.query.get_or_404(race_id)

        if request.method == "POST":
            race.race_date = datetime.strptime(request.form["race_date"], "%Y-%m-%d").date()
            race.track = request.form["track"]
            race.series = request.form.get("series") or None
            race.race_name = request.form.get("race_name") or None
            race.winner = request.form["winner"]
            race.start_position = int(request.form["start_position"]) if request.form.get("start_position") else None
            race.finish_position = int(request.form["finish_position"]) if request.form.get("finish_position") else None
            race.laps_led = int(request.form["laps_led"]) if request.form.get("laps_led") else None
            race.notes = request.form.get("notes") or None

            db.session.commit()
            flash("NASCAR race updated.", "success")
            return redirect(url_for("nascar_list"))

        return render_template("nascar_edit.html", race=race)

    @app.route("/nascar/<int:race_id>/delete", methods=["POST"])
    @require_admin
    def nascar_delete(race_id):
        race = NascarRace.query.get_or_404(race_id)
        db.session.delete(race)
        db.session.commit()
        flash("NASCAR race deleted.", "info")
        return redirect(url_for("nascar_list"))


    # ---------- NFL (Steelers only) ----------

    @app.route("/nfl")
    def nfl_list():
        season = request.args.get("season", type=int)
        result = request.args.get("result") or None

        query = NflGame.query

        if season:
            query = query.filter(NflGame.season == season)
        if result:
            query = query.filter(NflGame.result == result)

        games = query.order_by(NflGame.game_date.desc()).all()

        seasons = (
            db.session.query(NflGame.season)
            .distinct()
            .order_by(NflGame.season.desc())
            .all()
        )
        seasons = [s[0] for s in seasons]

        return render_template(
            "nfl_list.html",
            games=games,
            seasons=seasons,
            selected_season=season,
            selected_result=result or "",
        )

    @app.route("/nfl/add", methods=["GET", "POST"])
    @require_admin
    def nfl_add():
        if request.method == "POST":
            game_date = datetime.strptime(request.form["game_date"], "%Y-%m-%d").date()
            steelers_score = int(request.form["steelers_score"])
            opponent_score = int(request.form["opponent_score"])

            if steelers_score > opponent_score:
                result = "W"
            elif steelers_score < opponent_score:
                result = "L"
            else:
                result = "T"

            game = NflGame(
                game_date=game_date,
                season=int(request.form["season"]),
                week=int(request.form["week"])
                if request.form.get("week")
                else None,
                opponent=request.form["opponent"],
                home_away=request.form["home_away"],
                steelers_score=steelers_score,
                opponent_score=opponent_score,
                result=result,
                notes=request.form.get("notes") or None,
            )
            db.session.add(game)
            db.session.commit()
            flash("Steelers game added.", "success")
            return redirect(url_for("nfl_list"))

        return render_template("nfl_add.html")

    @app.route("/nfl/<int:game_id>/edit", methods=["GET", "POST"])
    @require_admin
    def nfl_edit(game_id):
        game = NflGame.query.get_or_404(game_id)

        if request.method == "POST":
            game.game_date = datetime.strptime(request.form["game_date"], "%Y-%m-%d").date()
            game.season = int(request.form["season"])
            game.week = int(request.form["week"]) if request.form.get("week") else None
            game.opponent = request.form["opponent"]
            game.home_away = request.form["home_away"]

            steelers_score = int(request.form["steelers_score"])
            opponent_score = int(request.form["opponent_score"])
            game.steelers_score = steelers_score
            game.opponent_score = opponent_score

            if steelers_score > opponent_score:
                game.result = "W"
            elif steelers_score < opponent_score:
                game.result = "L"
            else:
                game.result = "T"

            game.notes = request.form.get("notes") or None

            db.session.commit()
            flash("Steelers game updated.", "success")
            return redirect(url_for("nfl_list"))

        return render_template("nfl_edit.html", game=game)

    @app.route("/nfl/<int:game_id>/delete", methods=["POST"])
    @require_admin
    def nfl_delete(game_id):
        game = NflGame.query.get_or_404(game_id)
        db.session.delete(game)
        db.session.commit()
        flash("Steelers game deleted.", "info")
        return redirect(url_for("nfl_list"))


    # ---------- PGA ----------

    @app.route("/pga")
    def pga_list():
        year = request.args.get("year", type=int)
        tournament = request.args.get("tournament") or None

        query = PgaResult.query

        if year:
            query = query.filter(PgaResult.year == year)
        if tournament:
            query = query.filter(
                PgaResult.tournament_name.ilike(f"%{tournament}%")
            )

        results = query.order_by(
            PgaResult.year.desc(), PgaResult.tournament_name
        ).all()

        years = (
            db.session.query(PgaResult.year)
            .distinct()
            .order_by(PgaResult.year.desc())
            .all()
        )
        years = [y[0] for y in years]

        return render_template(
            "pga_list.html",
            results=results,
            years=years,
            selected_year=year,
            tournament_filter=tournament or "",
        )

    @app.route("/pga/add", methods=["GET", "POST"])
    @require_admin
    def pga_add():
        if request.method == "POST":
            result = PgaResult(
                year=int(request.form["year"]),
                tournament_name=request.form["tournament_name"],
                course=request.form.get("course") or None,
                finish_position=int(request.form["finish_position"])
                if request.form.get("finish_position")
                else None,
                score_to_par=int(request.form["score_to_par"])
                if request.form.get("score_to_par")
                else None,
                notes=request.form.get("notes") or None,
            )
            db.session.add(result)
            db.session.commit()
            flash("PGA result added.", "success")
            return redirect(url_for("pga_list"))

        return render_template("pga_add.html")

    @app.route("/pga/<int:result_id>/edit", methods=["GET", "POST"])
    @require_admin
    def pga_edit(result_id):
        result = PgaResult.query.get_or_404(result_id)

        if request.method == "POST":
            result.year = int(request.form["year"])
            result.tournament_name = request.form["tournament_name"]
            result.course = request.form.get("course") or None
            result.finish_position = int(request.form["finish_position"]) if request.form.get("finish_position") else None
            result.score_to_par = int(request.form["score_to_par"]) if request.form.get("score_to_par") else None
            result.notes = request.form.get("notes") or None

            db.session.commit()
            flash("PGA result updated.", "success")
            return redirect(url_for("pga_list"))

        return render_template("pga_edit.html", result=result)

    @app.route("/pga/<int:result_id>/delete", methods=["POST"])
    @require_admin
    def pga_delete(result_id):
        result = PgaResult.query.get_or_404(result_id)
        db.session.delete(result)
        db.session.commit()
        flash("PGA result deleted.", "info")
        return redirect(url_for("pga_list"))


    # ---------- NHL (Penguins only) ----------

    @app.route("/nhl")
    def nhl_list():
        season = request.args.get("season") or None
        result = request.args.get("result") or None

        query = NhlGame.query

        if season:
            query = query.filter(NhlGame.season == season)
        if result:
            query = query.filter(NhlGame.result == result)

        games = query.order_by(NhlGame.game_date.desc()).all()

        seasons = (
            db.session.query(NhlGame.season)
            .distinct()
            .order_by(NhlGame.season.desc())
            .all()
        )
        seasons = [s[0] for s in seasons]

        return render_template(
            "nhl_list.html",
            games=games,
            seasons=seasons,
            selected_season=season or "",
            selected_result=result or "",
        )

    @app.route("/nhl/add", methods=["GET", "POST"])
    @require_admin
    def nhl_add():
        if request.method == "POST":
            game_date = datetime.strptime(request.form["game_date"], "%Y-%m-%d").date()
            penguins_goals = int(request.form["penguins_goals"])
            opponent_goals = int(request.form["opponent_goals"])

            if penguins_goals > opponent_goals:
                result = "W"
            elif penguins_goals < opponent_goals:
                # for now treat all losses the same, can add OTL later
                result = "L"
            else:
                result = "T"

            game = NhlGame(
                game_date=game_date,
                season=request.form["season"],
                opponent=request.form["opponent"],
                home_away=request.form["home_away"],
                penguins_goals=penguins_goals,
                opponent_goals=opponent_goals,
                result=result,
                notes=request.form.get("notes") or None,
            )
            db.session.add(game)
            db.session.commit()
            flash("Penguins game added.", "success")
            return redirect(url_for("nhl_list"))

        return render_template("nhl_add.html")

    return app


app = create_app()

    @app.route("/nhl/<int:game_id>/edit", methods=["GET", "POST"])
    @require_admin
    def nhl_edit(game_id):
        game = NhlGame.query.get_or_404(game_id)

        if request.method == "POST":
            game.game_date = datetime.strptime(request.form["game_date"], "%Y-%m-%d").date()
            game.season = request.form["season"]
            game.opponent = request.form["opponent"]
            game.home_away = request.form["home_away"]

            penguins_goals = int(request.form["penguins_goals"])
            opponent_goals = int(request.form["opponent_goals"])
            game.penguins_goals = penguins_goals
            game.opponent_goals = opponent_goals

            if penguins_goals > opponent_goals:
                game.result = "W"
            elif penguins_goals < opponent_goals:
                game.result = "L"
            else:
                game.result = "T"

            game.notes = request.form.get("notes") or None

            db.session.commit()
            flash("Penguins game updated.", "success")
            return redirect(url_for("nhl_list"))

        return render_template("nhl_edit.html", game=game)

    @app.route("/nhl/<int:game_id>/delete", methods=["POST"])
    @require_admin
    def nhl_delete(game_id):
        game = NhlGame.query.get_or_404(game_id)
        db.session.delete(game)
        db.session.commit()
        flash("Penguins game deleted.", "info")
        return redirect(url_for("nhl_list"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
