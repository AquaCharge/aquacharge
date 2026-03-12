from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from .baseModel import BaseModel


@dataclass
class Vessel(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    userId: str = ""
    displayName: str = ""
    vesselType: str = ""
    chargerType: str = ""
    capacity: float = 0.0
    maxCapacity: float = 0.0
    maxChargeRate: float = 0.0
    minChargeRate: float = 0.0
    maxDischargeRate: float = 0.0
    longitude: float = 0.0
    latitude: float = 0.0
    rangeMeters: float = 0.0
    active: bool = True
    createdAt: datetime = field(default_factory=datetime.now)
    updatedAt: Optional[datetime] = None

    def validate(self) -> bool:
        """Validate model: capacity must not exceed maxCapacity."""
        if self.maxCapacity > 0 and self.capacity > self.maxCapacity:
            return False
        return True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        # Normalize numeric types from DynamoDB (Decimal -> float)
        normalized = dict(data)
        for key in (
            "capacity",
            "maxCapacity",
            "maxChargeRate",
            "minChargeRate",
            "maxDischargeRate",
            "longitude",
            "latitude",
            "rangeMeters",
        ):
            if key in normalized and normalized[key] is not None:
                normalized[key] = float(normalized[key])
        return cls(**normalized)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dict suitable for DynamoDB; ensure numeric capacity fields are Decimal."""
        data = super().to_dict()
        try:
            from decimal import Decimal

            if "capacity" in data and data["capacity"] is not None:
                data["capacity"] = Decimal(str(data["capacity"]))
            if "maxCapacity" in data and data["maxCapacity"] is not None:
                data["maxCapacity"] = Decimal(str(data["maxCapacity"]))
        except Exception:
            pass
        return data
