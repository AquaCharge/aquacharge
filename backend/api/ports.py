from botocore.exceptions import BotoCoreError, ClientError
from flask import Blueprint, jsonify, request

from services.ports.repository import PortsRepository

ports_bp = Blueprint("ports", __name__)

DEFAULT_LIMIT = 200
MAX_LIMIT = 500
ports_repo = PortsRepository()


def _parse_limit(raw_value) -> int:
    if raw_value is None:
        return DEFAULT_LIMIT
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc

    if value <= 0:
        raise ValueError("limit must be positive")
    return min(value, MAX_LIMIT)


def _parse_bbox(raw_bbox: str):
    parts = raw_bbox.split(",")
    if len(parts) != 4:
        raise ValueError("bbox must contain four comma-separated values")
    try:
        min_lon, min_lat, max_lon, max_lat = map(float, parts)
    except ValueError as exc:
        raise ValueError("bbox values must be numeric") from exc

    if max_lat <= min_lat:
        raise ValueError("bbox max latitude must be greater than min latitude")

    return min_lon, min_lat, max_lon, max_lat


@ports_bp.route("", methods=["GET"])
def list_ports():
    bbox_raw = request.args.get("bbox")
    query = request.args.get("q")
    query_normalized = query.strip() if query else None

    try:
        limit = _parse_limit(request.args.get("limit"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        if bbox_raw:
            bbox = _parse_bbox(bbox_raw)
            ports = ports_repo.get_ports_in_bbox(*bbox, limit=limit)
            if query_normalized:
                q_lower = query_normalized.lower()
                ports = [
                    port
                    for port in ports
                    if q_lower in (port.get("name") or "").lower()
                    or q_lower in (port.get("country") or "").lower()
                ][:limit]
        elif query_normalized:
            ports = ports_repo.search_ports_by_name(query_normalized, limit=limit)
        else:
            ports = []
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except (BotoCoreError, ClientError):
        return jsonify({"error": "Unable to load ports"}), 500
    except Exception:
        return jsonify({"error": "Unable to load ports"}), 500

    return jsonify({"ports": ports})
