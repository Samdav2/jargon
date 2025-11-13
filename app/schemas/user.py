from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class UserCreate(BaseModel):
    password: str
    email: str
    name: str
    primary_phone: Optional[str] = None

    class config:
        from_attributes = True

class UserProfileCreate(BaseModel):
    user_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth:Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture_url: Optional[str] = None


class UserProfileRead(BaseModel):
    first_name:str
    last_name: str
    date_of_birth: Optional[str] = None
    address: str
    phone_number: str
    profile_picture_url: str

class UserRead(BaseModel):
    user_did: str
    status: str
    primary_phone: Optional[str] = None
    email_verified: bool
    phone_verified: bool

    class config:
        from_attributes = True


class UserLoginToken(UserRead):
    token: str

    class config:
        from_attributes = True

class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth:Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture_url: Optional[str] = None
