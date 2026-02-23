import boto3
from botocore.exceptions import ClientError


class DynamoClient:
    def __init__(self, table_name: str, region_name: str):
        self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.dynamodb.Table(table_name)

    def put_item(self, item: dict):
        try:
            response = self.table.put_item(Item=item)
            return response
        except Exception as e:
            print(f"Error putting item: {e}")
            raise

    def put_item_conditional(
        self,
        item: dict,
        condition_expression,
        expression_attribute_names=None,
        expression_attribute_values=None,
    ) -> dict:
        """
        Put an item only if a condition is met.

        Args:
            item: The item to write.
            condition_expression: A ConditionExpression (string or boto3 Attr/Key condition).
            expression_attribute_names: Optional name placeholders.
            expression_attribute_values: Optional value placeholders.

        Returns:
            The DynamoDB response on success, or None if the condition failed.
        """
        try:
            params = {
                "Item": item,
                "ConditionExpression": condition_expression,
            }
            if expression_attribute_names is not None:
                params["ExpressionAttributeNames"] = expression_attribute_names
            if expression_attribute_values is not None:
                params["ExpressionAttributeValues"] = expression_attribute_values

            response = self.table.put_item(**params)
            return response
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            print(f"Error in conditional put: {e}")
            raise
        except Exception as e:
            print(f"Error in conditional put: {e}")
            raise

    def get_item(self, key: dict) -> dict:
        try:
            response = self.table.get_item(Key=key)
            return response.get("Item", {})
        except Exception as e:
            print(f"Error getting item: {e}")
            raise

    def query_items(
        self, key_condition_expression, expression_attribute_values
    ) -> list:
        try:
            response = self.table.query(
                KeyConditionExpression=key_condition_expression,
                ExpressionAttributeValues=expression_attribute_values,
            )
            return response.get("Items", [])
        except Exception as e:
            print(f"Error querying items: {e}")
            raise

    def scan_items(
        self, filter_expression=None, expression_attribute_values=None
    ) -> list:
        try:
            if filter_expression and expression_attribute_values:
                response = self.table.scan(
                    FilterExpression=filter_expression,
                    ExpressionAttributeValues=expression_attribute_values,
                )
            else:
                response = self.table.scan()
            return response.get("Items", [])
        except Exception as e:
            print(f"Error scanning items: {e}")
            raise

    def delete_item(self, key: dict) -> dict:
        try:
            response = self.table.delete_item(Key=key)
            return response
        except Exception as e:
            print(f"Error deleting item: {e}")
            raise

    def update_item(self, key: dict, update_data: dict) -> dict:
        try:
            # Build the update expression and attribute values dynamically
            update_expression_parts = []
            expression_attribute_values = {}
            expression_attribute_names = {}

            for i, (field, value) in enumerate(update_data.items()):
                placeholder = f":val{i}"
                name_placeholder = f"#field{i}"

                update_expression_parts.append(f"{name_placeholder} = {placeholder}")
                expression_attribute_values[placeholder] = value
                expression_attribute_names[name_placeholder] = field

            update_expression = "SET " + ", ".join(update_expression_parts)

            response = self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                ReturnValues="ALL_NEW",  # Returns the updated item
            )

            return response.get("Attributes", {})
        except Exception as e:
            print(f"Error updating item: {e}")
            raise

    def query_gsi(
        self,
        index_name: str,
        key_condition_expression,
        expression_attribute_values=None,
    ) -> list:
        """
        Query a Global Secondary Index

        Args:
            index_name: Name of the GSI (e.g., "email-index")
            key_condition_expression: Condition expression (use Key() from boto3.dynamodb.conditions)
            expression_attribute_values: Optional values dict (only used with string expressions)

        Returns:
            List of items matching the query
        """
        try:
            query_params = {
                "IndexName": index_name,
                "KeyConditionExpression": key_condition_expression,
            }

            # Only add ExpressionAttributeValues if provided and not None
            if expression_attribute_values is not None:
                query_params["ExpressionAttributeValues"] = expression_attribute_values

            response = self.table.query(**query_params)
            return response.get("Items", [])
        except Exception as e:
            print(f"Error querying GSI: {e}")
            raise

    def batch_write_items(self, items: list) -> dict:
        """
        Write multiple items in batches (up to 25 items per batch).
        DynamoDB limits batch_write to 25 items per request.

        Args:
            items: List of dictionaries representing items to write

        Returns:
            Dictionary with success count and any unprocessed items
        """
        try:
            if not items:
                return {"success_count": 0, "unprocessed_items": []}

            success_count = 0
            unprocessed_items = []

            # Process in batches of 25 (DynamoDB limit)
            batch_size = 25
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]

                # Build the batch write request
                request_items = {
                    self.table.table_name: [
                        {"PutRequest": {"Item": item}} for item in batch
                    ]
                }

                response = self.dynamodb.batch_write_item(RequestItems=request_items)

                # Count successful writes
                success_count += len(batch)

                # Handle unprocessed items (due to throttling or other issues)
                unprocessed = response.get("UnprocessedItems", {})
                if unprocessed and self.table.table_name in unprocessed:
                    unprocessed_batch = unprocessed[self.table.table_name]
                    for req in unprocessed_batch:
                        if "PutRequest" in req:
                            unprocessed_items.append(req["PutRequest"]["Item"])
                            success_count -= 1

            return {
                "success_count": success_count,
                "unprocessed_items": unprocessed_items,
            }
        except Exception as e:
            print(f"Error in batch write: {e}")
            raise

    def batch_delete_items(self, keys: list) -> dict:
        """
        Delete multiple items in batches (up to 25 items per batch).
        DynamoDB limits batch_write to 25 items per request.

        Args:
            keys: List of key dictionaries (e.g., [{"id": "123"}, {"id": "456"}])

        Returns:
            Dictionary with success count and any unprocessed keys
        """
        try:
            if not keys:
                return {"success_count": 0, "unprocessed_keys": []}

            success_count = 0
            unprocessed_keys = []

            # Process in batches of 25 (DynamoDB limit)
            batch_size = 25
            for i in range(0, len(keys), batch_size):
                batch = keys[i : i + batch_size]

                # Build the batch write request
                request_items = {
                    self.table.table_name: [
                        {"DeleteRequest": {"Key": key}} for key in batch
                    ]
                }

                response = self.dynamodb.batch_write_item(RequestItems=request_items)

                # Count successful deletes
                success_count += len(batch)

                # Handle unprocessed items (due to throttling or other issues)
                unprocessed = response.get("UnprocessedItems", {})
                if unprocessed and self.table.table_name in unprocessed:
                    unprocessed_batch = unprocessed[self.table.table_name]
                    for req in unprocessed_batch:
                        if "DeleteRequest" in req:
                            unprocessed_keys.append(req["DeleteRequest"]["Key"])
                            success_count -= 1

            return {
                "success_count": success_count,
                "unprocessed_keys": unprocessed_keys,
            }
        except Exception as e:
            print(f"Error in batch delete: {e}")
            raise
