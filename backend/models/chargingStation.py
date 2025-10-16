from dataclasses import dataclass
from typing import List

@dataclass
class ChargingStation:
    id: str
    name: str
    location: dict  # {'latitude': float, 'longitude': float}
    charger_types: List[str]
    total_chargers: int
    available_chargers: int
    status: str  # 'active', 'maintenance', 'inactive'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'chargerTypes': self.charger_types,
            'totalChargers': self.total_chargers,
            'availableChargers': self.available_chargers,
            'status': self.status
        }