from flask import Blueprint, jsonify, request
from middleware.auth import require_auth, require_role
from services.contracts import ContractService, ContractServiceError, convert_decimals

contracts_bp = Blueprint("contracts", __name__)
contract_service = ContractService()


@contracts_bp.route("", methods=["GET"])
@require_auth
@require_role("ADMIN")
def get_contracts():
    """Get all contracts with optional filtering"""
    try:
        status_filter = request.args.get("status")
        vessel_id = request.args.get("vesselId")
        filtered_contracts = contract_service.list_contracts(
            status_filter=status_filter,
            vessel_id=vessel_id,
        )

        return jsonify(convert_decimals(filtered_contracts)), 200

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
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
        contract = contract_service.get_contract(contract_id)
        return jsonify(convert_decimals(contract)), 200

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to retrieve contract", "details": str(e)}), 500


@contracts_bp.route("", methods=["POST"])
@require_auth
@require_role("ADMIN")
def create_contract():
    """Create a new contract"""
    try:
        data = request.get_json()
        contract = contract_service.create_contract(data)

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract created successfully",
                        "contract": contract,
                    }
                )
            ),
            201,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to create contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>", methods=["PUT"])
def update_contract(contract_id: str):
    """Update a contract"""
    try:
        data = request.get_json()
        contract = contract_service.update_contract(contract_id, data)
        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract updated successfully",
                        "contract": contract,
                    }
                )
            ),
            200,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to update contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>/cancel", methods=["POST"])
def cancel_contract(contract_id: str):
    """Cancel a pending contract"""
    try:
        contract = contract_service.cancel_contract(contract_id)

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract cancelled successfully",
                        "contract": contract,
                    }
                )
            ),
            200,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to cancel contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>/complete", methods=["POST"])
def complete_contract(contract_id: str):
    """Mark a contract as completed"""
    try:
        contract = contract_service.complete_contract(contract_id)

        return (
            jsonify(
                convert_decimals(
                    {
                        "message": "Contract completed successfully",
                        "contract": contract,
                    }
                )
            ),
            200,
        )

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to complete contract", "details": str(e)}), 500


@contracts_bp.route("/<contract_id>", methods=["DELETE"])
def delete_contract(contract_id: str):
    """Delete a contract (admin only)"""
    try:
        contract_service.delete_contract(contract_id)

        return jsonify({"message": "Contract deleted successfully"}), 200

    except ContractServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    except Exception as e:
        return jsonify({"error": "Failed to delete contract", "details": str(e)}), 500
