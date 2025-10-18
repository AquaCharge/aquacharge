from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum
import uuid

from .baseModel import BaseModel


class StationStatus(Enum):
    ACTIVE = 1
    MAINTENANCE = 2
    INACTIVE = 3


@dataclass
class Station(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    displayName: str = ""
    longitude: float = 0.0
    latitude: float = 0.0
    city: str = ""
    provinceOrState: str = ""
    country: str = ""
    status: StationStatus = StationStatus.ACTIVE

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)
