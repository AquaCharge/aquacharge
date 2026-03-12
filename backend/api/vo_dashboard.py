"""VO (Vessel Operator) dashboard API: aggregated metrics and current vessel."""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from boto3.dynamodb.conditions import Key

from db.dynamoClient import DynamoClient
from middleware.auth import require_auth
from services.contracts import ContractService, convert_decimals

vo_dashboard_bp = Blueprint("vo_dashboard", __name__)

_users_client = DynamoClient(table_name="aquacharge-users-dev", region_name="us-east-1")
_vessels_client = DynamoClient(
    table_name="aquacharge-vessels-dev", region_name="us-east-1"
)
contract_service = ContractService()


def _parse_iso(dt_string):
    if not dt_string:
        return None
    if isinstance(dt_string, datetime):
        return dt_string
    return datetime.fromisoformat(str(dt_string).replace("Z", "+00:00"))


@vo_dashboard_bp.route("/dashboard", methods=["GET"])
@require_auth
def get_vo_dashboard():
    """Get VO dashboard: current vessel SoC, discharge rate, metrics, active contract."""
    try:
        user_id = request.current_user.get("user_id")
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        user_id = str(user_id)

        user_data = _users_client.get_item(key={"id": user_id})
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        current_vessel_id = (user_data.get("currentVesselId") or "").strip() or None

        vessels = _vessels_client.query_gsi(
            index_name="userId-index",
            key_condition_expression=Key("userId").eq(user_id),
        )
        vessel_ids = [v["id"] for v in vessels] if vessels else []

        now = datetime.now(timezone.utc)

        # If user has no current vessel but has vessels, set current to first vessel
        if not current_vessel_id and vessel_ids:
            first_vessel_id = vessel_ids[0]
            _users_client.update_item(
                key={"id": user_id},
                update_data={
                    "currentVesselId": first_vessel_id,
                    "updatedAt": now.isoformat(),
                },
            )
            current_vessel_id = first_vessel_id
            user_data = _users_client.get_item(key={"id": user_id}) or user_data

        all_contracts = []
        for vid in vessel_ids:
            all_contracts.extend(
                contract_service.list_contracts(status_filter=None, vessel_id=vid)
            )

        now = datetime.now(timezone.utc)
        contracts_completed = sum(
            1 for c in all_contracts if c.get("status") == "completed"
        )
        total_kwh_discharged = sum(
            float(c.get("energyAmount") or 0)
            for c in all_contracts
            if c.get("status") in ("completed", "active")
        )
        total_earnings = sum(
            float(c.get("totalValue") or 0)
            for c in all_contracts
            if c.get("status") == "completed"
        )

        active_contract = None
        for c in all_contracts:
            if c.get("status") != "active":
                continue
            end_dt = _parse_iso(c.get("endTime"))
            if not end_dt:
                continue
            end_utc = end_dt if end_dt.tzinfo else end_dt.replace(tzinfo=timezone.utc)
            if end_utc > now:
                active_contract = {
                    "id": c.get("id"),
                    "endTime": c.get("endTime"),
                    "timeRemainingSeconds": max(
                        0, int((end_utc - now).total_seconds())
                    ),
                    "estimatedEarnings": float(c.get("totalValue") or 0),
                    "energyAmountKwh": float(c.get("energyAmount") or 0),
                }
                break

        current_vessel_payload = None
        if current_vessel_id and current_vessel_id in vessel_ids:
            vessel_data = _vessels_client.get_item(key={"id": current_vessel_id})
            if vessel_data:
                cap = float(vessel_data.get("capacity") or 0)
                max_cap = float(vessel_data.get("maxCapacity") or 0)
                soc = (cap / max_cap * 100.0) if max_cap > 0 else None
                current_vessel_payload = {
                    "id": vessel_data.get("id"),
                    "displayName": vessel_data.get("displayName") or "",
                    "socPercent": round(soc, 1) if soc is not None else None,
                    "dischargeRateKw": float(vessel_data.get("maxDischargeRate") or 0),
                    "capacityKwh": cap,
                    "maxCapacityKwh": max_cap,
                }

        payload = {
            "currentVessel": current_vessel_payload,
            "activeContract": active_contract,
            "metrics": {
                "contractsCompleted": contracts_completed,
                "totalKwhDischarged": round(total_kwh_discharged, 2),
                "totalEarnings": round(total_earnings, 2),
            },
            "updatedAt": now.isoformat(),
        }
        return jsonify(convert_decimals(payload)), 200

    except Exception as e:
        return jsonify({"error": "Failed to load dashboard", "details": str(e)}), 500
