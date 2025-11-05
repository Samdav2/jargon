from sqlmodel import SQLModel, Field, Relationship, ForeignKey
from uuid import UUID, uuid4
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, DateTime, VARCHAR, Text, func, UniqueConstraint
from enum import Enum


class OrgStatus(str, Enum):
    Approved = "approved"
    UnApproved = "un_approved"
    Rejected = "rejected"
    Banned = "banned"
    InProgress = "in_progress"
    Suspended = "suspended"


class ThirdParty(SQLModel, table=True):
    """
    Model for Table 4: third_party
    This advanced table manages all organizations (banks, govt, firms)
    that want to access the SDE network.
    """
    __tablename__ = "third_party"

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True
    )

    public_org_id: str = Field(
        sa_column=Column(VARCHAR(255), nullable=False, unique=True, index=True)
    )

    organization_name: str = Field(
        nullable=False,
        index=True
    )

    password: str = Field(nullable=False)

    contact_name: str = Field(nullable=False)

    contact_email: str = Field(
        sa_column=Column(VARCHAR(255), nullable=False, unique=True)
    )

    email_verified: Optional[bool] = False


    api_key_hash: str = Field(
        sa_column=Column(Text, nullable=False)
    )

    status: OrgStatus = Field(
        default=OrgStatus.UnApproved,
        sa_column=Column(VARCHAR(50), nullable=False, index=True)
    )

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )

    consent_requests: List["ConsentLedger"] = Relationship(back_populates="consent_requests")
    verification_details: "ThirdPartyVerification" = Relationship(
        back_populates="organization",
        sa_relationship_kwargs={"uselist": False}
    )

    data_request_storage: List["ThirdPartyDataRequests"] = Relationship(
        back_populates="organization",
        sa_relationship_kwargs={"uselist": False}
    )


class ThirdPartyVerification(SQLModel, table=True):
    """
    Model for Table 5: third_party_verification
    This table stores the KYC/KYB (Know Your Business) details for an organization
    to verify them before they can be 'active' on the network.
    """
    __tablename__ = "third_party_verification"

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True
    )


    third_party_id: UUID = Field(
        sa_column=Column(ForeignKey("third_party.id"), nullable=False, unique=True)
    )

    document_type: str = Field(
        sa_column=Column(VARCHAR(100), nullable=False)
    )

    document_reference: str = Field(
        sa_column=Column(VARCHAR(255), nullable=False)
    )


    document_storage_url: Optional[str] = Field(
        default=None,
        sa_column=Column(Text)
    )

    verification_status: str = Field(
        default="pending",
        sa_column=Column(VARCHAR(50), nullable=False, index=True)
    )

    rejection_reason: Optional[str] = Field(
        default=None,
        sa_column=Column(Text)
    )

    verified_by_admin_id: Optional[UUID] = Field(default=None)

    verified_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    organization: "ThirdParty" = Relationship(
        back_populates="verification_details",
        sa_relationship_kwargs={"uselist": False}
    )


class ThirdPartyDataRequests(SQLModel, table=True):
    """
    Model for Table 5: third_party_verification
    This table stores the KYC/KYB (Know Your Business) details for an organization
    to verify them before they can be 'active' on the network.
    """
    __tablename__ = "third_party_data_requests"

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True
    )


    third_party_id: UUID = Field(
        sa_column=Column(ForeignKey("third_party.id"), nullable=False)
    )

    user_id: UUID = Field(
        sa_column=Column(ForeignKey("user.id"), nullable=False)
    )
    data_type: str = Field(
        sa_column=Column(VARCHAR(100), nullable=False)
    )

    ai_details: str = Field(sa_column=Column(Text, nullable=False))

    data_reference: str = Field(
        sa_column=Column(VARCHAR(255))
    )
    usage_description: str = Field(sa_column=Column(Text, nullable=False))


    data_token: Optional[str] = Field(
        default=None,
        sa_column=Column(Text)
    )

    data_consent_status: str = Field(
        default="pending",
        sa_column=Column(VARCHAR(50), nullable=False, index=True)
    )

    data_consent_rejection_reason: Optional[str] = Field(
        default=None,
        sa_column=Column(Text)
    )


    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    organization: "ThirdParty" = Relationship(
        back_populates="data_request_storage",
        sa_relationship_kwargs={"uselist": False}
    )

    user: "User" = Relationship(
        back_populates="data_request_storage"
    )
