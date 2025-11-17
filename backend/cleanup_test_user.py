#!/usr/bin/env python3
"""
Script to manually delete test users from DynamoDB
"""
from db.dynamoClient import DynamoClient
from boto3.dynamodb.conditions import Key

# Initialize DynamoDB client
dynamo_client = DynamoClient(
    table_name="aquacharge-users-dev",
    region_name="us-east-1"
)

# Test emails to delete
test_emails = [
    "testuser@example.com",
    "newemail@example.com",
    "testverify@example.com",
]

print("Deleting test users from DynamoDB...")
for email in test_emails:
    try:
        # Query by email using GSI
        users = dynamo_client.query_gsi(
            index_name="email-index",
            key_condition_expression=Key("email").eq(email),
        )
        
        if users:
            for user in users:
                dynamo_client.delete_item(key={"id": user["id"]})
                print(f"✓ Deleted user: {email} (id: {user['id']})")
        else:
            print(f"- No user found with email: {email}")
    except Exception as e:
        print(f"✗ Failed to delete {email}: {e}")

print("\nCleanup complete!")
