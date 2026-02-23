from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid

from .baseModel import BaseModel


# Enum for event types
class EventStatus(Enum):
    CREATED = "Created"
    DISPATCHED = "Dispatched"
    ACCEPTED = "Accepted"
    COMMITTED = "Committed"
    ACTIVE = "Active"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"
    SETTLED = "Settled"
    ARCHIVED = "Archived"


@dataclass
class DREvent(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stationId: str = ""
    pricePerKwh: float = 0.0
    targetEnergyKwh: float = 0.0
    maxParticipants: int = 0
    startTime: datetime = field(
        default_factory=lambda: datetime.now() + timedelta(hours=2)
    )
    endTime: datetime = field(
        default_factory=lambda: datetime.now() + timedelta(hours=5)
    )
    status: EventStatus = EventStatus.CREATED
    details: Optional[Dict[str, Any]] = None
    createdAt: Optional[str] = None

    @classmethod
    def validate(self):
        """Validate event data"""
        if self.targetEnergyKwh <= 0:
            raise ValueError("Target energy must be greater than 0")
        if self.pricePerKwh <= 0:
            raise ValueError("Price per kWh must be greater than 0")
        if self.startTime >= self.endTime:
            raise ValueError("End time must be after start time")
        if not self.stationId:
            raise ValueError("Station ID is required")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create Contract instance from dictionary"""
        # Handle datetime parsing
        if isinstance(data.get("startTime"), str):
            data["startTime"] = datetime.fromisoformat(
                data["startTime"].replace("Z", "+00:00")
            )
        if isinstance(data.get("endTime"), str):
            data["endTime"] = datetime.fromisoformat(
                data["endTime"].replace("Z", "+00:00")
            )
        if isinstance(data.get("createdAt"), str):
            data["createdAt"] = datetime.fromisoformat(
                data["createdAt"].replace("Z", "+00:00")
            )

        return cls(**data)

    def to_public_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "stationId": self.stationId,
            "contractId": self.contractId,
            "pricePerKwh": self.pricePerKwh,
            "targetEnergyKwh": self.targetEnergyKwh,
            "maxParticipants": self.maxParticipants,
            "startTime": (
                self.startTime.isoformat()
                if isinstance(self.startTime, datetime)
                else self.startTime
            ),
            "endTime": (
                self.endTime.isoformat()
                if isinstance(self.endTime, datetime)
                else self.endTime
            ),
            "createdAt": self.createdAt,
            "status": self.status.value,
            "details": self.details,
        }
