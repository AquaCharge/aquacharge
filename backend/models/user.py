from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
from typing import Optional, Dict, Any

from backend.models.baseModel import BaseModel

# Enum for user roles
class UserRole(Enum):
    ADMIN = 1
    USER = 2
    OPERATOR = 3

@dataclass
class User(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    email: str = ""
    passwordHash: str = ""
    role: int = UserRole.USER.value
    active: bool = True
    orgId: Optional[str] = None
    createdAt: datetime = field(default_factory=datetime.now)
    updatedAt: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)
    
    def validate(self) -> bool:
        if not self.username or not self.email:
            raise ValueError("Username and email are required")
        if '@' not in self.email:
            raise ValueError("Invalid email format")
        if self.role not in [e.value for e in UserRole]:
            raise ValueError("Invalid user role")
        return True
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Return user data without sensitive information"""
        data = self.to_dict()
        data.pop('passwordHash', None)
        return data
