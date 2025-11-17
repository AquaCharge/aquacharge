#!/usr/bin/env python3
"""Debug script to check if testuser@example.com exists in DynamoDB"""

from db.dynamoClient import DynamoClient
from boto3.dynamodb.conditions import Attr, Key

def check_user_exists():
    dynamo_client = DynamoClient(
        table_name="aquacharge-users-dev",
        region_name="us-east-1"
    )
    
    test_email = "testuser@example.com"
    
    print(f"Checking for user with email: {test_email}")
    print("-" * 50)
    
    # Method 1: Scan with filter (what register endpoint uses)
    print("\n1. Using scan_items with filter:")
    scan_results = dynamo_client.scan_items(
        filter_expression=Attr('email').eq(test_email)
    )
    print(f"   Found {len(scan_results)} users")
    for user in scan_results:
        print(f"   - ID: {user.get('id')}, Email: {user.get('email')}, DisplayName: {user.get('displayName')}")
    
    # Method 2: Query GSI
    print("\n2. Using query_gsi on email-index:")
    try:
        gsi_results = dynamo_client.query_gsi(
            index_name="email-index",
            key_condition_expression=Key('email').eq(test_email)
        )
        print(f"   Found {len(gsi_results)} users")
        for user in gsi_results:
            print(f"   - ID: {user.get('id')}, Email: {user.get('email')}, DisplayName: {user.get('displayName')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 3: Scan entire table to see all users
    print("\n3. All users in table:")
    all_users = dynamo_client.scan_items()
    print(f"   Total users: {len(all_users)}")
    for user in all_users:
        print(f"   - ID: {user.get('id')}, Email: {user.get('email')}, DisplayName: {user.get('displayName')}")

if __name__ == "__main__":
    check_user_exists()
