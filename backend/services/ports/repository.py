from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import BotoCoreError, ClientError

from aws_client import get_ports_table

PORT_FIELD_VARIANTS = {
    "port_id": ("portId", "port_id", "PORT_ID", "id", "ID"),
    "city": ("CITY", "city", "City"),
    "country": ("COUNTRY", "country", "Country"),
    "lat": ("LATITUDE", "latitude", "Latitude", "lat", "Lat"),
    "lng": ("LONGITUDE", "longitude", "Longitude", "lng", "Lng", "lon", "Lon"),
}

PORT_PROJECTION = ", ".join(
    sorted({field for variants in PORT_FIELD_VARIANTS.values() for field in variants})
)

MAX_LIMIT = 500
LATITUDE_FIELDS: Sequence[str] = PORT_FIELD_VARIANTS["lat"]
LONGITUDE_FIELDS: Sequence[str] = PORT_FIELD_VARIANTS["lng"]


def _to_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_first_value(item: Dict, keys: Iterable[str]) -> Optional[object]:
    for key in keys:
        if key in item:
            value = item[key]
            if value is not None and value != "":
                return value
    return None


def _normalize_port(item: Dict) -> Optional[Dict]:
    if not item:
        return None

    lat = _to_float(_get_first_value(item, LATITUDE_FIELDS))
    lng = _to_float(_get_first_value(item, LONGITUDE_FIELDS))
    if lat is None or lng is None:
        return None

    return {
        "portId": _get_first_value(item, PORT_FIELD_VARIANTS["port_id"]),
        "name": _get_first_value(item, PORT_FIELD_VARIANTS["city"]),
        "country": _get_first_value(item, PORT_FIELD_VARIANTS["country"]),
        "lat": lat,
        "lng": lng,
    }


def _build_between_expression(
    attribute_names: Sequence[str], minimum: float, maximum: float
):
    expression = None
    min_decimal = Decimal(str(minimum))
    max_decimal = Decimal(str(maximum))
    for name in attribute_names:
        condition = Attr(name).between(min_decimal, max_decimal)
        expression = condition if expression is None else expression | condition
    return expression


def _build_cross_dateline_expression(
    attribute_names: Sequence[str], minimum: float, maximum: float
):
    expression = None
    min_decimal = Decimal(str(minimum))
    max_decimal = Decimal(str(maximum))
    for name in attribute_names:
        condition = Attr(name).gte(min_decimal) | Attr(name).lte(max_decimal)
        expression = condition if expression is None else expression | condition
    return expression


class PortsRepository:
    def __init__(self, table=None):
        self.table = table or get_ports_table()

    def _scan(self, limit: int, **scan_kwargs) -> List[Dict]:
        limit = min(max(limit, 0), MAX_LIMIT)
        if limit == 0:
            return []

        results: List[Dict] = []
        exclusive_start_key = None

        while len(results) < limit:
            paginated_kwargs = dict(scan_kwargs)
            if exclusive_start_key:
                paginated_kwargs["ExclusiveStartKey"] = exclusive_start_key

            response = self.table.scan(**paginated_kwargs)
            for item in response.get("Items", []):
                normalized = _normalize_port(item)
                if not normalized:
                    continue
                results.append(normalized)
                if len(results) >= limit:
                    break

            exclusive_start_key = response.get("LastEvaluatedKey")
            if not exclusive_start_key:
                break

        return results

    def get_ports_in_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        limit: int = MAX_LIMIT,
    ) -> List[Dict]:
        crosses_dateline = max_lon < min_lon
        lat_expression = _build_between_expression(LATITUDE_FIELDS, min_lat, max_lat)
        lon_expression = (
            _build_between_expression(LONGITUDE_FIELDS, min_lon, max_lon)
            if not crosses_dateline
            else _build_cross_dateline_expression(
                LONGITUDE_FIELDS, min_lon, max_lon
            )
        )
        filter_expression = lat_expression & lon_expression
        scan_kwargs = {
            "FilterExpression": filter_expression,
            "ProjectionExpression": PORT_PROJECTION,
        }
        return self._scan(limit, **scan_kwargs)

    def search_ports_by_name(
        self, query: str, limit: int = 100, include_country: bool = True
    ) -> List[Dict]:
        if not query:
            return []

        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        scan_kwargs = {"ProjectionExpression": PORT_PROJECTION}
        results: List[Dict] = []
        exclusive_start_key = None

        while len(results) < min(limit, MAX_LIMIT):
            paginated_kwargs = dict(scan_kwargs)
            if exclusive_start_key:
                paginated_kwargs["ExclusiveStartKey"] = exclusive_start_key

            response = self.table.scan(**paginated_kwargs)
            for item in response.get("Items", []):
                raw_name = _get_first_value(item, PORT_FIELD_VARIANTS["city"]) or ""
                name = str(raw_name).strip()
                raw_country = _get_first_value(item, PORT_FIELD_VARIANTS["country"]) or ""
                country = str(raw_country).strip()
                if normalized_query in name.lower() or (
                    include_country and normalized_query in country.lower()
                ):
                    normalized = _normalize_port(item)
                    if not normalized:
                        continue
                    results.append(normalized)
                    if len(results) >= limit:
                        break

            exclusive_start_key = response.get("LastEvaluatedKey")
            if not exclusive_start_key:
                break

        return results

    def get_port_by_id(self, port_id: str) -> Optional[Dict]:
        if not port_id:
            return None
        try:
            response = self.table.get_item(
                Key={"portId": port_id},
                ProjectionExpression=PORT_PROJECTION,
            )
        except (BotoCoreError, ClientError):
            raise

        item = response.get("Item")
        return _normalize_port(item)
