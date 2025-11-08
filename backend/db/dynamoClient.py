import boto3


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


# Example usage:
# dynamo_client = DynamoClient(table_name="your-table-name", region_name="us-east-1")
# dynamo_client.put_item({"id": "123", "name": "Sample Item"})
