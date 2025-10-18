from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from backend.models.baseModel import BaseModel

# Enum for booking status
class BookingStatus(Enum):
    PENDING = 1
    CONFIRMED = 2
    COMPLETED = 3
    CANCELLED = 4

@dataclass
class Booking(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    userId: str = ""
    vesselId: str = ""
    stationId: str = ""
    startTime: datetime = field(default_factory=datetime.now)
    endTime: datetime = field(default_factory=datetime.now)
    status: BookingStatus = BookingStatus.PENDING
    chargerType: str = ""
    createdAt: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)





