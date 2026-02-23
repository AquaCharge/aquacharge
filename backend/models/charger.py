from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum
import decimal
import uuid

from .baseModel import BaseModel


class ChargerStatus(Enum):
    ACTIVE = 1
    MAINTENANCE = 2
    INACTIVE = 3


@dataclass
class Charger(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chargingStationId: str = ""
    chargerType: str = ""
    maxRate: decimal.Decimal = decimal.Decimal(0.0)
    status: ChargerStatus = ChargerStatus.ACTIVE

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        # Migrate legacy 'active' field to 'status'
        if "active" in data:
            active = data.pop("active")
            if "status" not in data or not data["status"]:
                data["status"] = "active" if active else "inactive"
        return cls(**data)
