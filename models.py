from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()


class NascarRace(db.Model):
    __tablename__ = "nascar_races"

    id = db.Column(db.Integer, primary_key=True)
    race_date = db.Column(db.Date, nullable=False)
    track = db.Column(db.String(120), nullable=False)
    series = db.Column(db.String(80), nullable=True)  # Cup, Xfinity, etc.
    race_name = db.Column(db.String(150), nullable=True)
    winner = db.Column(db.String(120), nullable=False)
    start_position = db.Column(db.Integer, nullable=True)
    finish_position = db.Column(db.Integer, nullable=True)
    laps_led = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)


class NflGame(db.Model):
    __tablename__ = "nfl_games"

    id = db.Column(db.Integer, primary_key=True)
    game_date = db.Column(db.Date, nullable=False)
    season = db.Column(db.Integer, nullable=False)
    week = db.Column(db.Integer, nullable=True)  # 1–18, playoffs can be null or >18
    opponent = db.Column(db.String(120), nullable=False)
    home_away = db.Column(db.String(1), nullable=False)  # 'H' or 'A'
    steelers_score = db.Column(db.Integer, nullable=False)
    opponent_score = db.Column(db.Integer, nullable=False)
    result = db.Column(db.String(1), nullable=False)  # 'W', 'L', 'T'
    notes = db.Column(db.Text, nullable=True)


class PgaResult(db.Model):
    __tablename__ = "pga_results"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    tournament_name = db.Column(db.String(150), nullable=False)
    course = db.Column(db.String(150), nullable=True)
    finish_position = db.Column(db.Integer, nullable=True)
    score_to_par = db.Column(db.Integer, nullable=True)  # e.g., -10, +2
    notes = db.Column(db.Text, nullable=True)


class NhlGame(db.Model):
    __tablename__ = "nhl_games"

    id = db.Column(db.Integer, primary_key=True)
    game_date = db.Column(db.Date, nullable=False)
    season = db.Column(db.String(9), nullable=False)  # '2025-26', etc.
    opponent = db.Column(db.String(120), nullable=False)
    home_away = db.Column(db.String(1), nullable=False)  # 'H' or 'A'
    penguins_goals = db.Column(db.Integer, nullable=False)
    opponent_goals = db.Column(db.Integer, nullable=False)
    result = db.Column(db.String(1), nullable=False)  # 'W', 'L', 'OTL'
    notes = db.Column(db.Text, nullable=True)
