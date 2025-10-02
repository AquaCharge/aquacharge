from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Booking:
    id: str
    user_id: str
    vessel_id: str
    station_id: str
    start_time: datetime
    end_time: datetime
    status: str  # 'pending', 'confirmed', 'completed', 'cancelled'
    charger_type: str
    created_at: datetime
    
    def to_dict(self):
        return {
            'id': self.id,
            'userId': self.user_id,
            'vesselId': self.vessel_id,
            'stationId': self.station_id,
            'startTime': self.start_time.isoformat(),
            'endTime': self.end_time.isoformat(),
            'status': self.status,
            'chargerType': self.charger_type,
            'createdAt': self.created_at.isoformat()
        }