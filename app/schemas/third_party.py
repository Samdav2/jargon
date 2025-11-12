from pydantic import BaseModel, EmailStr, Field, HttpUrl
from uuid import UUID
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from uuid import UUID
from datetime import datetime
from enum import Enum
from typing import Optional


class VerificationDocumentType(str, Enum):
    """Enum for allowed verification document types."""
    CAC = "CAC_REGISTRATION"
    GOVT_LICENSE = "GOVERNMENT_LICENSE"
    TAX_ID = "TAX_IDENTIFICATION_NUMBER"
    OTHER = "OTHER"

class OrganizationStatus(str, Enum):
    """Enum for the organization's lifecycle status."""
    APPROVED = "approved"
    UN_APPROVED = "un_approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    IN_PROGRESS = "in_progress"
    BANNED = "banned"


class ThirdPartyCreate(BaseModel):
    """
    Schema used to register a new Third-Party organization.
    This single schema provides data for both ThirdParty and ThirdPartyVerification tables.
    """

    organization_name: str = Field(
        ...,
        min_length=3,
        max_length=255,
        examples=["Zenith Bank PLC"]
    )
    contact_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        examples=["Adewale Chukwunonso"]
    )
    contact_email: EmailStr = Field(
        ...,
        examples=["contact@zenithbank.com"]
    )

    document_type: VerificationDocumentType = Field(
        ...,
        examples=[VerificationDocumentType.CAC]
    )
    document_reference: str = Field(
        ...,
        min_length=5,
        max_length=255,
        examples=["RC123456"]
    )
    document_storage_url: Optional[str] = Field(
        default=None,
        examples=["https.../sde_admin_vault/cac_doc.pdf"],
        description="Optional: A secure URL to a pre-uploaded verification document."
    )

    # --- Field for the API Key ---
    # The organization *provides* a secure password.
    # Our service layer will HASH this and store it in 'api_key_hash'.
    # This password will be used for their *initial* auth.
    password: str = Field(
        ...,
        min_length=12,
        description="A secure password for the organization's account. This will be hashed."
    )



class ThirdPartyVerificationRead(BaseModel):
    """Pydantic schema for safely reading verification details."""
    document_type: VerificationDocumentType
    document_reference: str
    api_key: str
    document_storage_url: Optional[str] = None
    verification_status: str
    rejection_reason: Optional[str] = None
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ThirdPartyRead(BaseModel):
    """
    Pydantic schema for safely reading public Third-Party data.
    Notice 'api_key_hash' is NOT included.
    """
    id: UUID
    public_org_id: str
    organization_name: str
    contact_name: str
    contact_email: EmailStr
    status: OrganizationStatus
    created_at: datetime
    api_key_hash: str

    class Config:
        from_attributes = True

class ThirdPartyReadWithVerification(ThirdPartyRead):
    """
Signature<'...'read: A-to-one relationship."""
    verification_details: Optional[ThirdPartyVerificationRead] = None



class ThirdPartyRegistrationResponse(BaseModel):
    """
    The response sent back to the organization after they register.
    """
    public_org_id: str
    organization_name: str
    status: OrganizationStatus
    api_key_hash: str
    message: str = "Registration successful. Your application is pending review."


class ThirdPartyApiKeyResponse(BaseModel):
    """
    The response sent ONE TIME when an admin approves an organization
    and a new API key is generated.
    """
    public_org_id: str
    api_key: Optional[str] = Field(..., examples=["sde_live_sk_..."])
    message: str = "API Key generated. This is the only time you will see this key."


class ThirdPartyUpdate(BaseModel):
    """Schema for an organization to update its own info."""
    contact_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255
    )
    contact_email: Optional[EmailStr] = Field(
        default=None
    )
    organization_name: str
    public_org_id: str
    org_id: Optional[str] = None

class ThirdPartyTokenResponse(BaseModel):
    """
    A token is sent along sidde with other org details
    """
    public_org_id: str
    organization_name: str
    contact_name: str
    token: Optional[str] = Field(..., examples=["ebooouyy8hhh_..."])
    message: str = "Login Successful"


class ThirdPartyLogin(BaseModel):
    """Schema for an thirdpary login."""
    username: str
    password: str

    class Config:
        from_attributes = True

class ThirdPartyDataRequestStorageCreate(BaseModel):
    """
    Pydantic schema for safely creating public Third-Party data request storage.
    """
    third_party_id: str
    user_id: str
    data_type: str
    ai_details: Optional[str] = None
    data_reference: str
    usage_description: str
    data_token: str
    data_consent_status: OrganizationStatus
    data_rejection_reason: str

    class Config:
        from_attributes = True

class ThirdPartytDataVault(BaseModel):
    user_id: str
    data_type: str
    added_by: Optional[UUID] = None
    org_name: Optional[str] = None
    status: Optional[OrganizationStatus] = OrganizationStatus.UN_APPROVED
    encrypted_data: str
    data_hash: Optional[str] = None

    class config:
        from_attributes = True

class ThirdPartyUpdateRead(BaseModel):
    """
    Pydantic schema for safely reading public Third-Party data.
    Notice 'api_key_hash' is NOT included.
    """
    public_org_id: str
    organization_name: str
    contact_name: str
    contact_email: EmailStr
    status: OrganizationStatus
    created_at: datetime

    class Config:
        from_attributes = True
