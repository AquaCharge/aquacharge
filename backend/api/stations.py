from flask import Blueprint, jsonify, request
from backend.models.station import Station, StationStatus
from typing import Dict

stations_bp = Blueprint('stations', __name__)

# In-memory storage (replace with actual database)
stations_db: Dict[str, Station] = {}

# Initialize with sample data
def init_sample_stations():
    if not stations_db:  # Only initialize if empty
        sample_stations = [
            Station(
                id="station-001",
                displayName="Marina Bay Charging Hub",
                longitude=-123.1207,
                latitude=49.2827,
                city="Vancouver",
                provinceOrState="British Columbia",
                country="Canada",
                status=StationStatus.ACTIVE
            ),
            Station(
                id="station-002",
                displayName="Harbour View Electric Dock",
                longitude=-122.4194,
                latitude=37.7749,
                city="San Francisco",
                provinceOrState="California",
                country="USA",
                status=StationStatus.ACTIVE
            ),
            Station(
                id="station-003",
                displayName="Blue Water Marina Station",
                longitude=-80.1918,
                latitude=25.7617,
                city="Miami",
                provinceOrState="Florida",
                country="USA",
                status=StationStatus.MAINTENANCE
            ),
            Station(
                id="station-004",
                displayName="Nordic Fjord Charging Point",
                longitude=10.7522,
                latitude=59.9139,
                city="Oslo",
                provinceOrState="Oslo",
                country="Norway",
                status=StationStatus.ACTIVE
            ),
            Station(
                id="station-005",
                displayName="Sydney Harbour Electric",
                longitude=151.2093,
                latitude=-33.8688,
                city="Sydney",
                provinceOrState="New South Wales",
                country="Australia",
                status=StationStatus.INACTIVE
            ),
            Station(
                id="station-006",
                displayName="Mediterranean Charging Hub",
                longitude=2.1734,
                latitude=41.3851,
                city="Barcelona",
                provinceOrState="Catalonia",
                country="Spain",
                status=StationStatus.ACTIVE
            )
        ]
        
        for station in sample_stations:
            stations_db[station.id] = station

# Initialize sample data when module is imported
init_sample_stations()

@stations_bp.route('', methods=['GET'])
def get_stations():
    """Get all stations, optionally filtered by city or status"""
    city = request.args.get('city')
    status = request.args.get('status')
    
    stations = list(stations_db.values())
    
    if city:
        stations = [s for s in stations if s.city.lower() == city.lower()]
    
    if status:
        try:
            status_enum = StationStatus[status.upper()]
            stations = [s for s in stations if s.status == status_enum]
        except KeyError:
            return jsonify({'error': 'Invalid status'}), 400
    
    return jsonify([s.to_dict() for s in stations]), 200

@stations_bp.route('/<station_id>', methods=['GET'])
def get_station(station_id: str):
    """Get a specific station by ID"""
    if station_id not in stations_db:
        return jsonify({'error': 'Station not found'}), 404
    
    return jsonify(stations_db[station_id].to_dict()), 200

@stations_bp.route('', methods=['POST'])
def create_station():
    """Create a new charging station"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['displayName', 'longitude', 'latitude', 'city', 'provinceOrState', 'country']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Create station instance
    station = Station(
        displayName=data['displayName'],
        longitude=float(data['longitude']),
        latitude=float(data['latitude']),
        city=data['city'],
        provinceOrState=data['provinceOrState'],
        country=data['country'],
        status=StationStatus[data.get('status', 'ACTIVE').upper()] if 'status' in data else StationStatus.ACTIVE
    )
    
    # Store station
    stations_db[station.id] = station
    
    return jsonify(station.to_dict()), 201

@stations_bp.route('/<station_id>', methods=['PUT'])
def update_station(station_id: str):
    """Update an existing station"""
    if station_id not in stations_db:
        return jsonify({'error': 'Station not found'}), 404
    
    data = request.get_json()
    station = stations_db[station_id]
    
    # Update allowed fields
    update_fields = ['displayName', 'longitude', 'latitude', 'city', 
                     'provinceOrState', 'country', 'status']
    
    for field in update_fields:
        if field in data:
            if field in ['longitude', 'latitude']:
                setattr(station, field, float(data[field]))
            elif field == 'status':
                setattr(station, field, StationStatus[data[field].upper()])
            else:
                setattr(station, field, data[field])
    
    return jsonify(station.to_dict()), 200

@stations_bp.route('/<station_id>', methods=['DELETE'])
def delete_station(station_id: str):
    """Delete a station"""
    if station_id not in stations_db:
        return jsonify({'error': 'Station not found'}), 404
    
    del stations_db[station_id]
    return jsonify({'message': 'Station deleted successfully'}), 200

@stations_bp.route('/nearby', methods=['GET'])
def get_nearby_stations():
    """Get stations near a specific location"""
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', default=10, type=float)  # km
    
    if lat is None or lng is None:
        return jsonify({'error': 'lat and lng parameters are required'}), 400
    
    # Simple distance calculation (you'd want to use proper geospatial queries in production)
    nearby = []
    for station in stations_db.values():
        # Simplified distance calculation
        distance = ((station.latitude - lat) ** 2 + (station.longitude - lng) ** 2) ** 0.5
        if distance <= radius:
            station_dict = station.to_dict()
            station_dict['distance'] = distance
            nearby.append(station_dict)
    
    # Sort by distance
    nearby.sort(key=lambda x: x['distance'])
    
    return jsonify(nearby), 200