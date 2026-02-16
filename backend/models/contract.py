from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from .baseModel import BaseModel


# Enum for contract status
class ContractStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Contract(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bookingId: str = ""
    vesselId: str = ""
    drEventId: str = ""
    vesselName: str = ""
    energyAmount: float = 0.0  # kWh
    pricePerKwh: float = 0.0  # USD per kWh
    totalValue: float = 0.0  # USD
    startTime: datetime = field(default_factory=datetime.now)
    endTime: datetime = field(default_factory=datetime.now)
    status: str = ContractStatus.PENDING.value
    terms: str = ""
    createdAt: datetime = field(default_factory=datetime.now)
    updatedAt: Optional[datetime] = None
    createdBy: str = ""  # User ID who created the contract

    def __post_init__(self):
        """Calculate total value after initialization"""
        if self.totalValue == 0.0 and self.energyAmount > 0 and self.pricePerKwh > 0:
            self.totalValue = self.energyAmount * self.pricePerKwh

    def validate(self):
        """Validate contract data"""
        if not self.vesselId:
            raise ValueError("Vessel ID is required")
        if not self.drEventId:
            raise ValueError("DR event ID is required")
        if not self.vesselName:
            raise ValueError("Vessel name is required")
        if self.energyAmount <= 0:
            raise ValueError("Energy amount must be greater than 0")
        if self.pricePerKwh <= 0:
            raise ValueError("Price per kWh must be greater than 0")
        if self.startTime >= self.endTime:
            raise ValueError("End time must be after start time")
        if not self.terms:
            raise ValueError("Contract terms are required")

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
        if isinstance(data.get("updatedAt"), str):
            data["updatedAt"] = datetime.fromisoformat(
                data["updatedAt"].replace("Z", "+00:00")
            )

        return cls(**data)

    def to_public_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "bookingId": self.bookingId,
            "vesselId": self.vesselId,
            "drEventId": self.drEventId,
            "vesselName": self.vesselName,
            "energyAmount": self.energyAmount,
            "pricePerKwh": self.pricePerKwh,
            "totalValue": self.totalValue,
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
            "status": self.status,
            "terms": self.terms,
            "createdAt": (
                self.createdAt.isoformat()
                if isinstance(self.createdAt, datetime)
                else self.createdAt
            ),
            "updatedAt": (
                self.updatedAt.isoformat()
                if self.updatedAt and isinstance(self.updatedAt, datetime)
                else self.updatedAt
            ),
            "createdBy": self.createdBy,
        }
