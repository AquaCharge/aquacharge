from dataclasses import dataclass, field
from typing import Dict, Any
import uuid

from .baseModel import BaseModel


@dataclass
class Org(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    displayName: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)
