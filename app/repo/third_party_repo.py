from fastapi import HTTPException, status
from typing import Optional
import re
from app.model.third_party import ThirdParty, ThirdPartyVerification, OrgStatus, ThirdPartyDataRequests
from app.schemas.third_party import ThirdPartyCreate, ThirdPartyDataRequestStorageCreate
import hashlib
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, update
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime
from app.model.user import UserDataVault
from app.dependecies.ai_model import AIOracleService
from app.dependecies.oracle_helper import format_oracle_response
import bcrypt
from asyncio import gather
from app.model.user import User, Notifications
from app.dependecies.user_encryption import hash_identifier
from app.security.user_token import get_user_Pii, decode_user_pii
from app.schemas.user import NotificationCreate, NotificationUpdate



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

    async def save_request_data(self, request_data: ThirdPartyDataRequestStorageCreate, org_name):
        if request_data:
            new_request_data = ThirdPartyDataRequests(**request_data.model_dump(exclude={"created_at", "updated_at", "ai_details"}))
            new_request_data.created_at = datetime.now()
            new_request_data.updated_at = datetime.now()

            stmt_b= select(ThirdParty).where(ThirdParty.organization_name == org_name)
            result_b = await self.session.exec(stmt_b)
            org = result_b.first()
            print("Org Status", org.status)

            if org.status != "approved":
                raise HTTPException(detail=f"Third Party Must Be Approved To Use This Service", status_code=500)

            ai_service = AIOracleService()
            ai_details =  await ai_service.translate_request_for_user(
                data_type=new_request_data.data_type,
                org_name=org_name,
                purpose=new_request_data.usage_description
                )
            new_request_data.ai_details = await format_oracle_response(ai_details)
            try:
                self.session.add(new_request_data)
                await self.session.commit()
                await self.session.refresh(new_request_data)
            except Exception as e:
                raise HTTPException(detail=f"Error saving request data. Full details: {e}", status_code=500)

            return new_request_data

    async def get_vic_request_repo(self, org_id: UUID, db: AsyncSession):
        if org_id:
            try:
                stmt = select(UserDataVault).where(UserDataVault.added_by == org_id)
                result = await db.exec(stmt)
                data = result.all()

                stmt_b= select(ThirdParty).where(ThirdParty.id == org_id)
                result_b = await db.exec(stmt_b)
                org = result_b.first()
                print("Org Status", org.status)

                if org.status != "approved":
                    raise HTTPException(detail=f"Third Party Must Be Approved To Use This Service", status_code=500)

                return data

            except Exception as e:
                raise HTTPException(detail=f"Error Getting Sent VIC. Full details: {e}", status_code=403)

    async def verify_email_repo(self, org_id: str) -> Optional[ThirdParty]:
        """Finds a third party by their organization name."""
        statement = select(ThirdParty).where(ThirdParty.id == org_id).options(selectinload(ThirdParty.verification_details))
        result = await self.session.exec(statement)
        data = result.first()
        if not data.email_verified:
            data.email_verified = True
            self.session.add(data)
            await self.session.commit()
            await self.session.refresh(data)
        return data

    async def update_org_pass(self, org_pass: str, org_id: UUID,  db: AsyncSession):
        if org_id and org_pass:
            try:
                stmt = select(ThirdParty).where(ThirdParty.id == org_id)
                result = await db.exec(stmt)
                org = result.first()
                org.password = bcrypt.hashpw(org_pass.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
                db.add(org)
                await db.commit()
                await db.refresh(org)

            except Exception as e:
                raise HTTPException(detail=f"Error Changing user password. Full details {e}", status_code=500)
            return org

    async def get_data_by_type(
        self,
        org_id: str,
        description: str,
        data_type: list[str],
        email: str,
        org_name,
        expire: int,
        ):
        data_store = []
        email_hash = await hash_identifier(email=email)
        stmt = select(User).where(User.email_index == email_hash).options(selectinload(User.data_vault_entries))
        stmt_b = select(ThirdParty).where(ThirdParty.id== org_id)

        async def run_statment(statement):
            result = await self.session.exec(statement)
            data = result.first()
            return data

        try:
            org, user_data = await gather(run_statment(stmt_b), run_statment(stmt))


            if org.status != "approved":

                raise HTTPException(detail=f"Third Part Needs To Be Approved To Use This Service", status_code=500)
            for p in user_data.data_vault_entries:
                if p.data_type in data_type:
                    data_store.append({"encrypted_data": p.encrypted_data, "Data Type": p.data_type})


            pii_data = await get_user_Pii(subject=str(org_id), data={"user_data":data_store, }, expire=expire)


            storage = ThirdPartyDataRequestStorageCreate(
                third_party_id=org_id,
                user_id=str(user_data.id),
                data_type=str(data_type),
                data_reference="Storing user data",
                usage_description=description,
                data_token=pii_data,
                data_consent_status="un_approved",
                data_rejection_reason="Null",
                duration = expire
            )


            await self.save_request_data(storage, org_name=org_name)

            return {"pii":pii_data, "user": user_data, "org": org}

        except Exception as e:
            raise HTTPException(detail=f"Error Getting user. Full details: {e}", status_code=500)


    async def decrypt_user_tk_data(token: str):
        try:
            encrypted_data = await  decode_user_pii(token=token)
            return encrypted_data
        except Exception as e:
            raise HTTPException(detail=f"Error Detokenizing Data. Full details: {e}", status_code=500)

    async def org_stats(self, org_id: str, db: AsyncSession):
        if org_id:

            """ Data Storage for Request Data"""
            total_request_data = 0
            rejected_request_data = 0
            approved_request_data = 0
            un_approved_request_data = 0

            """Data Storage for User Data"""
            total_added_data = 0
            rejected_added_data = 0
            approved_added_data = 0
            un_approved_added_data = 0

            stmt = select(ThirdPartyDataRequests).where(ThirdPartyDataRequests.third_party_id == org_id)
            stmt_b = select(UserDataVault).where(UserDataVault.added_by == org_id)

            async def run_query(stmts):
                result = await db.exec(stmts)
                payload = result.all()
                return payload

            try:
                user_data, request_data = await gather(run_query(stmt_b), run_query(stmt))
                print("Testing User Data", user_data)
                print("Testing Request Data", request_data)

                for data in user_data:
                    if data.status == "approved":
                        approved_added_data += 1
                    elif data.status == "un_approved":
                        un_approved_added_data += 1
                    else:
                        rejected_added_data += 1

                total_added_data = len(user_data)

                for request in request_data:
                    if request.data_consent_status == "approved":
                        approved_request_data += 1
                    elif request.data_consent_status == "un_approved":
                        un_approved_request_data += 1
                    else:
                        rejected_request_data += 1

                total_request_data = len(request_data)

                return {
                    "request_data_stats":
                    {
                        "total_request_data": total_request_data,
                        "approved_request_data": approved_request_data,
                        "rejected_request_data": rejected_request_data,
                        "un_approved_request_data": un_approved_request_data
                    },

                    "added_data_stats":
                    {
                        "total_added_data": total_added_data,
                        "approved_added_data": approved_added_data,
                        "rejected_added_data": rejected_added_data,
                        "un_approved_added_data": un_approved_added_data
                    }
                }

            except Exception as e:
                raise HTTPException(detail=f"Error Getting Organization Data. Full detais: {e}", status_code=500)


    async def create_org_notification(self, notification: NotificationCreate, db: AsyncSession):
        if notification:
            try:
                new_notification = Notifications(**notification.model_dump())
                db.add(new_notification)
                await db.commit()
                await db.refresh(new_notification)

            except Exception as e:
                raise HTTPException(detail=f"An Error occurred while creating notification. Full details: {e}", status_code=500)

            return new_notification

    async def update_or_read_notification_FAST(
        self,
        notification_updates: list[NotificationUpdate], db: AsyncSession
    ) -> list[Notifications]:

        if not notification_updates:
            return []

        try:
            notification_ids = [n.id for n in notification_updates]

            stmt_update = (
                update(Notifications)
                .where(Notifications.id.in_(notification_ids))
                .values(read=True)
                .execution_options(synchronize_session=False)
            )
            await db.exec(stmt_update)

            stmt_select = select(Notifications).where(Notifications.id.in_(notification_ids))
            payload = await db.exec(stmt_select)
            results = payload.all()

            await db.commit()

            return results

        except Exception as e:
            print(f"Transaction failed, rolling back. Error: {e}")
            await db.rollback()
            return []

    async def get_org_notification(self, user_id: UUID, db: AsyncSession):
        if user_id:
            try:
                stmt = select(Notifications).where(Notifications.user_id == user_id)
                payload = await db.exec(stmt)
                result = payload.all()
                if not result:
                    raise HTTPException(detail=f"User does not have any notification", status_code=404)
                return result
            except Exception as e:
                raise HTTPException(detail=f"Error occured while perfoming operation. full details: {e}", status_code=500)
