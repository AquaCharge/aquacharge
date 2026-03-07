from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
import uuid
from decimal import Decimal

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
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "vesselId": self.vesselId,
            "contractId": self.contractId,
            "drEventId": self.drEventId,
            "timestamp": self.timestamp.isoformat(),
            "energyKwh": self.energyKwh,
            "powerKw": self.powerKw,
            "createdAt": self.createdAt.isoformat(),
            "currentSOC": self.currentSOC,
        }

        # Convert numeric fields to Decimal for DynamoDB compatibility
        try:
            data["energyKwh"] = Decimal(str(self.energyKwh))
        except Exception:
            data["energyKwh"] = Decimal("0")
        try:
            data["powerKw"] = Decimal(str(self.powerKw))
        except Exception:
            data["powerKw"] = Decimal("0")
        try:
            data["currentSOC"] = Decimal(str(self.currentSOC))
        except Exception:
            data["currentSOC"] = Decimal("0")

        return data

