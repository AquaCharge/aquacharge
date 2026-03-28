from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from api import register_blueprints
from monitoring import record_request_end, record_request_start, setup_logging

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Keep demo polling usable in production by matching the development defaults.
default_limits = ["100000 per day", "5000 per hour"]

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=default_limits,
    storage_uri="memory://",
    strategy="fixed-window",
)

# Register all API blueprints
register_blueprints(app)

# Set up structured logging (+ optional CloudWatch Logs)
setup_logging()


# ---------------------------------------------------------------------------
# Request lifecycle hooks for CloudWatch metrics
# ---------------------------------------------------------------------------


@app.before_request
def _before():
    record_request_start(g)


@app.after_request
def _after(response):
    if getattr(g, "request_start", None) is not None:
        record_request_end(g, response, request.endpoint or request.path, request.method)
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
@limiter.exempt
def health():
    return jsonify({"status": "ok", "service": "aquacharge-backend"})


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5050)
