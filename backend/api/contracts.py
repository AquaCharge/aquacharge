from flask import Blueprint, jsonify, request
from models.contract import Contract, ContractStatus
from middleware.auth import require_auth, require_role
from datetime import datetime
from db.dynamoClient import DynamoClient
from decimal import Decimal

contracts_bp = Blueprint("contracts", __name__)

dynamoDB_client = DynamoClient(
    table_name="aquacharge-contracts-dev", region_name="us-east-1"
)


def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


@contracts_bp.route("", methods=["GET"])
@require_auth
@require_role("ADMIN")
def get_contracts():
    """Get all contracts with optional filtering"""
    try:
        # Get query parameters
        status_filter = request.args.get("status")
        vessel_id = request.args.get("vesselId")
        contracts = dynamoDB_client.scan_items()

        # Filter contracts
        filtered_contracts = []
        for contract in contracts:
            # Apply status filter
            if status_filter and contract["status"] != status_filter:
                continue
            # Apply vessel filter
            if vessel_id and contract.get("vesselId") != vessel_id:
                continue
            contract = Contract.from_dict(contract)
            filtered_contracts.append(contract.to_public_dict())

        # Sort by creation date (newest first)
        filtered_contracts.sort(key=lambda x: x["createdAt"], reverse=True)

        return jsonify(convert_decimals(filtered_contracts)), 200

    except Exception as e:
        return (
            jsonify({"error": "Failed to retrieve contracts", "details": str(e)}),
            500,
        )


@contracts_bp.route("/<contract_id>", methods=["GET"])
@require_auth
@require_role("ADMIN")
def get_contract(contract_id: str):
    """Get a specific contract by ID"""
    contract = dynamoDB_client.get_item(key={"id": contract_id})
    try:
        if not contract:
            return jsonify({"error": "Contract not found"}), 404

        contract = Contract.from_dict(contract)
        return jsonify(convert_decimals(contract.to_public_dict())), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve contract", "details": str(e)}), 500


@contracts_bp.route("", methods=["POST"])
@require_auth
@require_role("ADMIN")
def create_contract():
    """Create a new contract"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            "vesselId",
            "drEventId",
            "vesselName",
            "energyAmount",
            "pricePerKwh",
            "startTime",
            "endTime",
            "terms",
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        # Parse datetime strings
        try:
            start_time = datetime.fromisoformat(
                data["startTime"].replace("Z", "+00:00")
            )
            end_time = datetime.fromisoformat(data["endTime"].replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid date format. Use ISO format."}), 400

        # Create contract instance
        booking_id = data.get("bookingId")
        if isinstance(booking_id, str):
            booking_id = booking_id.strip() or None

        contract = Contract(
            bookingId=booking_id,
            vesselId=data["vesselId"],
            drEventId=data["drEventId"],
            vesselName=data["vesselName"],
            energyAmount=Decimal(str(data["energyAmount"])),
            pricePerKwh=Decimal(str(data["pricePerKwh"])),
            startTime=start_time,
            endTime=end_time,
            terms=data["terms"],
            createdBy=data.get("createdBy", "unknown"),
        )

        # Calculate total value
        contract.totalValue = contract.energyAmount * contract.pricePerKwh

        # Validate contract data
        contract.validate()

        # Store contract
        contract_item = contract.to_dict()
        contract_item = {k: v for k, v in contract_item.items() if v is not None}
        dynamoDB_client.put_item(item=contract_item)

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract created successfully",
                        "contract": contract.to_public_dict(),
                    }
                )
            ),
            201,
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to create contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>", methods=["PUT"])
def update_contract(contract_id: str):
    """Update a contract"""
    contract = dynamoDB_client.get_item(key={"id": contract_id})
    try:
        if not contract:
            return jsonify({"error": "Contract not found"}), 404

        data = request.get_json()
        contract = Contract.from_dict(contract)
        # Update fields if provided
        if "status" in data:
            if data["status"] not in [status.value for status in ContractStatus]:
                return jsonify({"error": "Invalid status"}), 400
            contract.status = data["status"]

        if "terms" in data:
            contract.terms = data["terms"]

        # Update timestamp
        contract.updatedAt = datetime.now()

        dynamoDB_client.update_item(
            key={"id": contract_id},
            update_data={
                "status": contract.status,
                "terms": contract.terms,
                "updatedAt": contract.updatedAt.isoformat(),
            },
        )
        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract updated successfully",
                        "contract": contract.to_public_dict(),
                    }
                )
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Failed to update contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>/cancel", methods=["POST"])
def cancel_contract(contract_id: str):
    """Cancel a pending contract"""
    contract = dynamoDB_client.get_item(key={"id": contract_id})
    try:
        if not contract:
            return jsonify({"error": "Contract not found"}), 404

        contract = Contract.from_dict(contract)

        if contract.status != ContractStatus.PENDING.value:
            return jsonify({"error": "Only pending contracts can be cancelled"}), 400

        contract.status = ContractStatus.CANCELLED.value
        contract.updatedAt = datetime.now()

        dynamoDB_client.update_item(
            key={"id": contract_id},
            update_data={
                "status": contract.status,
                "updatedAt": contract.updatedAt.isoformat(),
            },
        )

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract cancelled successfully",
                        "contract": contract.to_public_dict(),
                    }
                )
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Failed to cancel contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>/complete", methods=["POST"])
def complete_contract(contract_id: str):
    """Mark a contract as completed"""
    contract = dynamoDB_client.get_item(key={"id": contract_id})
    try:
        if not contract:
            return jsonify({"error": "Contract not found"}), 404

        contract = Contract.from_dict(contract)

        if contract.status not in [
            ContractStatus.PENDING.value,
            ContractStatus.ACTIVE.value,
        ]:
            return (
                jsonify({"error": "Only pending or active contracts can be completed"}),
                400,
            )

        contract.status = ContractStatus.COMPLETED.value
        contract.updatedAt = datetime.now()
        dynamoDB_client.update_item(
            key={"id": contract_id},
            update_data={
                "status": contract.status,
                "updatedAt": contract.updatedAt.isoformat(),
            },
        )

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract completed successfully",
                        "contract": contract.to_public_dict(),
                    }
                )
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Failed to complete contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>", methods=["DELETE"])
def delete_contract(contract_id: str):
    """Delete a contract (admin only)"""
    contract = dynamoDB_client.get_item(key={"id": contract_id})
    try:
        if not contract:
            return jsonify({"error": "Contract not found"}), 404

        dynamoDB_client.delete_item(key={"id": contract_id})

        return jsonify({"message": "Contract deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to delete contract", "details": str(e)}), 500
