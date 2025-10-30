#!/usr/bin/env python3
"""
Script to initialize DynamoDB tables with sample data for AquaCharge.
This script populates the tables with test data matching the backend models.
"""

import boto3
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import argparse


def get_table_names(environment='dev'):
    """Get DynamoDB table names for the given environment."""
    return {
        'users': f'aquacharge-users-{environment}',
        'stations': f'aquacharge-stations-{environment}',
        'chargers': f'aquacharge-chargers-{environment}',
        'vessels': f'aquacharge-vessels-{environment}',
        'bookings': f'aquacharge-bookings-{environment}',
    }


def init_users_table(dynamodb, table_name):
    """Initialize Users table with sample data."""
    table = dynamodb.Table(table_name)
    
    users = [
        {
            'id': str(uuid.uuid4()),
            'username': 'admin',
            'email': 'admin@aquacharge.com',
            'passwordHash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIeWEJbgxa',  # password: admin123
            'role': 1,  # ADMIN
            'active': True,
            'createdAt': datetime.now().isoformat(),
        },
        {
            'id': str(uuid.uuid4()),
            'username': 'operator1',
            'email': 'operator@aquacharge.com',
            'passwordHash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIeWEJbgxa',  # password: admin123
            'role': 3,  # OPERATOR
            'active': True,
            'createdAt': datetime.now().isoformat(),
        },
        {
            'id': str(uuid.uuid4()),
            'username': 'testuser',
            'email': 'user@example.com',
            'passwordHash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIeWEJbgxa',  # password: admin123
            'role': 2,  # USER
            'active': True,
            'createdAt': datetime.now().isoformat(),
        },
    ]
    
    for user in users:
        try:
            table.put_item(Item=user)
            print(f"✓ Created user: {user['email']}")
        except Exception as e:
            print(f"✗ Error creating user {user['email']}: {str(e)}")
    
    return users


def init_stations_table(dynamodb, table_name):
    """Initialize Stations table with sample data."""
    table = dynamodb.Table(table_name)
    
    stations = [
        {
            'id': str(uuid.uuid4()),
            'displayName': 'Halifax Harbour Marina',
            'longitude': Decimal('-63.5754'),
            'latitude': Decimal('44.6488'),
            'city': 'Halifax',
            'provinceOrState': 'Nova Scotia',
            'country': 'Canada',
            'status': 1,  # ACTIVE
        },
        {
            'id': str(uuid.uuid4()),
            'displayName': 'Vancouver Marina',
            'longitude': Decimal('-123.1207'),
            'latitude': Decimal('49.2827'),
            'city': 'Vancouver',
            'provinceOrState': 'British Columbia',
            'country': 'Canada',
            'status': 1,  # ACTIVE
        },
        {
            'id': str(uuid.uuid4()),
            'displayName': 'Toronto Waterfront',
            'longitude': Decimal('-79.3832'),
            'latitude': Decimal('43.6532'),
            'city': 'Toronto',
            'provinceOrState': 'Ontario',
            'country': 'Canada',
            'status': 1,  # ACTIVE
        },
        {
            'id': str(uuid.uuid4()),
            'displayName': 'Seattle Marina',
            'longitude': Decimal('-122.3321'),
            'latitude': Decimal('47.6062'),
            'city': 'Seattle',
            'provinceOrState': 'Washington',
            'country': 'United States',
            'status': 2,  # MAINTENANCE
        },
    ]
    
    for station in stations:
        try:
            table.put_item(Item=station)
            print(f"✓ Created station: {station['displayName']}")
        except Exception as e:
            print(f"✗ Error creating station {station['displayName']}: {str(e)}")
    
    return stations


def init_chargers_table(dynamodb, table_name, stations):
    """Initialize Chargers table with sample data."""
    table = dynamodb.Table(table_name)
    
    charger_types = ['Type A', 'Type B', 'Type C', 'Fast Charge']
    chargers = []
    
    for station in stations[:3]:  # Only active stations
        for i, charger_type in enumerate(charger_types):
            charger = {
                'id': str(uuid.uuid4()),
                'chargingStationId': station['id'],
                'chargerType': charger_type,
                'maxRate': Decimal(str(50 + (i * 25))),  # 50, 75, 100, 125 kW
                'active': True,
            }
            chargers.append(charger)
            
            try:
                table.put_item(Item=charger)
                print(f"✓ Created charger: {charger_type} at {station['displayName']}")
            except Exception as e:
                print(f"✗ Error creating charger: {str(e)}")
    
    return chargers


def init_vessels_table(dynamodb, table_name, users):
    """Initialize Vessels table with sample data."""
    table = dynamodb.Table(table_name)
    
    # Get a user ID for the vessels
    user_id = users[2]['id']  # testuser
    
    vessels = [
        {
            'id': str(uuid.uuid4()),
            'userId': user_id,
            'displayName': 'Sea Breeze',
            'vesselType': 'Sailboat',
            'chargerType': 'Type A',
            'capacity': Decimal('100.0'),
            'maxChargeRate': Decimal('50.0'),
            'minChargeRate': Decimal('10.0'),
            'rangeMeters': Decimal('50000.0'),
            'active': True,
            'createdAt': datetime.now().isoformat(),
        },
        {
            'id': str(uuid.uuid4()),
            'userId': user_id,
            'displayName': 'Ocean Explorer',
            'vesselType': 'Motor Yacht',
            'chargerType': 'Type C',
            'capacity': Decimal('250.0'),
            'maxChargeRate': Decimal('100.0'),
            'minChargeRate': Decimal('25.0'),
            'rangeMeters': Decimal('100000.0'),
            'active': True,
            'createdAt': datetime.now().isoformat(),
        },
    ]
    
    for vessel in vessels:
        try:
            table.put_item(Item=vessel)
            print(f"✓ Created vessel: {vessel['displayName']}")
        except Exception as e:
            print(f"✗ Error creating vessel {vessel['displayName']}: {str(e)}")
    
    return vessels


def init_bookings_table(dynamodb, table_name, users, vessels, stations):
    """Initialize Bookings table with sample data."""
    table = dynamodb.Table(table_name)
    
    user_id = users[2]['id']
    vessel_id = vessels[0]['id']
    station_id = stations[0]['id']
    
    # Create bookings for different time periods
    now = datetime.now()
    
    bookings = [
        {
            'id': str(uuid.uuid4()),
            'userId': user_id,
            'vesselId': vessel_id,
            'stationId': station_id,
            'startTime': (now + timedelta(hours=2)).isoformat(),
            'endTime': (now + timedelta(hours=4)).isoformat(),
            'status': 2,  # CONFIRMED
            'chargerType': 'Type A',
            'createdAt': now.isoformat(),
        },
        {
            'id': str(uuid.uuid4()),
            'userId': user_id,
            'vesselId': vessels[1]['id'],
            'stationId': stations[1]['id'],
            'startTime': (now + timedelta(days=1)).isoformat(),
            'endTime': (now + timedelta(days=1, hours=3)).isoformat(),
            'status': 1,  # PENDING
            'chargerType': 'Type C',
            'createdAt': now.isoformat(),
        },
        {
            'id': str(uuid.uuid4()),
            'userId': user_id,
            'vesselId': vessel_id,
            'stationId': station_id,
            'startTime': (now - timedelta(days=2)).isoformat(),
            'endTime': (now - timedelta(days=2, hours=-3)).isoformat(),
            'status': 3,  # COMPLETED
            'chargerType': 'Type A',
            'createdAt': (now - timedelta(days=3)).isoformat(),
        },
    ]
    
    for booking in bookings:
        try:
            table.put_item(Item=booking)
            print(f"✓ Created booking for station: {booking['stationId']}")
        except Exception as e:
            print(f"✗ Error creating booking: {str(e)}")
    
    return bookings


def main():
    parser = argparse.ArgumentParser(description='Initialize DynamoDB tables with sample data')
    parser.add_argument(
        '--environment',
        '-e',
        default='dev',
        help='Environment name (default: dev)'
    )
    parser.add_argument(
        '--region',
        '-r',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--profile',
        '-p',
        help='AWS profile to use'
    )
    
    args = parser.parse_args()
    
    # Initialize boto3 session
    session_kwargs = {'region_name': args.region}
    if args.profile:
        session_kwargs['profile_name'] = args.profile
    
    session = boto3.Session(**session_kwargs)
    dynamodb = session.resource('dynamodb')
    
    table_names = get_table_names(args.environment)
    
    print(f"\n🚀 Initializing DynamoDB tables for environment: {args.environment}")
    print("=" * 60)
    
    try:
        # Initialize tables in order (respecting dependencies)
        print("\n📝 Creating users...")
        users = init_users_table(dynamodb, table_names['users'])
        
        print("\n🏢 Creating stations...")
        stations = init_stations_table(dynamodb, table_names['stations'])
        
        print("\n⚡ Creating chargers...")
        chargers = init_chargers_table(dynamodb, table_names['chargers'], stations)
        
        print("\n⛵ Creating vessels...")
        vessels = init_vessels_table(dynamodb, table_names['vessels'], users)
        
        print("\n📅 Creating bookings...")
        bookings = init_bookings_table(dynamodb, table_names['bookings'], users, vessels, stations)
        
        print("\n" + "=" * 60)
        print("✅ Successfully initialized all tables!")
        print(f"\nSummary:")
        print(f"  Users: {len(users)}")
        print(f"  Stations: {len(stations)}")
        print(f"  Chargers: {len(chargers)}")
        print(f"  Vessels: {len(vessels)}")
        print(f"  Bookings: {len(bookings)}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
