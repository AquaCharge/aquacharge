from dataclasses import dataclass
from typing import Optional

@dataclass
class Vessel:
    id: str
    user_id: str
    name: str
    vessel_type: str
    battery_capacity: float
    charger_compatibility: list[str]
    registration_number: str
    created_at: str
    updated_at: Optional[str] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'userId': self.user_id,
            'name': self.name,
            'vesselType': self.vessel_type,
            'batteryCapacity': self.battery_capacity,
            'chargerCompatibility': self.charger_compatibility,
            'registrationNumber': self.registration_number,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at
        }