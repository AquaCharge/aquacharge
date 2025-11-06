from flask import Blueprint, jsonify, request
from models.station import Station, StationStatus
from db.dynamodb import db_client

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("", methods=["GET"])
def get_stations():
    """Get all stations, optionally filtered by city or status"""
    try:
        city = request.args.get("city")
        status = request.args.get("status")

        # Get all stations from DynamoDB
        stations_data = db_client.scan_table(db_client.stations_table_name, limit=1000)
        stations = [Station.from_dict(s) for s in stations_data]

        # Apply filters
        if city:
            stations = [s for s in stations if s.city.lower() == city.lower()]

        if status:
            try:
                status_enum = StationStatus[status.upper()]
                stations = [s for s in stations if s.status == status_enum]
            except KeyError:
                return jsonify({"error": "Invalid status"}), 400

        return jsonify([s.to_dict() for s in stations]), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch stations", "details": str(e)}), 500


@stations_bp.route("/<station_id>", methods=["GET"])
def get_station(station_id: str):
    """Get a specific station by ID"""
    try:
        station_data = db_client.get_station_by_id(station_id)

        if not station_data:
            return jsonify({"error": "Station not found"}), 404

        station = Station.from_dict(station_data)
        return jsonify(station.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch station", "details": str(e)}), 500


@stations_bp.route("", methods=["POST"])
def create_station():
    """Create a new charging station"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            "displayName",
            "longitude",
            "latitude",
            "city",
            "provinceOrState",
            "country",
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        # Create station instance
        station = Station(
            displayName=data["displayName"],
            longitude=float(data["longitude"]),
            latitude=float(data["latitude"]),
            city=data["city"],
            provinceOrState=data["provinceOrState"],
            country=data["country"],
            status=(
                StationStatus[data.get("status", "ACTIVE").upper()]
                if "status" in data
                else StationStatus.ACTIVE
            ),
        )

        # Store station in DynamoDB
        db_client.create_station(station.to_dict())

        return jsonify(station.to_dict()), 201
    except Exception as e:
        return jsonify({"error": "Failed to create station", "details": str(e)}), 500


@stations_bp.route("/<station_id>", methods=["PUT"])
def update_station(station_id: str):
    """Update an existing station"""
    try:
        station_data = db_client.get_station_by_id(station_id)

        if not station_data:
            return jsonify({"error": "Station not found"}), 404

        data = request.get_json()
        station = Station.from_dict(station_data)

        # Update allowed fields
        update_fields = [
            "displayName",
            "longitude",
            "latitude",
            "city",
            "provinceOrState",
            "country",
            "status",
        ]

        for field in update_fields:
            if field in data:
                if field in ["longitude", "latitude"]:
                    setattr(station, field, float(data[field]))
                elif field == "status":
                    setattr(station, field, StationStatus[data[field].upper()])
                else:
                    setattr(station, field, data[field])

        # Update in DynamoDB
        db_client.put_item(db_client.stations_table_name, station.to_dict())

        return jsonify(station.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to update station", "details": str(e)}), 500


@stations_bp.route("/<station_id>", methods=["DELETE"])
def delete_station(station_id: str):
    """Delete a station"""
    try:
        station_data = db_client.get_station_by_id(station_id)

        if not station_data:
            return jsonify({"error": "Station not found"}), 404

        db_client.delete_item(db_client.stations_table_name, {"id": station_id})
        return jsonify({"message": "Station deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete station", "details": str(e)}), 500


@stations_bp.route("/nearby", methods=["GET"])
def get_nearby_stations():
    """Get stations near a specific location"""
    try:
        lat = request.args.get("lat", type=float)
        lng = request.args.get("lng", type=float)
        radius = request.args.get("radius", default=10, type=float)  # km

        if lat is None or lng is None:
            return jsonify({"error": "lat and lng parameters are required"}), 400

        # Get all stations from DynamoDB
        stations_data = db_client.scan_table(db_client.stations_table_name, limit=1000)

        # Calculate distances
        nearby = []
        for station_data in stations_data:
            # Simplified distance calculation
            distance = (
                (station_data["latitude"] - lat) ** 2
                + (station_data["longitude"] - lng) ** 2
            ) ** 0.5
            if distance <= radius:
                station_dict = station_data.copy()
                station_dict["distance"] = distance
                nearby.append(station_dict)

        # Sort by distance
        nearby.sort(key=lambda x: x["distance"])

        return jsonify(nearby), 200
    except Exception as e:
        return (
            jsonify({"error": "Failed to fetch nearby stations", "details": str(e)}),
            500,
        )
