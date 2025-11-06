from flask import Blueprint, jsonify, request
from models.contract import Contract, ContractStatus
from middleware.auth import require_auth, require_role
from datetime import datetime
from db.dynamodb import db_client

contracts_bp = Blueprint("contracts", __name__)


@contracts_bp.route("", methods=["GET"])
@require_auth
@require_role("ADMIN")
def get_contracts():
    """Get all contracts with optional filtering"""
    try:
        # Get query parameters
        status_filter = request.args.get("status")
        vessel_id = request.args.get("vesselId")

        # Fetch contracts from DynamoDB
        if vessel_id:
            contracts_data = db_client.get_contracts_by_vessel(vessel_id)
        else:
            contracts_data = db_client.scan_table(db_client.contracts_table_name, limit=1000)

        # Filter by status if provided
        filtered_contracts = []
        for contract_data in contracts_data:
            contract = Contract.from_dict(contract_data)
            if status_filter and contract.status != status_filter:
                continue
            filtered_contracts.append(contract.to_public_dict())

        # Sort by creation date (newest first)
        filtered_contracts.sort(key=lambda x: x["createdAt"], reverse=True)

        return jsonify(filtered_contracts), 200

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
    try:
        contract_data = db_client.get_contract_by_id(contract_id)
        
        if not contract_data:
            return jsonify({"error": "Contract not found"}), 404

        contract = Contract.from_dict(contract_data)
        return jsonify(contract.to_public_dict()), 200

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
        contract = Contract(
            vesselId=data["vesselId"],
            vesselName=data["vesselName"],
            energyAmount=float(data["energyAmount"]),
            pricePerKwh=float(data["pricePerKwh"]),
            startTime=start_time,
            endTime=end_time,
            terms=data["terms"],
            createdBy=data.get("createdBy", "unknown"),
        )

        # Calculate total value
        contract.totalValue = contract.energyAmount * contract.pricePerKwh

        # Validate contract data
        contract.validate()

        # Store contract in DynamoDB
        db_client.create_contract(contract.to_dict())

        return (
            jsonify(
                {
                    "message": "Contract created successfully",
                    "contract": contract.to_public_dict(),
                }
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
    try:
        contract_data = db_client.get_contract_by_id(contract_id)
        
        if not contract_data:
            return jsonify({"error": "Contract not found"}), 404

        data = request.get_json()
        contract = Contract.from_dict(contract_data)

        # Update fields if provided
        if "status" in data:
            if data["status"] not in [status.value for status in ContractStatus]:
                return jsonify({"error": "Invalid status"}), 400
            contract.status = data["status"]

        if "terms" in data:
            contract.terms = data["terms"]

        # Update timestamp
        contract.updatedAt = datetime.now()

        # Update in DynamoDB
        db_client.put_item(db_client.contracts_table_name, contract.to_dict())

        return (
            jsonify(
                {
                    "message": "Contract updated successfully",
                    "contract": contract.to_public_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Failed to update contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>/cancel", methods=["POST"])
def cancel_contract(contract_id: str):
    """Cancel a pending contract"""
    try:
        contract_data = db_client.get_contract_by_id(contract_id)
        
        if not contract_data:
            return jsonify({"error": "Contract not found"}), 404

        contract = Contract.from_dict(contract_data)

        if contract.status != ContractStatus.PENDING.value:
            return jsonify({"error": "Only pending contracts can be cancelled"}), 400

        contract.status = ContractStatus.CANCELLED.value
        contract.updatedAt = datetime.now()

        # Update in DynamoDB
        db_client.put_item(db_client.contracts_table_name, contract.to_dict())

        return (
            jsonify(
                {
                    "message": "Contract cancelled successfully",
                    "contract": contract.to_public_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Failed to cancel contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>/complete", methods=["POST"])
def complete_contract(contract_id: str):
    """Mark a contract as completed"""
    try:
        contract_data = db_client.get_contract_by_id(contract_id)
        
        if not contract_data:
            return jsonify({"error": "Contract not found"}), 404

        contract = Contract.from_dict(contract_data)

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

        # Update in DynamoDB
        db_client.put_item(db_client.contracts_table_name, contract.to_dict())

        return (
            jsonify(
                {
                    "message": "Contract completed successfully",
                    "contract": contract.to_public_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Failed to complete contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>", methods=["DELETE"])
def delete_contract(contract_id: str):
    """Delete a contract (admin only)"""
    try:
        contract_data = db_client.get_contract_by_id(contract_id)
        
        if not contract_data:
            return jsonify({"error": "Contract not found"}), 404

        db_client.delete_item(db_client.contracts_table_name, {"id": contract_id})

        return jsonify({"message": "Contract deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to delete contract", "details": str(e)}), 500
