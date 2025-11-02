from sqlmodel import Session
from fastapi import HTTPException, status
from repo.third_party_repo import ThirdPartyRepo
from schemas.third_party import ThirdPartyCreate, ThirdPartyRegistrationResponse, ThirdPartyUpdate, ThirdPartyApiKeyResponse, ThirdPartyLogin, ThirdPartyTokenResponse
from model.third_party import ThirdParty, ThirdPartyVerification, OrgStatus
from bcrypt import hashpw, checkpw, gensalt
from dependecies.gen_api_key import generate_api_key
from datetime import datetime, timezone
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from security.user_token import get_access_token


class ThirdPartyService:
    """
    Service layer for business logic related to ThirdParty organizations.
    """

    def __init__(self, session: AsyncSession):
        self.repo = ThirdPartyRepo(session)

    async def register_new_organization(
        self,
        org_create_schema: ThirdPartyCreate
    ) -> ThirdPartyRegistrationResponse:
        """
        Orchestrates the registration of a new organization.
        """

        if await self.repo.get_by_email(org_create_schema.contact_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An organization with this email already exists."
            )

        if await self.repo.get_by_org_name(org_create_schema.organization_name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An organization with this name already exists."
            )

        hashed_password = hashpw(org_create_schema.password.encode("utf-8"), gensalt(rounds=12)).decode("utf-8")


        org_model_data = org_create_schema.model_dump(
            exclude={"password", "document_type", "document_reference", "document_storage_url"}
        )
        new_org = ThirdParty(
            **org_model_data,
            password=hashed_password,
            status=OrgStatus.UnApproved,
            api_key_hash= await generate_api_key()
        )

        verification_model_data = org_create_schema.model_dump(
            include={"document_type", "document_reference", "document_storage_url"}
        )
        new_verification = ThirdPartyVerification(
            **verification_model_data,
            verification_status="pending"
        )

        created_org = await self.repo.create_new_organization(new_org, new_verification)

        return ThirdPartyRegistrationResponse(
            public_org_id=created_org.public_org_id,
            organization_name=created_org.organization_name,
            status=created_org.status,
            api_key_hash=created_org.api_key_hash
        )

    async def get_all_thirdparties(self):
        try:
            third_parties = await self.repo.get_all()
        except Exception as e:
            raise HTTPException(detail=f"{e}", status_code=500)

        return third_parties

    async def update_organization_info(
        self,
        update_data: ThirdPartyUpdate
    ) -> ThirdParty:
        """Updates an organization's mutable info (e.g., contact)."""
        update_dict = update_data.model_dump(exclude_unset=True)
        org = await self.repo.get_by_org_id(update_data.org_id)

        # Check for email conflict if email is being changed
        if "contact_email" in update_dict and update_dict["contact_email"] != org.contact_email:
            if await self.repo.get_by_email(update_dict["contact_email"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An organization with this email already exists."
                )
        update_dict.pop("org_id", None)
        for key, value in update_dict.items():
            setattr(org, key, value)

        return await self.repo.save(org)


    async def approve_organization(self, org_id: UUID) -> ThirdPartyApiKeyResponse:
        """
        Admin action: Approves an organization and generates their first API key.
        """
        org = await self.repo.get_by_org_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found."
            )

        if org.status == OrgStatus.Approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization is already approved."
            )

        org.status = OrgStatus.Approved
        if org.verification_details:
            org.verification_details.verification_status = "approved"
            org.verification_details.verified_at = datetime.now(timezone.utc)

        third_party = await self.repo.save(org)

        return ThirdPartyApiKeyResponse(
            public_org_id=third_party.public_org_id,
            api_key=third_party.api_key_hash
        )
    async def delete_organization(self, org_id: UUID):
        """Deletes an organization and their verification data."""
        await self.repo.delete(org_id)
        return {"message": "Organization deleted successfully"}

    async def login_organization(
        self,
        login_data: ThirdPartyLogin
    ) -> ThirdPartyTokenResponse:
        """Handles organization login and issues a JWT."""
        org = await self.repo.get_by_email(login_data.username)

        if not org:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        if not checkpw(login_data.password.encode("utf-8"), org.password.encode("utf-8")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        if org.status != OrgStatus.Approved:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Organization account is not approved. Current status: {org.status}"
            )

        access_token = await get_access_token(
            str(org.id)
        )
        return ThirdPartyTokenResponse(
            token = access_token,
            public_org_id = org.public_org_id,
            contact_name = org.contact_name,
            organization_name = org.organization_name
        )
