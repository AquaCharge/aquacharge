from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Dict, Any
from datetime import datetime
import json


class BaseModel(ABC):
    """Base class for all models with common functionality"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for NoSQL storage"""
        data = asdict(self)
        # Handle datetime serialization
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create instance from NoSQL document"""
        pass

    def to_json(self) -> str:
        """Convert model to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str):
        """Create instance from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def validate(self) -> bool:
        """Validate model data - to be overridden by subclasses"""
        return True

    def __repr__(self) -> str:
        """String representation of the model"""
        return f"{self.__class__.__name__}({self.to_dict()})"
