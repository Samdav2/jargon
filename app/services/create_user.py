from app.dependecies.user_encryption import generate_sovereign_identity, encrypt_private_key, decrypt_private_key
from app.schemas.user import UserCreate, UserProfileCreate, UserLogin, UserRead, UserLoginToken, UserProfileUpdate, NotificationCreate, NotificationUpdate
from sqlmodel.ext.asyncio.session import AsyncSession
from app.repo.user_repo import save_user_to_db, save_user_profile_to_db, get_user_by_email, get_user_by_didx, get_user_by_did, update_user_pass, get_vic_request_repo, get_user_profile, update_user_profile, create_user_notification, update_or_read_notification_FAST, get_user_notification
from app.dependecies.encrypt_user_data import decrypt_pw_key, decrypt_data_with_private_key, encrypt_pw_key
from fastapi import HTTPException, BackgroundTasks
from app.security.user_token import get_access_token, get_user_Pii, decode_user_pii
import bcrypt
from app.dependecies.email import EmailService
from dotenv import load_dotenv
from uuid import UUID
import os
from app.model.third_party import ThirdPartyDataRequests
from sqlmodel import select
from app.dependecies.user_encryption import decrypt_private_key as decrypt_private_key_x
from app.model.user import User
from app.dependecies.user_encryption import hash_identifier
from app.dependecies.encrypt_user_data import decrypt_private_key as decrypt_private_key_y
from app.schemas.data_vault import Decision
from app.repo.user_repo import approve_reject as aj
from sqlalchemy.orm import selectinload





load_dotenv()

URL = os.getenv("DOMAIN")
TOKEN = os.getenv("VOID_EMAIL")
NAME_TOKEN = os.getenv("VOID_NAME")
TOKEN_P = os.getenv("VOID_PW")


class CreateUserService:
    @staticmethod
    async def execute(user: UserCreate, background_task: BackgroundTasks, db: AsyncSession):
        if await get_user_by_email(user.email.lower(), db=db):
            raise HTTPException(detail="Account already exist on this email, pls use another email or reset pass", status_code=403)
        did = await generate_sovereign_identity()
        private_key = await encrypt_private_key(private_key_hex=did["private_key_hex"], user=user)
        user.email = user.email.lower()
        db_user = await save_user_to_db(user, did["did"], private_key, db)
        send_email = EmailService()
        send_email.send_user_welcome_email(background_tasks=background_task, email_to=user.email, name=user.name)
        await CreateUserService.send_email_verication(user_did=did["did"], email=user.email, name=user.name, background_task=background_task)

        return db_user

    async def decrypt_user_pass(private_key_hex, password):

        user_pass = await decrypt_pw_key(password, token=TOKEN_P)
        encrypted = await decrypt_private_key_y(private_key_hex)
        result = await decrypt_private_key(encrypted_data_json=encrypted, password=user_pass)
        return result

    async def create_user_profile(profile: UserProfileCreate, db: AsyncSession) -> UserRead:
        profile = await save_user_profile_to_db(profile, db)
        return profile

    async def user_login(user_details: UserLogin, db: AsyncSession):
        try:
            user = await get_user_by_email(user_details.username.lower(), db=db)
            if user:
                print("user_sample", user)
                if not bcrypt.checkpw(user_details.password.encode("utf-8"), user.login_password.encode("utf-8")):
                    raise HTTPException(detail=f"Incorrect User Pasword", status_code=401)
            else:
                raise HTTPException(detail=f"Incorrect email, User not found.", status_code=404)
        except Exception as e:
            raise HTTPException(detail=f"An error occured during user login. Full details: {e}", status_code=500)
        token = await get_access_token(str(user.id))

        refined_user = UserRead.model_validate(user.model_dump())
        return UserLoginToken(**refined_user.model_dump(), token=token
        )

    async def send_email_verication(user_did, email, name, background_task: BackgroundTasks):
        user_token = await get_user_Pii(subject=user_did, expire=60)
        print("User_Token", user_token)
        verifcation_link = f"{URL}/verify_email?token={user_token}"
        email_service = EmailService
        email_service.send_email_verification(email_to=email, name=name, verification_link=verifcation_link, background_tasks=background_task)

    async def verify_email(token: str, background_task: BackgroundTasks, db: AsyncSession):
        did_obj= await decode_user_pii(token = token)
        did = did_obj["sub"]
        user = await get_user_by_didx(did = did, db=db)
        email_service = EmailService()
        email = await decrypt_pw_key(encrypted_data_json=user.email, token=TOKEN)
        name = await decrypt_pw_key(encrypted_data_json=user.name, token=NAME_TOKEN)
        email_service.send_email_verified_notice(background_tasks=background_task, email_to=email, name=name)
        return True

    async def send_email_verication_x(user_did, background_task: BackgroundTasks, db: AsyncSession):
        user_token = await get_user_Pii(subject=user_did, expire=60)
        user = await get_user_by_did(did = user_did, db=db)
        email = await decrypt_pw_key(encrypted_data_json=user.email, token=TOKEN)
        name = await decrypt_pw_key(encrypted_data_json=user.name, token=NAME_TOKEN)
        print("User_Token", user_token)
        verifcation_link = f"{URL}/verify_email?token={user_token}"
        email_service = EmailService
        email_service.send_email_verification(email_to=email, name=name, verification_link=verifcation_link, background_tasks=background_task)
        return True

    async def change_pass_service(user_pass: str, token: str, background_task: BackgroundTasks, db: AsyncSession):
        user = await decode_user_pii(token=token)
        user_id = user["sub"]
        if user_pass and user_id:
            try:
                user = await update_user_pass(user_pass=user_pass, user_id=user_id, db=db)
                email_service = EmailService()
                email = await decrypt_pw_key(encrypted_data_json=user.email, token=TOKEN)
                name = await decrypt_pw_key(encrypted_data_json=user.name, token=NAME_TOKEN)
                email_service.send_password_change_notice(background_tasks=background_task, email_to=email, name=name)
            except Exception as e:
                raise HTTPException(detail=f"{e}", status_code=500)

            return {"message":"Password changed successfully"}


    async def send_email_pass_email(user, background_task: BackgroundTasks):
        email_service = EmailService()
        user_token = await get_user_Pii(subject=str(user.id), expire=15)
        reset_link = f"{URL}/change_pass?token={user_token}"
        email = await decrypt_pw_key(encrypted_data_json=user.email, token=TOKEN)
        name = await decrypt_pw_key(encrypted_data_json=user.name, token=NAME_TOKEN)
        email_service.send_password_reset_email(background_tasks=background_task, email_to=email, reset_link=reset_link, name=name)


    async def get_user_by_email_service(email:str, db: AsyncSession):
        try:
            user = await get_user_by_email(email.lower(), db=db)

        except Exception as e:
            raise HTTPException(detail=f"{e}", status_code=404)

        return user

    async def get_vic_request(user_id: UUID, db: AsyncSession):
        if user_id:
            try:
                request = await get_vic_request_repo(user_id, db)
            except Exception as e:
                raise HTTPException(detail=f"{e}", status_code=403)
            return request


    async def get_thirdparty_data_request(email: str, db: AsyncSession):
        data_list = []
        decrypt_email = await decrypt_pw_key(encrypted_data_json=email, token=TOKEN)

        hash_email = await hash_identifier(decrypt_email)

        user_stmt = select(User).where(User.email_index == hash_email)
        user_result = await db.exec(user_stmt)
        payload = user_result.first()

        if not payload:
            raise HTTPException(status_code=404, detail="User not found")

        data_stmt = select(ThirdPartyDataRequests).where(
            ThirdPartyDataRequests.user_id == payload.id
        ).options(selectinload(ThirdPartyDataRequests.organization))
        data_result = await db.exec(data_stmt)
        user_data_requests = data_result.all()

        if not user_data_requests:
            return []

        user_pass = payload.password
        raw_xxx_kkk = payload.xxx_kkk

        try:
            pwx = await decrypt_pw_key(user_pass, token=TOKEN_P)
            decrypt_xxx_kkk = await decrypt_private_key_y(raw_xxx_kkk)
            token = await decrypt_private_key_x(decrypt_xxx_kkk, pwx)
            print("Decryp KK", decrypt_xxx_kkk)
            print("token", token)

        except Exception as e:
            raise HTTPException(detail=f"An error occurred during key decryption. Full details {e}", status_code=500)
        else:
            try:

                for d in user_data_requests:
                    try:
                        detokenized_pii = await decode_user_pii(d.data_token)
                    except Exception:
                        continue

                    if "user_data" not in detokenized_pii:
                        continue

                    for item in detokenized_pii["user_data"]:
                        encrypted_data = item["encrypted_data"]
                        data_type = item["Data Type"]

                        decrypted_data_point = await decrypt_data_with_private_key(
                            encrypted_jargon=encrypted_data,
                            private_key_hex=token
                        )
                        idx = await encrypt_pw_key(str(d.id), token=TOKEN_P)

                        data_list.append({
                            "Data Type": data_type,
                            "Data": decrypted_data_point,
                            "idx": idx,
                            "Created At": d.created_at,
                            "Updated At": d.updated_at,
                            "Requested By": d.organization.organization_name,
                            "status": d.data_consent_status,
                            "Duration": d.duration
                        })

                        break

            except Exception as e:
                raise HTTPException(detail=f"Error Decrypting User Data. Full details: {e}", status_code=500)

            return data_list

    async def approve_reject(data_id: str, response: Decision, db: AsyncSession, background_task: BackgroundTasks):
        if data_id:
            try:
                idx = await decrypt_pw_key(data_id, TOKEN_P )
                print("Data Id", idx)
                data = await aj(data_id=idx, response=response, db=db)
                org = data["org"]
                user = data["user"]
                content = data["data"]
                data_idx = await encrypt_pw_key(str(content.id), token=TOKEN_P)

                email_service = EmailService()
                if response == "approve":
                    email_service.send_org_consent_approved_email(
                        background_tasks=background_task,
                        email_to=org.contact_email,
                        org_name=org.organization_name,
                        user_did =user.user_did,
                        consent_id= data_idx,
                        )
                else:
                    email_service.send_org_consent_revoked_email(
                        background_tasks=background_task,
                        email_to=org.contact_email,
                        org_name=org.organization_name,
                        user_did =user.user_did,
                        consent_id= data_idx,
                    )


            except Exception as e:
                raise HTTPException(f"{e}")
            return data["data"]

    async def get_user_profile_service(user_id: str, db: AsyncSession):
        if user_id:
            user_profile = await get_user_profile(user_id=user_id, db=db)
            return user_profile

    async def update_user_profile_service(profile_update: UserProfileUpdate, user_id: str, db: AsyncSession):
        if user_id:
            user_profile_udate = await update_user_profile(profile_update=profile_update, user_id=user_id, db=db)
            return user_profile_udate

    async def create_notification_service(notification: NotificationCreate, db: AsyncSession):
        if notification:
            result = await create_user_notification(notification=notification, db=db)
            return result

    async def update_or_read_notification_service(notification: NotificationUpdate, db: AsyncSession):
        if notification:
            result = await update_or_read_notification_FAST(notification_updates=notification, db=db)
            return result

    async def get_user_notfication_service(user_id: UUID, db: AsyncSession):
        if user_id:
            result = await get_user_notification(user_id=user_id, db=db)
            return result
