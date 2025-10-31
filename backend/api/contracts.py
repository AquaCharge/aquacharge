from flask import Blueprint, jsonify, request
from models.contract import Contract, ContractStatus
from middleware.auth import require_auth, require_role
from datetime import datetime
from typing import Dict

contracts_bp = Blueprint("contracts", __name__)

# In-memory storage (replace with actual database)
contracts_db: Dict[str, Contract] = {}


# Initialize with sample contracts
def init_sample_contracts():
    if not contracts_db:  # Only initialize if empty

        sample_contracts = [
            Contract(
                id="contract-001",
                vesselId="vessel-001",
                vesselName="Sea Breeze",
                energyAmount=150.0,
                pricePerKwh=0.15,
                totalValue=22.50,
                startTime=datetime(2025, 10, 27, 9, 0, 0),
                endTime=datetime(2025, 10, 27, 17, 0, 0),
                status=ContractStatus.ACTIVE.value,
                terms="Standard vessel-to-grid energy transaction terms",
                createdAt=datetime(2025, 10, 26, 10, 0, 0),
                createdBy="user-001",
            ),
            Contract(
                id="contract-002",
                vesselId="vessel-002",
                vesselName="Ocean Explorer",
                energyAmount=200.0,
                pricePerKwh=0.18,
                totalValue=36.00,
                startTime=datetime(2025, 10, 28, 8, 0, 0),
                endTime=datetime(2025, 10, 28, 18, 0, 0),
                status=ContractStatus.PENDING.value,
                terms="Peak hour energy transaction with premium rates",
                createdAt=datetime(2025, 10, 26, 14, 30, 0),
                createdBy="user-001",
            ),
            Contract(
                id="contract-003",
                vesselId="vessel-003",
                vesselName="Wave Runner",
                energyAmount=75.0,
                pricePerKwh=0.12,
                totalValue=9.00,
                startTime=datetime(2025, 10, 25, 14, 0, 0),
                endTime=datetime(2025, 10, 25, 20, 0, 0),
                status=ContractStatus.COMPLETED.value,
                terms="Off-peak energy transaction",
                createdAt=datetime(2025, 10, 25, 8, 0, 0),
                createdBy="user-001",
            ),
            Contract(
                id="contract-004",
                vesselId="vessel-004",
                vesselName="Harbor Master",
                energyAmount=300.0,
                pricePerKwh=0.20,
                totalValue=60.00,
                startTime=datetime(2025, 10, 26, 6, 0, 0),
                endTime=datetime(2025, 10, 26, 12, 0, 0),
                status=ContractStatus.FAILED.value,
                terms="High-capacity energy transfer agreement",
                createdAt=datetime(2025, 10, 25, 18, 0, 0),
                createdBy="user-001",
            ),
        ]

        for contract in sample_contracts:
            contracts_db[contract.id] = contract


# Initialize sample data when module is imported
init_sample_contracts()


@contracts_bp.route("", methods=["GET"])
@require_auth
@require_role("ADMIN")
def get_contracts():
    """Get all contracts with optional filtering"""
    try:
        # Get query parameters
        status_filter = request.args.get("status")
        vessel_id = request.args.get("vesselId")

        # Filter contracts
        filtered_contracts = []
        for contract in contracts_db.values():
            # Apply status filter
            if status_filter and contract.status != status_filter:
                continue
            # Apply vessel filter
            if vessel_id and contract.vesselId != vessel_id:
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
        if contract_id not in contracts_db:
            return jsonify({"error": "Contract not found"}), 404

        contract = contracts_db[contract_id]
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

        # Store contract
        contracts_db[contract.id] = contract

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
        if contract_id not in contracts_db:
            return jsonify({"error": "Contract not found"}), 404

        data = request.get_json()
        contract = contracts_db[contract_id]

        # Update fields if provided
        if "status" in data:
            if data["status"] not in [status.value for status in ContractStatus]:
                return jsonify({"error": "Invalid status"}), 400
            contract.status = data["status"]

        if "terms" in data:
            contract.terms = data["terms"]

        # Update timestamp
        contract.updatedAt = datetime.now()

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
        if contract_id not in contracts_db:
            return jsonify({"error": "Contract not found"}), 404

        contract = contracts_db[contract_id]

        if contract.status != ContractStatus.PENDING.value:
            return jsonify({"error": "Only pending contracts can be cancelled"}), 400

        contract.status = ContractStatus.CANCELLED.value
        contract.updatedAt = datetime.now()

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
        if contract_id not in contracts_db:
            return jsonify({"error": "Contract not found"}), 404

        contract = contracts_db[contract_id]

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
        if contract_id not in contracts_db:
            return jsonify({"error": "Contract not found"}), 404

        del contracts_db[contract_id]

        return jsonify({"message": "Contract deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to delete contract", "details": str(e)}), 500
