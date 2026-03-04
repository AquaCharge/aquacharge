from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
import uuid

from .baseModel import BaseModel


@dataclass
class Measurement(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vesselId: str = ""
    contractId: str = ""
    drEventId: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    energyKwh: float = 0.0
    powerKw: float = 0.0
    createdAt: datetime = field(default_factory=datetime.now)
    currentSOC: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if "createdAt" in data and isinstance(data["createdAt"], str):
            data["createdAt"] = datetime.fromisoformat(data["createdAt"])
        return cls(**data)
