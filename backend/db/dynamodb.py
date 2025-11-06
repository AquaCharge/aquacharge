"""
DynamoDB client helper module for AquaCharge backend.
Reads table names from environment variables and provides CRUD operations.
"""

import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, Any, List, Optional
from decimal import Decimal
import json
from datetime import datetime


class DynamoDBClient:
    """Helper class for DynamoDB operations"""
    
    def __init__(self):
        """Initialize DynamoDB client and get table names from environment"""
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        
        # Get table names from environment variables
        self.users_table_name = os.environ.get('DYNAMODB_USERS_TABLE', 'aquacharge-users-dev')
        self.stations_table_name = os.environ.get('DYNAMODB_STATIONS_TABLE', 'aquacharge-stations-dev')
        self.chargers_table_name = os.environ.get('DYNAMODB_CHARGERS_TABLE', 'aquacharge-chargers-dev')
        self.vessels_table_name = os.environ.get('DYNAMODB_VESSELS_TABLE', 'aquacharge-vessels-dev')
        self.bookings_table_name = os.environ.get('DYNAMODB_BOOKINGS_TABLE', 'aquacharge-bookings-dev')
        self.contracts_table_name = os.environ.get('DYNAMODB_CONTRACTS_TABLE', 'aquacharge-contracts-dev')
        
        # Initialize table resources
        self.users_table = self.dynamodb.Table(self.users_table_name)
        self.stations_table = self.dynamodb.Table(self.stations_table_name)
        self.chargers_table = self.dynamodb.Table(self.chargers_table_name)
        self.vessels_table = self.dynamodb.Table(self.vessels_table_name)
        self.bookings_table = self.dynamodb.Table(self.bookings_table_name)
        self.contracts_table = self.dynamodb.Table(self.contracts_table_name)
    
    @staticmethod
    def decimal_to_float(obj):
        """Convert DynamoDB Decimal objects to float for JSON serialization"""
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, dict):
            return {k: DynamoDBClient.decimal_to_float(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [DynamoDBClient.decimal_to_float(item) for item in obj]
        return obj
    
    @staticmethod
    def prepare_item_for_dynamodb(item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare item for DynamoDB by converting types appropriately"""
        prepared = {}
        for key, value in item.items():
            if value is None:
                # Skip None values (DynamoDB doesn't allow null)
                continue
            elif isinstance(value, datetime):
                # Convert datetime to ISO string
                prepared[key] = value.isoformat()
            elif isinstance(value, float):
                # Convert float to Decimal for DynamoDB
                prepared[key] = Decimal(str(value))
            elif isinstance(value, dict):
                # Recursively handle nested dictionaries
                prepared[key] = DynamoDBClient.prepare_item_for_dynamodb(value)
            elif isinstance(value, list):
                # Recursively handle lists
                prepared[key] = [
                    DynamoDBClient.prepare_item_for_dynamodb(item) if isinstance(item, dict)
                    else Decimal(str(item)) if isinstance(item, float)
                    else item
                    for item in value
                ]
            else:
                prepared[key] = value
        return prepared
    
    # ===== Generic CRUD Operations =====
    
    def put_item(self, table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update an item in a table"""
        table = self.dynamodb.Table(table_name)
        prepared_item = self.prepare_item_for_dynamodb(item)
        response = table.put_item(Item=prepared_item)
        return response
    
    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get an item by primary key"""
        table = self.dynamodb.Table(table_name)
        response = table.get_item(Key=key)
        item = response.get('Item')
        return self.decimal_to_float(item) if item else None
    
    def delete_item(self, table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an item by primary key"""
        table = self.dynamodb.Table(table_name)
        response = table.delete_item(Key=key)
        return response
    
    def scan_table(self, table_name: str, filter_expression=None, limit: int = 100) -> List[Dict[str, Any]]:
        """Scan entire table (use sparingly, expensive operation)"""
        table = self.dynamodb.Table(table_name)
        params = {'Limit': limit}
        if filter_expression:
            params['FilterExpression'] = filter_expression
        
        response = table.scan(**params)
        items = response.get('Items', [])
        return [self.decimal_to_float(item) for item in items]
    
    def query_index(self, table_name: str, index_name: str, key_condition, 
                   filter_expression=None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query a Global Secondary Index"""
        table = self.dynamodb.Table(table_name)
        params = {
            'IndexName': index_name,
            'KeyConditionExpression': key_condition,
            'Limit': limit
        }
        if filter_expression:
            params['FilterExpression'] = filter_expression
        
        response = table.query(**params)
        items = response.get('Items', [])
        return [self.decimal_to_float(item) for item in items]
    
    # ===== User Operations =====
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return self.get_item(self.users_table_name, {'id': user_id})
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email using email-index GSI"""
        results = self.query_index(
            self.users_table_name,
            'email-index',
            Key('email').eq(email)
        )
        return results[0] if results else None
    
    def get_users_by_org(self, org_id: str) -> List[Dict[str, Any]]:
        """Get all users in an organization using orgId-index GSI"""
        return self.query_index(
            self.users_table_name,
            'orgId-index',
            Key('orgId').eq(org_id)
        )
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        return self.put_item(self.users_table_name, user_data)
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user fields"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        user.update(updates)
        return self.put_item(self.users_table_name, user)
    
    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """Delete a user"""
        return self.delete_item(self.users_table_name, {'id': user_id})
    
    # ===== Station Operations =====
    
    def get_station_by_id(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Get station by ID"""
        return self.get_item(self.stations_table_name, {'id': station_id})
    
    def get_stations_by_city(self, city: str) -> List[Dict[str, Any]]:
        """Get stations in a city using city-index GSI"""
        return self.query_index(
            self.stations_table_name,
            'city-index',
            Key('city').eq(city)
        )
    
    def get_stations_by_status(self, status: int) -> List[Dict[str, Any]]:
        """Get stations by status using status-index GSI"""
        return self.query_index(
            self.stations_table_name,
            'status-index',
            Key('status').eq(status)
        )
    
    def get_all_stations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all stations"""
        return self.scan_table(self.stations_table_name, limit=limit)
    
    def create_station(self, station_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new station"""
        return self.put_item(self.stations_table_name, station_data)
    
    # ===== Charger Operations =====
    
    def get_charger_by_id(self, charger_id: str) -> Optional[Dict[str, Any]]:
        """Get charger by ID"""
        return self.get_item(self.chargers_table_name, {'id': charger_id})
    
    def get_chargers_by_station(self, station_id: str) -> List[Dict[str, Any]]:
        """Get all chargers at a station using chargingStationId-index GSI"""
        return self.query_index(
            self.chargers_table_name,
            'chargingStationId-index',
            Key('chargingStationId').eq(station_id)
        )
    
    def get_chargers_by_type(self, charger_type: str) -> List[Dict[str, Any]]:
        """Get chargers by type using chargerType-index GSI"""
        return self.query_index(
            self.chargers_table_name,
            'chargerType-index',
            Key('chargerType').eq(charger_type)
        )
    
    def create_charger(self, charger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new charger"""
        return self.put_item(self.chargers_table_name, charger_data)
    
    # ===== Vessel Operations =====
    
    def get_vessel_by_id(self, vessel_id: str) -> Optional[Dict[str, Any]]:
        """Get vessel by ID"""
        return self.get_item(self.vessels_table_name, {'id': vessel_id})
    
    def get_vessels_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all vessels owned by a user using userId-index GSI"""
        return self.query_index(
            self.vessels_table_name,
            'userId-index',
            Key('userId').eq(user_id)
        )
    
    def get_vessels_by_type(self, vessel_type: str) -> List[Dict[str, Any]]:
        """Get vessels by type using vesselType-index GSI"""
        return self.query_index(
            self.vessels_table_name,
            'vesselType-index',
            Key('vesselType').eq(vessel_type)
        )
    
    def create_vessel(self, vessel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vessel"""
        return self.put_item(self.vessels_table_name, vessel_data)
    
    # ===== Booking Operations =====
    
    def get_booking_by_id(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Get booking by ID"""
        return self.get_item(self.bookings_table_name, {'id': booking_id})
    
    def get_bookings_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all bookings for a user using userId-index GSI"""
        return self.query_index(
            self.bookings_table_name,
            'userId-index',
            Key('userId').eq(user_id)
        )
    
    def get_bookings_by_station(self, station_id: str) -> List[Dict[str, Any]]:
        """Get all bookings for a station using stationId-index GSI"""
        return self.query_index(
            self.bookings_table_name,
            'stationId-index',
            Key('stationId').eq(station_id)
        )
    
    def get_bookings_by_vessel(self, vessel_id: str) -> List[Dict[str, Any]]:
        """Get all bookings for a vessel using vesselId-index GSI"""
        return self.query_index(
            self.bookings_table_name,
            'vesselId-index',
            Key('vesselId').eq(vessel_id)
        )
    
    def get_bookings_by_status(self, status: int) -> List[Dict[str, Any]]:
        """Get bookings by status using status-index GSI"""
        return self.query_index(
            self.bookings_table_name,
            'status-index',
            Key('status').eq(status)
        )
    
    def create_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new booking"""
        return self.put_item(self.bookings_table_name, booking_data)
    
    # ===== Contract Operations =====
    
    def get_contract_by_id(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get a contract by ID"""
        return self.get_item(self.contracts_table_name, {'id': contract_id})
    
    def get_contracts_by_vessel(self, vessel_id: str) -> List[Dict[str, Any]]:
        """Get all contracts for a vessel using vesselId-index GSI"""
        return self.query_index(
            self.contracts_table_name,
            'vesselId-index',
            Key('vesselId').eq(vessel_id)
        )
    
    def create_contract(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contract"""
        return self.put_item(self.contracts_table_name, contract_data)


# Create a singleton instance
db_client = DynamoDBClient()
