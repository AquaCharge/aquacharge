from flask import Flask
from api.users import users_bp
from api.vessels import vessels_bp
from api.stations import stations_bp
from api.chargers import chargers_bp
from api.bookings import bookings_bp
from api.contracts import contracts_bp
from api.drevents import drevents_bp
from api.auth import auth_bp
from api.ports import ports_bp
from api.vo_dashboard import vo_dashboard_bp


def register_blueprints(app: Flask):
    """Register all API blueprints with the Flask app"""
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(vessels_bp, url_prefix="/api/vessels")
    app.register_blueprint(stations_bp, url_prefix="/api/stations")
    app.register_blueprint(chargers_bp, url_prefix="/api/chargers")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(drevents_bp, url_prefix="/api/drevents")
    app.register_blueprint(contracts_bp, url_prefix="/api/contracts")
    app.register_blueprint(ports_bp, url_prefix="/api/ports")
    app.register_blueprint(vo_dashboard_bp, url_prefix="/api/vo")
