from flask import Flask
from api.users import users_bp
from api.vessels import vessels_bp
from api.stations import stations_bp
from api.chargers import chargers_bp
from api.bookings import bookings_bp


def register_blueprints(app: Flask):
    """Register all API blueprints with the Flask app"""
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(vessels_bp, url_prefix="/api/vessels")
    app.register_blueprint(stations_bp, url_prefix="/api/stations")
    app.register_blueprint(chargers_bp, url_prefix="/api/chargers")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
