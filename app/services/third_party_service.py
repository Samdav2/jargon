from sqlmodel import Session
from fastapi import HTTPException, status, BackgroundTasks
from app.repo.third_party_repo import ThirdPartyRepo
from app.schemas.third_party import ThirdPartyCreate, ThirdPartyRegistrationResponse, ThirdPartyUpdate, ThirdPartyApiKeyResponse, ThirdPartyLogin, ThirdPartyTokenResponse, ThirdPartytDataVault, ThirdPartytDataVaultEmail
from app.model.third_party import ThirdParty, ThirdPartyVerification, OrgStatus
from bcrypt import hashpw, checkpw, gensalt
from app.dependecies.gen_api_key import generate_api_key
from datetime import datetime, timezone
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from app.security.user_token import get_access_token
from app.repo.data_vault_repo import get_data_by_type, save_user_data_to_db
from app.model.user import User
from app.dependecies.user_encryption import hash_identifier
from sqlmodel import select
from sqlalchemy.orm import selectinload
from app.model.third_party import ThirdPartyDataRequests
import os
from dotenv import load_dotenv
from app.dependecies.encrypt_user_data import decrypt_pw_key, decrypt_private_key, decrypt_data_with_private_key
from app.security.user_token import decode_user_pii, get_user_Pii
from app.dependecies.user_encryption import decrypt_private_key as decrypt_private_key_x
from app.services.data_vault import save_user_data_vault
from app.dependecies.email import EmailService
from app.dependecies.ai_model import AIOracleService
from app.dependecies.oracle_helper import format_oracle_response
from app.repo.user_repo import get_user_by_did, get_user_by_email
from app.schemas.user import NotificationCreate, NotificationUpdate


load_dotenv

TOKEN = os.getenv("VOID_PW")
URL = os.getenv("DOMAIN")
NAME_TOKEN = os.getenv("VOID_NAME")


class ThirdPartyService:
    """
    Service layer for business logic related to ThirdParty organizations.
    """

    def __init__(self, session: AsyncSession):
        self.repo = ThirdPartyRepo(session)

    async def register_new_organization(
        self,
        org_create_schema: ThirdPartyCreate,
        background_task: BackgroundTasks
    ) -> ThirdPartyRegistrationResponse:
        """
        Orchestrates the registration of a new organization.
        """

        org_create_schema.contact_name = org_create_schema.contact_email.lower()
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
        email_service = EmailService()
        email_service.send_org_welcome_email(
            background_tasks=background_task,
            email_to=created_org.contact_email,
            org_name=created_org.organization_name,
            public_org_id=created_org.public_org_id,
            api_key=new_org.api_key_hash
            )

        token = await get_user_Pii(str(created_org.id), expire=60)
        verifcation_link = f"{URL}/verify_email?token={token}"

        email_service.send_email_verification(
            background_tasks=background_task,
            email_to=created_org.contact_email,
            name=created_org.contact_name,
            verification_link=verifcation_link
            )

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

        login_data.username = login_data.username.lower()
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

        access_token = await get_access_token(
            str(org.id)
        )
        return ThirdPartyTokenResponse(
            token = access_token,
            public_org_id = org.public_org_id,
            contact_name = org.contact_name,
            organization_name = org.organization_name
        )

    async def get_data_by_type_service(self, org_id: str, description: str, email: str, expire: int, data_type: list[str], org_name, background_task: BackgroundTasks, db: AsyncSession):
        try:
            data_store = await self.repo.get_data_by_type(org_id=org_id, description=description, expire = expire, email=email, data_type=data_type, org_name=org_name)
            user = data_store["user"]
            org = data_store["org"]
            name = await decrypt_pw_key(encrypted_data_json=user.name, token=NAME_TOKEN)

            ai_service = AIOracleService()
            try:
                ai_description = await  ai_service.translate_request_for_user(purpose=description, data_type=str(data_type), org_name=org.organization_name)
            except Exception:
                ai_description  = "AI service is Unavalable at the moment"


            ai_refined = await format_oracle_response(ai_description)


            email_service = EmailService()
            email_service.send_new_consent_request_email(
                background_tasks=background_task,
                email_to=email,
                user_name=name,
                plain_language_purpose=ai_refined,
                org_name=org.organization_name
                )

            new_notification = NotificationCreate(
                user_id=user.id,
                content=f"Hello {name}, {org.organization_name} is requesting to make use of this service: {data_type}. Pls respond to it fast",
                read=False
            )

            await self.create_notification_service(notification=new_notification, db=db)

            return data_store["pii"]
        except Exception as e:
            raise HTTPException(detail=f"{e}", status_code=500)


    async def decrypt_data_request(self, email: str, org_id: str, db: AsyncSession):
        data_list = []
        decrypted_data_point = None
        hash_email = await hash_identifier(email)

        user_stmt = select(User).where(User.email_index == hash_email)
        user_result = await db.exec(user_stmt)
        payload = user_result.first()

        if not payload:
            raise HTTPException(status_code=404, detail="User not found")

        data_stmt = select(ThirdPartyDataRequests).where(
            ThirdPartyDataRequests.user_id == payload.id,
            ThirdPartyDataRequests.third_party_id == org_id
        )
        data_result = await db.exec(data_stmt)
        user_data_requests = data_result.all()
        if not user_data_requests:
            return []

        user_pass = payload.password
        raw_xxx_kkk = payload.xxx_kkk

        try:
            pwx = await decrypt_pw_key(user_pass, token=TOKEN)
            decrypt_xxx_kkk = await decrypt_private_key(raw_xxx_kkk)
            token = await decrypt_private_key_x(decrypt_xxx_kkk, pwx)
            print("Decryp KK", decrypt_xxx_kkk)
            print("token", token)

        except Exception as e:
            raise HTTPException(detail=f"An error occurred during key decryption. Full details {e}", status_code=500)
        else:
            try:
                for d in user_data_requests:


                    decrypted_data_point = None
                    data_type = "Unknown"  # Default in case of error

                    try:
                        detokenized_pii = await decode_user_pii(d.data_token)
                    except Exception:
                        continue

                    if "user_data" not in detokenized_pii or not detokenized_pii["user_data"]:
                        continue

                    for item in detokenized_pii["user_data"]:
                        data_type = item.get("Data Type", "Unknown")
                        encrypted_data = item.get("encrypted_data")


                        if d.data_consent_status == "approve":
                            if not encrypted_data:
                                decrypted_data_point = "Payload missing 'encrypted_data' field"
                            else:
                                try:
                                    decrypted_data_point = await decrypt_data_with_private_key(
                                        encrypted_jargon=encrypted_data,
                                        private_key_hex=token
                                    )
                                except Exception as e:
                                    decrypted_data_point = f"Decryption Failed: {e}"
                        else:
                            decrypted_data_point = "User Consent Not Approved. Data is unavailable"

                        data_list.append({
                            "Data Type": data_type,
                            "Data": decrypted_data_point,
                            "Created At": d.created_at,
                            "Updated At": d.updated_at,
                        })

            except Exception as e:
                raise HTTPException(detail=f"Error Decrypting User Data. Full details: {e}", status_code=500)

            return data_list


    async def adding_user_vic(self, data_vic: ThirdPartytDataVaultEmail, db: AsyncSession):
        if data_vic:
            try:
                user_id = await get_user_by_email(email=data_vic.email, db=db)
                data_vic.user_id = str(user_id.id)
                user_data = await save_user_data_vault(data_vic, db=db)

            except Exception as e:
                raise HTTPException(detail=f"{e}", status_code=500)
            return user_data

    async def get_vic_request(self, org_id: UUID, db: AsyncSession):
        if org_id:
            try:
                request = await self.repo.get_vic_request_repo(org_id, db)
            except Exception as e:
                raise HTTPException(detail=f"{e}", status_code=403)
            return request

    async def verify_email_service(self, token: str, background_task: BackgroundTasks, db: AsyncSession):
        did_obj= await decode_user_pii(token = token)
        ord_id = did_obj["sub"]
        org = await self.repo.verify_email_repo(ord_id)
        email_service = EmailService()
        email_service.send_email_verified_notice(background_tasks=background_task, email_to=org.contact_email, name=org.contact_name)
        return True

    async def send_email_verication_x(self, org_id, background_task: BackgroundTasks, db: AsyncSession):
        token = await get_user_Pii(subject=str(org_id), expire=60)
        org = await self.repo.get_by_org_id(org_id)
        print("User_Token", token)
        verifcation_link = f"{URL}/verify-email?token={token}"
        email_service = EmailService
        email_service.send_email_verification(email_to=org.contact_email, name=org.contact_name, verification_link=verifcation_link, background_tasks=background_task)
        return True

    async def change_pass_service(self, org_pass: str, token: str, db: AsyncSession, background_task: BackgroundTasks):
        org = await decode_user_pii(token=token)
        org_id = org["sub"]
        if org_pass and org_id:
            try:
                org = await self.repo.update_org_pass(org_pass=org_pass, org_id=org_id, db=db)
                email_service = EmailService()
                email_service.send_password_change_notice(
                    background_tasks=background_task,
                    email_to=org.contact_email,
                    name=org.contact_name
                    )
            except Exception as e:
                raise HTTPException(detail=f"{e}", status_code=500)

            return {"message":"Password changed successfully"}


    async def send_email_pass_email(self, org, background_task: BackgroundTasks):
        email_service = EmailService()
        token = await get_user_Pii(subject=str(org.id), expire=15)
        reset_link = f"{URL}/org/change-password?token={token}"
        email_service.send_password_reset_email(background_tasks=background_task, email_to=org.contact_email, reset_link=reset_link, name=org.contact_name)


    async def get_org_by_email_service(self, email:str, db: AsyncSession):
        try:
            org = await self.repo.get_by_email(email.lower())

        except Exception as e:
            raise HTTPException(detail=f"{e}", status_code=404)

        return org

    async def detonize_user_data_service(self, token: str):
        if token:
            try:
                detokenized_data = await decode_user_pii(token)
                return detokenized_data["user_data"][0]["encrypted_data"]
            except Exception as e:
                raise HTTPException(detail=f"Error Perfoming detoneization.  Full details: {e}", status_code=500)

    async def get_organization_stats(self, org_id: str, db: AsyncSession):
        if org_id:
                stats = await self.repo.org_stats(org_id=org_id, db=db)
                return stats

    async def create_notification_service(self, notification: NotificationCreate, db: AsyncSession):
        if notification:
            result = await self.repo.create_org_notification(notification=notification, db=db)
            return result

    async def update_or_read_notification_service(self, notification: NotificationUpdate, db: AsyncSession):
        if notification:
            result = await self.repo.update_or_read_notification_FAST(notification_updates=notification, db=db)
            return result

    async def get_user_notfication_service(self, user_id: UUID, db: AsyncSession):
        if user_id:
            result = await self.repo.get_org_notification(user_id=user_id, db=db)
