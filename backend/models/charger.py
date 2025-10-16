from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
from typing import Optional, Dict, Any

from backend.models.baseModel import BaseModel
from backend.models.station import StationStatus

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