from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class UserDataVautltCreate(BaseModel):
    user_id: UUID
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
