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
    maxChargeRate: float = 0.0
    minChargeRate: float = 0.0
    maxDischargeRate: float = 0.0
    longitude: float = 0.0
    latitude: float = 0.0
    rangeMeters: float = 0.0
    active: bool = True
    createdAt: datetime = field(default_factory=datetime.now)
    updatedAt: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)
