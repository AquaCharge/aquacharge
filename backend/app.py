from flask import Flask, jsonify
from flask_cors import CORS
from api import register_blueprints

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register all API blueprints
register_blueprints(app)


@app.get("/api/health")
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
