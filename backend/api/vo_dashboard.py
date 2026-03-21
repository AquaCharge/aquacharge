"""VO (Vessel Operator) dashboard API: aggregated metrics and current vessel."""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request
from boto3.dynamodb.conditions import Key

from db.dynamoClient import DynamoClient
from middleware.auth import require_auth
from services.contracts import ContractService, convert_decimals
import config

vo_dashboard_bp = Blueprint("vo_dashboard", __name__)

_users_client = DynamoClient(table_name=config.USERS_TABLE, region_name=config.AWS_REGION)
_vessels_client = DynamoClient(
    table_name=config.VESSELS_TABLE, region_name=config.AWS_REGION
)
_measurements_client = DynamoClient(
    table_name="aquacharge-measurements-dev", region_name="us-east-1"
)
_drevents_client = DynamoClient(
    table_name="aquacharge-drevents-dev", region_name="us-east-1"
)
_stations_client = DynamoClient(
    table_name="aquacharge-stations-dev", region_name="us-east-1"
)
contract_service = ContractService()


def _parse_iso(dt_string):
    if not dt_string:
        return None
    if isinstance(dt_string, datetime):
        return dt_string
    return datetime.fromisoformat(str(dt_string).replace("Z", "+00:00"))


def _week_start_utc(dt):
    """Monday 00:00:00 UTC for the week containing dt."""
    # weekday(): Monday=0, Sunday=6
    days_since_monday = dt.weekday()
    return (dt.replace(hour=0, minute=0, second=0, microsecond=0)
            - timedelta(days=days_since_monday))


def _weekly_earnings_from_contracts(contracts, now):
    """
    From completed contracts, compute earnings for the current week (Mon–Sun UTC).
    Returns dict: total, dailyEarnings (list of 7 floats, Mon..Sun), todayIndex (0–6).
    """
    week_start = _week_start_utc(now)
    week_end = week_start + timedelta(days=7)
    daily = [0.0] * 7  # Monday=0 .. Sunday=6
    for c in contracts:
        if c.get("status") != "completed":
            continue
        end_dt = _parse_iso(c.get("endTime"))
        if not end_dt:
            continue
        end_utc = end_dt if end_dt.tzinfo else end_dt.replace(tzinfo=timezone.utc)
        if not (week_start <= end_utc < week_end):
            continue
        weekday = end_utc.weekday()  # Monday=0, Sunday=6
        daily[weekday] += float(c.get("totalValue") or 0)
    total = round(sum(daily), 2)
    daily_rounded = [round(x, 2) for x in daily]
    today_index = now.weekday()  # 0=Mon, 6=Sun
    return {
        "total": total,
        "dailyEarnings": daily_rounded,
        "todayIndex": today_index,
    }


def _parse_measurement_timestamp(item: Dict[str, Any]) -> datetime | None:
    raw = item.get("timestamp") or item.get("createdAt")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _enrich_active_contract(payload: Dict[str, Any], raw_contract: Dict[str, Any]):
    """Add DR event details (location, energy progress) when the DR event is active."""
    try:
        dr_event_id = raw_contract.get("drEventId")
        if not dr_event_id:
            return

        dr_event = _drevents_client.get_item(key={"id": dr_event_id})
        if not dr_event:
            return

        event_status = str(dr_event.get("status") or "")
        if event_status.upper() != "ACTIVE":
            return

        payload["drEventStatus"] = event_status

        station_id = dr_event.get("stationId")
        if station_id:
            station = _stations_client.get_item(key={"id": station_id})
            if station:
                payload["station"] = {
                    "id": station.get("id"),
                    "displayName": station.get("displayName", ""),
                    "city": station.get("city", ""),
                    "provinceOrState": station.get("provinceOrState", ""),
                    "latitude": float(station.get("latitude") or 0),
                    "longitude": float(station.get("longitude") or 0),
                }

        contract_id = raw_contract.get("id")
        if contract_id:
            measurements = _measurements_client.query_gsi(
                index_name="contractId-index",
                key_condition_expression=Key("contractId").eq(contract_id),
            )
            total_delivered_kwh = sum(
                float(m.get("energyKwh") or 0) for m in measurements
            )
            committed_kwh = float(raw_contract.get("energyAmount") or 0)
            payload["energyDeliveredKwh"] = round(total_delivered_kwh, 2)
            payload["energyRemainingKwh"] = round(
                max(0, committed_kwh - total_delivered_kwh), 2
            )

        payload["committedPowerKw"] = float(
            raw_contract.get("committedPowerKw") or 0
        )
    except Exception:
        pass


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
        weekly_earnings = _weekly_earnings_from_contracts(all_contracts, now)

        active_contract = None
        raw_active_contract = None
        for c in all_contracts:
            if c.get("status") != "active":
                continue
            end_dt = _parse_iso(c.get("endTime"))
            if not end_dt:
                continue
            end_utc = end_dt if end_dt.tzinfo else end_dt.replace(tzinfo=timezone.utc)
            if end_utc > now:
                start_dt = _parse_iso(c.get("startTime"))
                start_utc = (
                    start_dt if start_dt and start_dt.tzinfo
                    else start_dt.replace(tzinfo=timezone.utc) if start_dt
                    else None
                )
                active_contract = {
                    "id": c.get("id"),
                    "startTime": c.get("startTime"),
                    "endTime": c.get("endTime"),
                    "timeRemainingSeconds": max(0, int((end_utc - now).total_seconds())),
                    "timeWindowSeconds": (
                        max(0, int((end_utc - start_utc).total_seconds()))
                        if start_utc else None
                    ),
                    "estimatedEarnings": float(c.get("totalValue") or 0),
                    "energyAmountKwh": float(c.get("energyAmount") or 0),
                }
                raw_active_contract = c
                break

        if active_contract and raw_active_contract:
            _enrich_active_contract(active_contract, raw_active_contract)

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
            "weeklyEarnings": weekly_earnings,
            "updatedAt": now.isoformat(),
        }
        return jsonify(convert_decimals(payload)), 200

    except Exception as e:
        return jsonify({"error": "Failed to load dashboard", "details": str(e)}), 500


@vo_dashboard_bp.route("/soc-history", methods=["GET"])
@require_auth
def get_weekly_soc_history():
    """
    Time-series SoC history for the authenticated user's current vessel.

    Looks back over the previous 7 *24-hour* days (rolling window) and returns
    measurement-backed SoC points for the vessel currently selected on the VO
    dashboard. This endpoint is intentionally additive and does not change the
    existing /dashboard contract.
    """
    try:
        user_id = request.current_user.get("user_id")
        if user_id is None:
            return jsonify({"error": "Authentication required"}), 401
        user_id = str(user_id)

        user_data = _users_client.get_item(key={"id": user_id})
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        current_vessel_id = (user_data.get("currentVesselId") or "").strip() or None
        if not current_vessel_id:
            return (
                jsonify(
                    {
                        "points": [],
                        "empty": True,
                        "currentVesselId": None,
                        "message": "No current vessel selected",
                    }
                ),
                200,
            )

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=7)

        try:
            measurements: List[Dict[str, Any]] = _measurements_client.scan_items()
        except Exception:
            measurements = []

        series: List[Dict[str, Any]] = []
        for item in measurements:
            if item.get("vesselId") != current_vessel_id:
                continue
            ts = _parse_measurement_timestamp(item)
            if ts is None or ts < window_start or ts > now:
                continue

            soc_value = item.get("currentSOC")
            try:
                soc = float(soc_value)
            except (TypeError, ValueError):
                continue

            if soc < 0 or soc > 200:
                # Discard clearly invalid telemetry rather than breaking the graph.
                continue

            series.append(
                {
                    "timestamp": ts.isoformat(),
                    "socPercent": round(soc, 2),
                }
            )

        series.sort(key=lambda point: point["timestamp"])

        payload = {
            "currentVesselId": current_vessel_id,
            "points": series,
            "empty": len(series) == 0,
            "windowStart": window_start.isoformat(),
            "windowEnd": now.isoformat(),
        }
        return jsonify(convert_decimals(payload)), 200

    except Exception as e:  # pragma: no cover - defensive logging path
        return (
            jsonify(
                {
                    "error": "Failed to load SoC history",
                    "details": str(e),
                }
            ),
            500,
        )
