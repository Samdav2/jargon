from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from enum import Enum

class Decision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    UN_APPROVE = "un_approve"

class UserDataVautltCreate(BaseModel):
    user_id: Optional[UUID] = None
    data_type: str
    encrypted_data: str
    data_hash: Optional[str] = None

    class config:
        from_attributes = True

class UserDataVaultUpdate(UserDataVautltCreate):
    pass

    class config:
        from_attributes = True

class GetUserData(BaseModel):
    user_id: UUID
    data_type: Optional[list[str]]

class ApproveReject(BaseModel):
    response: Decision

    class config:
        from_attributes = True
