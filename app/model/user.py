from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import Column, DateTime, Text, VARCHAR
from sqlalchemy.sql import func

# --- Best Practice for Timestamps ---
# We use `server_default=func.now()` to let the PostgreSQL database
# set the creation time.
# We use `onupdate=func.now()` to let the database automatically
# update the timestamp whenever the row is changed.
# The `default_factory=datetime.utcnow` is a fallback for the Python model.
# The `DateTime(timezone=True)` ensures the DB stores it with timezone info.

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
    name: str = Field(unique=False, index=True)
    email: str = Field(unique=True, index=True, nullable=False)
    email_index: str = Field(unique=True, index=True, nullable=False)
    password: str = Field(nullable=False)
    login_password: str = Field(nullable=False)
    user_did: str = Field(index=True, nullable=False)
    status: str = Field(
        default="active",
        sa_column=Column(VARCHAR(50), nullable=False)
    )

    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    xxx_kkk: str = Field(nullable=False)
    profile: Optional["UserProfile"] = Relationship(back_populates="user")
    data_vault_entries: List["UserDataVault"] = Relationship(back_populates="user")


class UserDataVault(SQLModel, table=True):
    """
    Model for Table 2: user_data_vault
    This table stores all of the user's personal encrypted data "blobs".
    """
    __tablename__ = "user_data_vault"

    __table_args__ = (
        UniqueConstraint("user_id", "data_type", name="uq_user_id_data_type"),
    )

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True
    )

    user_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)

    data_type: str = Field(nullable=False)

    encrypted_data: str = Field(sa_column=Column(Text, nullable=False))

    data_hash: Optional[str] = Field(default=None)

    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    )

    user: Optional[User] = Relationship(back_populates="data_vault_entries")


class ConsentLedger(SQLModel, table=True):
    """
    Model for Table 3: consent_ledger
    This is the database-driven "audit trail" of all consent actions.
    """
    __tablename__ = "consent_ledger"

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True
    )

    user_did: UUID = Field(nullable=False, index=True)

    third_party_id: UUID = Field(foreign_key="third_party.id", nullable=False, index=True)

    vault_data_id: Optional[UUID] = Field(
        default=None,
        foreign_key="user_data_vault.id"
    )

    data_type_requested: str = Field(
        sa_column=Column(VARCHAR(100), nullable=False)
    )

    purpose: str = Field(sa_column=Column(Text, nullable=False))

    status: str = Field(nullable=False, index=True)

    granted_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )

    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    transaction_signature: Optional[str] = Field(
        default=None,
        sa_column=Column(Text)
    )

    consent_requests: "ThirdParty" = Relationship(back_populates="consent_requests")



class UserProfile(SQLModel, table=True):
    """
    Model for Table 4: user_profile
    """
    __tablename__ = "user_profile"

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True
    )

    user_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)

    first_name: Optional[str] = Field(default=None)

    last_name: Optional[str] = Field(default=None)

    date_of_birth: Optional[str] = Field(default=None)

    address: Optional[str] = Field(default=None)

    phone_number: Optional[str] = Field(default=None)

    profile_picture_url: Optional[str] = Field(default=None)

    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    )

    user : Optional[User] = Relationship(back_populates="profile")
