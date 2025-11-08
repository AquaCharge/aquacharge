from flask import Blueprint, jsonify, request
from models.station import Station, StationStatus
from db.dynamoClient import DynamoClient
import decimal

stations_bp = Blueprint("stations", __name__)

# In-memory storage (replace with actual database)

dynamoDB_client = DynamoClient(
    table_name="aquacharge-stations-dev", region_name="us-east-1"
)


@stations_bp.route("", methods=["GET"])
def get_stations():
    """Get all stations, optionally filtered by city or status"""
    city = request.args.get("city")
    status = request.args.get("status")

    stations = list(dynamoDB_client.scan_items())

    if city:
        stations = [s for s in stations if s.city.lower() == city.lower()]

    if status:
        try:
            status_enum = StationStatus[status.upper()]
            stations = [s for s in stations if s.status == status_enum]
        except KeyError:
            return jsonify({"error": "Invalid status"}), 400

    return jsonify(stations), 200


@stations_bp.route("/<station_id>", methods=["GET"])
def get_station(station_id: str):
    """Get a specific station by ID"""

    station = dynamoDB_client.get_item(key={"id": station_id})

    if not station:
        return jsonify({"error": "Station not found"}), 404

    return jsonify(station), 200


@stations_bp.route("", methods=["POST"])
def create_station():
    """Create a new charging station"""
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
        longitude=decimal.Decimal(str(data["longitude"])),
        latitude=decimal.Decimal(str(data["latitude"])),
        city=data["city"],
        provinceOrState=data["provinceOrState"],
        country=data["country"],
        status=(
            StationStatus[data.get("status", "ACTIVE").upper()]
            if "status" in data
            else StationStatus.ACTIVE
        ),
    )

    # Store station
    dynamoDB_client.put_item(item=station.to_dict())

    return jsonify(station.to_dict()), 201


@stations_bp.route("/<station_id>", methods=["PUT"])
def update_station(station_id: str):
    """Update an existing station"""
    station = dynamoDB_client.get_item(key={"id": station_id})

    if not station:
        return jsonify({"error": "Station not found"}), 404

    data = request.get_json()
    current_station = Station.from_dict(station)

    # Build update dictionary with only provided fields
    update_data = {}

    if "displayName" in data:
        update_data["displayName"] = data["displayName"]
        current_station.displayName = data["displayName"]
    if "longitude" in data:
        update_data["longitude"] = decimal.Decimal(str(data["longitude"]))
        current_station.longitude = decimal.Decimal(str(data["longitude"]))
    if "latitude" in data:
        update_data["latitude"] = decimal.Decimal(str(data["latitude"]))
        current_station.latitude = decimal.Decimal(str(data["latitude"]))
    if "city" in data:
        update_data["city"] = data["city"]
        current_station.city = data["city"]
    if "provinceOrState" in data:
        update_data["provinceOrState"] = data["provinceOrState"]
        current_station.provinceOrState = data["provinceOrState"]
    if "country" in data:
        update_data["country"] = data["country"]
        current_station.country = data["country"]
    if "status" in data:
        status_value = StationStatus[data["status"].upper()].value
        update_data["status"] = status_value
        current_station.status = StationStatus[data["status"].upper()]

    # Update the item in DynamoDB
    updated_station_dict = dynamoDB_client.update_item(
        key={"id": station_id}, update_data=update_data
    )

    return jsonify(updated_station_dict), 200


@stations_bp.route("/<station_id>", methods=["DELETE"])
def delete_station(station_id: str):
    """Delete a station"""
    station = dynamoDB_client.get_item(key={"id": station_id})

    if not station:
        return jsonify({"error": "Station not found"}), 404

    dynamoDB_client.delete_item(key={"id": station_id})
    return jsonify({"message": "Station deleted successfully"}), 200


@stations_bp.route("/nearby", methods=["GET"])
def get_nearby_stations():
    """Get stations near a specific location"""
    lat = request.args.get("lat", type=decimal.Decimal)
    lng = request.args.get("lng", type=decimal.Decimal)
    radius = request.args.get("radius", default=10, type=decimal.Decimal)  # km

    if lat is None or lng is None:
        return jsonify({"error": "lat and lng parameters are required"}), 400

    # Simple distance calculation (you'd want to use proper geospatial queries in production)
    nearby = []
    stations = dynamoDB_client.scan_items()
    for station in stations:
        # Simplified distance calculation
        print(station)
        distance = (
            float((station["latitude"] - lat)) ** 2
            + float((station["longitude"] - lng)) ** 2
        ) ** 0.5
        distance = decimal.Decimal(distance)
        if distance <= radius:
            station_dict = station
            station_dict["distance"] = distance
            nearby.append(station_dict)

    # Sort by distance
    nearby.sort(key=lambda x: x["distance"])

    return jsonify(nearby), 200
