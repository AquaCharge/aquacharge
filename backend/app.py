
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "aquacharge-backend"})

@app.get("/api/sites")
def sites():
    return jsonify([
        {"id": "site_1", "name": "Harbour Export Hub", "city": "Moncton"},
        {"id": "site_2", "name": "City Center Lot", "city": "Saint John"}
    ])

if __name__ == "__main__":
    app.run(debug=True, port=5050)
