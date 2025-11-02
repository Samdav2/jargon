from fastapi import HTTPException, status
from typing import Optional
import re
from model.third_party import ThirdParty, ThirdPartyVerification, OrgStatus
from schemas.third_party import ThirdPartyCreate
import hashlib
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from uuid import UUID

class ThirdPartyRepo:
    """
    Repository layer for all database operations related to ThirdParty.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _generate_public_org_id(self, org_name: str) -> str:
        """
        Creates a unique, URL-safe public ID from the organization name.
        Example: "Zenith Bank PLC" -> "org_zenith_bank_plc"
        """
        base_id = re.sub(r'[^a-z0-9]+', '_', org_name.lower()).strip('_')
        public_id = f"org_{base_id}"

        count = 0
        final_id = public_id
        while await self.get_by_public_id(final_id):
            count += 1
            final_id = f"{public_id}_{count}"

        return final_id

    async def get_by_email(self, email: str) -> Optional[ThirdParty]:
        """Finds a third party by their contact email."""

        statement = select(ThirdParty).where(ThirdParty.contact_email == email)
        result = await self.session.exec(statement)
        data = result.first()
        return data

    async def get_by_org_name(self, org_name: str) -> Optional[ThirdParty]:
        """Finds a third party by their organization name."""
        statement = select(ThirdParty).where(ThirdParty.organization_name == org_name)
        result = await self.session.exec(statement)
        data = result.first()
        return data

    async def get_by_public_id(self, public_id: str) -> Optional[ThirdParty]:
        """Finds a third party by their public_org_id."""

        statement = select(ThirdParty).where(ThirdParty.public_org_id == public_id)
        result = await self.session.exec(statement)
        data = result.first()
        return data

    async def create_new_organization(
        self,
        org_data: ThirdParty,
        verification_data: ThirdPartyVerification
    ) -> ThirdParty:
        """
        Saves a new ThirdParty and its ThirdPartyVerification record
        in a single transaction.
        """
        plain_key = org_data.api_key_hash
        try:
            org_data.public_org_id = await self._generate_public_org_id(org_data.organization_name)
            org_data.api_key_hash =  hashlib.sha256(plain_key.encode('utf-8')).hexdigest()

            self.session.add(org_data)
            verification_data.third_party_id = org_data.id
            self.session.add(verification_data)
            await self.session.commit()
            await self.session.refresh(org_data)
            org_data.api_key_hash = plain_key
            return org_data

        except Exception as e:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Error creating organization: {e}"
            )
    async def get_all(self):
        try:
            statement = select(ThirdParty)
            result = await self.session.exec(statement)
            third_party = result.first()
        except Exception as e:
            raise HTTPException(detail=f"Error Getting third parties. Full details: {e}", status_code=500)
        return third_party

    async def save(self, org: ThirdParty) -> ThirdParty:
        """Saves any changes to an organization object."""
        try:
            self.session.add(org)
            await self.session.commit()
            await self.session.refresh(org)
            return org
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving organization: {e}"
            )

    async def get_by_org_id(self, org_id: str) -> Optional[ThirdParty]:
        """Finds a third party by their organization name."""
        statement = select(ThirdParty).where(ThirdParty.id == org_id).options(selectinload(ThirdParty.verification_details))
        result = await self.session.exec(statement)
        data = result.first()
        return data

    async def delete(self, org_id: UUID):
        """Deletes an organization."""
        try:
            verification = await self.session.get(ThirdPartyVerification, org_id)

            statement = select(ThirdPartyVerification).where(ThirdPartyVerification.third_party_id == org_id)
            org = await self.get_by_org_id(org_id)
            result = await self.session.exec(statement)
            verification = result.first()

            if verification:
                await self.session.delete(verification)

            await self.session.delete(org)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting organization: {e}"
            )
