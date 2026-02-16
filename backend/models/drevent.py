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
    COMPLETED = "Completed"
    SETTLED = "Settled"
    ARCHIVED = "Archived"


@dataclass
class DREvent(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stationId: str = ""
    contractId: str = ""
    pricePerKwh: float = 0.0
    targetEnergyKwh: float = 0.0
    maxParticipants: int = 0
    startTime: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=2))
    endTime: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=5))
    status: EventStatus = EventStatus.CREATED
    details: Optional[Dict[str, Any]] = None

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