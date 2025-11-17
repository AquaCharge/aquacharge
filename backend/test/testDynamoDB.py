import pytest
from db.dynamoClient import DynamoClient
from boto3.dynamodb.conditions import Key, Attr
import uuid
from datetime import datetime


# Track created test items for cleanup
test_item_ids = []


@pytest.fixture
def dynamo_client():
    """Fixture to provide DynamoDB client for testing"""
    client = DynamoClient(
        table_name="aquacharge-users-dev",
        region_name="us-east-1"
    )
    yield client


@pytest.fixture(autouse=True)
def cleanup_test_items(dynamo_client):
    """Automatically clean up test items after each test"""
    yield  # Run the test first
    
    # Cleanup: Delete all test items created during the test
    if test_item_ids:
        for item_id in test_item_ids:
            try:
                dynamo_client.delete_item(key={"id": item_id})
                print(f"Cleaned up test item: {item_id}")
            except Exception as e:
                print(f"Cleanup failed for {item_id}: {e}")
        test_item_ids.clear()


# --- Connection Tests --- #
def test_dynamodb_connection(dynamo_client):
    """Test that we can connect to DynamoDB"""
    try:
        # Try to perform a simple operation
        result = dynamo_client.scan_items()
        assert isinstance(result, list), "Should return a list"
        print(f"✓ Successfully connected to DynamoDB. Table has {len(result)} items.")
    except Exception as e:
        pytest.fail(f"Failed to connect to DynamoDB: {e}")


def test_dynamodb_table_exists(dynamo_client):
    """Test that the table exists and is accessible"""
    try:
        table_name = dynamo_client.table.table_name
        assert table_name == "aquacharge-users-dev"
        print(f"✓ Table '{table_name}' is accessible")
    except Exception as e:
        pytest.fail(f"Table does not exist or is not accessible: {e}")


# --- CRUD Operation Tests --- #
def test_put_and_get_item(dynamo_client):
    """Test putting and getting an item"""
    test_id = f"test-{uuid.uuid4()}"
    test_item_ids.append(test_id)
    
    test_item = {
        "id": test_id,
        "displayName": "Test User",
        "email": f"test_{test_id}@example.com",
        "passwordHash": "hashed_password",
        "role": 2,
        "type": 1,
        "active": True,
        "createdAt": datetime.now().isoformat(),
    }
    
    # Put item
    response = dynamo_client.put_item(test_item)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Get item
    retrieved_item = dynamo_client.get_item(key={"id": test_id})
    assert retrieved_item["id"] == test_id
    assert retrieved_item["email"] == test_item["email"]
    assert retrieved_item["displayName"] == test_item["displayName"]


def test_update_item(dynamo_client):
    """Test updating an item"""
    test_id = f"test-{uuid.uuid4()}"
    test_item_ids.append(test_id)
    
    # Create initial item
    test_item = {
        "id": test_id,
        "displayName": "Original Name",
        "email": f"test_{test_id}@example.com",
        "passwordHash": "hashed_password",
        "role": 2,
        "type": 1,
        "active": True,
        "createdAt": datetime.now().isoformat(),
    }
    dynamo_client.put_item(test_item)
    
    # Update item
    update_data = {
        "displayName": "Updated Name",
        "active": False,
        "updatedAt": datetime.now().isoformat()
    }
    updated_item = dynamo_client.update_item(
        key={"id": test_id},
        update_data=update_data
    )
    
    assert updated_item["displayName"] == "Updated Name"
    assert updated_item["active"] == False
    assert "updatedAt" in updated_item


def test_delete_item(dynamo_client):
    """Test deleting an item"""
    test_id = f"test-{uuid.uuid4()}"
    
    # Create item
    test_item = {
        "id": test_id,
        "displayName": "To Be Deleted",
        "email": f"test_{test_id}@example.com",
        "passwordHash": "hashed_password",
        "role": 2,
        "type": 1,
        "active": True,
        "createdAt": datetime.now().isoformat(),
    }
    dynamo_client.put_item(test_item)
    
    # Verify it exists
    retrieved = dynamo_client.get_item(key={"id": test_id})
    assert retrieved["id"] == test_id
    
    # Delete item
    response = dynamo_client.delete_item(key={"id": test_id})
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Verify it's deleted
    deleted_item = dynamo_client.get_item(key={"id": test_id})
    assert deleted_item == {}  # Should return empty dict


# --- Query Tests --- #
def test_query_gsi_email_index(dynamo_client):
    """Test querying using the email GSI"""
    test_id = f"test-{uuid.uuid4()}"
    test_item_ids.append(test_id)
    test_email = f"test_{test_id}@example.com"
    
    # Create item
    test_item = {
        "id": test_id,
        "displayName": "GSI Test User",
        "email": test_email,
        "passwordHash": "hashed_password",
        "role": 2,
        "type": 1,
        "active": True,
        "createdAt": datetime.now().isoformat(),
    }
    dynamo_client.put_item(test_item)
    
    # Query by email using GSI
    results = dynamo_client.query_gsi(
        index_name="email-index",
        key_condition_expression=Key("email").eq(test_email)
    )
    
    assert len(results) == 1
    assert results[0]["email"] == test_email
    assert results[0]["id"] == test_id


def test_scan_with_filter(dynamo_client):
    """Test scanning with a filter expression"""
    test_id = f"test-{uuid.uuid4()}"
    test_item_ids.append(test_id)
    
    # Create item with specific attribute
    test_item = {
        "id": test_id,
        "displayName": "Scan Test User",
        "email": f"test_{test_id}@example.com",
        "passwordHash": "hashed_password",
        "role": 2,
        "type": 1,
        "active": True,
        "createdAt": datetime.now().isoformat(),
    }
    dynamo_client.put_item(test_item)
    
    # Scan with filter
    results = dynamo_client.scan_items(
        filter_expression=Attr("id").eq(test_id)
    )
    
    assert len(results) >= 1
    found = any(item["id"] == test_id for item in results)
    assert found, f"Test item {test_id} not found in scan results"


# --- Batch Operations Tests --- #
def test_batch_write_items(dynamo_client):
    """Test batch writing multiple items"""
    # Create test items
    test_items = []
    for i in range(5):
        test_id = f"test-batch-{uuid.uuid4()}"
        test_item_ids.append(test_id)
        test_items.append({
            "id": test_id,
            "displayName": f"Batch User {i}",
            "email": f"batch_{test_id}@example.com",
            "passwordHash": "hashed_password",
            "role": 2,
            "type": 1,
            "active": True,
            "createdAt": datetime.now().isoformat(),
        })
    
    # Batch write
    result = dynamo_client.batch_write_items(test_items)
    
    assert result["success_count"] == 5
    assert len(result["unprocessed_items"]) == 0
    
    # Verify all items were written
    for item in test_items:
        retrieved = dynamo_client.get_item(key={"id": item["id"]})
        assert retrieved["id"] == item["id"]


def test_batch_delete_items(dynamo_client):
    """Test batch deleting multiple items"""
    # Create test items
    test_items = []
    keys = []
    for i in range(3):
        test_id = f"test-batch-delete-{uuid.uuid4()}"
        keys.append({"id": test_id})
        test_items.append({
            "id": test_id,
            "displayName": f"Delete User {i}",
            "email": f"delete_{test_id}@example.com",
            "passwordHash": "hashed_password",
            "role": 2,
            "type": 1,
            "active": True,
            "createdAt": datetime.now().isoformat(),
        })
    
    # Write items first
    dynamo_client.batch_write_items(test_items)
    
    # Batch delete
    result = dynamo_client.batch_delete_items(keys)
    
    assert result["success_count"] == 3
    assert len(result["unprocessed_keys"]) == 0
    
    # Verify all items were deleted
    for key in keys:
        retrieved = dynamo_client.get_item(key=key)
        assert retrieved == {}


def test_batch_write_large_batch(dynamo_client):
    """Test batch write with more than 25 items (DynamoDB batch limit)"""
    # Create 30 test items (more than the 25 item batch limit)
    test_items = []
    for i in range(30):
        test_id = f"test-large-batch-{uuid.uuid4()}"
        test_item_ids.append(test_id)
        test_items.append({
            "id": test_id,
            "displayName": f"Large Batch User {i}",
            "email": f"large_{test_id}@example.com",
            "passwordHash": "hashed_password",
            "role": 2,
            "type": 1,
            "active": True,
            "createdAt": datetime.now().isoformat(),
        })
    
    # Batch write (should automatically handle multiple batches)
    result = dynamo_client.batch_write_items(test_items)
    
    assert result["success_count"] == 30
    print(f"✓ Successfully wrote {result['success_count']} items across multiple batches")


# --- Error Handling Tests --- #
def test_get_nonexistent_item(dynamo_client):
    """Test getting an item that doesn't exist"""
    result = dynamo_client.get_item(key={"id": "nonexistent-id-12345"})
    assert result == {}


def test_query_gsi_no_results(dynamo_client):
    """Test querying GSI with no matching results"""
    results = dynamo_client.query_gsi(
        index_name="email-index",
        key_condition_expression=Key("email").eq("nonexistent@example.com")
    )
    assert results == []


def test_batch_write_empty_list(dynamo_client):
    """Test batch write with empty list"""
    result = dynamo_client.batch_write_items([])
    assert result["success_count"] == 0
    assert result["unprocessed_items"] == []


def test_batch_delete_empty_list(dynamo_client):
    """Test batch delete with empty list"""
    result = dynamo_client.batch_delete_items([])
    assert result["success_count"] == 0
    assert result["unprocessed_keys"] == []
