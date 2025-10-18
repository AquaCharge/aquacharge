from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum
import uuid

from backend.models.baseModel import BaseModel


class ChargerStatus(Enum):
    ACTIVE = 1
    MAINTENANCE = 2
    INACTIVE = 3


@dataclass
class Charger(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chargingStationId: str = ""
    chargerType: str = ""
    maxRate: float = 0.0
    active: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)
