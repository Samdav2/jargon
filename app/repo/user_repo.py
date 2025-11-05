from model.user import User, UserProfile
from sqlmodel import select
from uuid import uuid4
from app.schemas.user import UserCreate, UserProfileCreate, UserRead
from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from passlib.hash import bcrypt
import bcrypt
from app.dependecies.encrypt_user_data import encrypt_private_key, encrypt_pw_key
from app.dependecies.user_encryption import hash_identifier
import os
from dotenv import load_dotenv
from uuid import UUID
from app.model.user import UserDataVault
from sqlalchemy.orm import selectinload
from app.model.third_party import ThirdParty, ThirdPartyDataRequests
from app.schemas.data_vault import Decision

load_dotenv()

TOKEN = os.getenv("VOID_PW")
N_TOKEN = os.getenv("VOID_NAME")
E_TOKEN = os.getenv("VOID_EMAIL")
PASS_PASS=os.getenv("PASS_PASS")

async def save_user_to_db(user_create, did, xxx_kkk, db):
    user = User(
        id = uuid4(),
        name= await encrypt_pw_key(private_key_hex=user_create.name, token=N_TOKEN),
        email= await encrypt_pw_key(user_create.email, token=E_TOKEN),
        email_index = await hash_identifier(user_create.email),
        did=did,
        password = await encrypt_pw_key(private_key_hex=user_create.password, token=TOKEN),
        login_password= bcrypt.hashpw(user_create.password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8"),
        user_did = did,
        xxx_kkk= await encrypt_private_key(xxx_kkk),
        primary_phone=user_create.primary_phone
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def save_user_profile_to_db(profile_create: UserProfileCreate, db: AsyncSession):
    try:
        profile = UserProfile(**profile_create.model_dump())
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving user profile to database {str(e)}")
    return profile

async def get_user(user_id, db: AsyncSession):
    try:
        stm = select(User).where(User.id == user_id)
        result = await db.exec(stm)
        user = result.first()

    except Exception as e :
        raise HTTPException(detail=f"Error while selecting user. Real resaon{e}", status_code=500)
    return user

async def get_user_by_email(email: str, db: AsyncSession) -> UserRead:
    email_hash = await hash_identifier(email)
    print("Email_hash", email_hash)
    try:
        stmt = select(User).where(User.email_index == email_hash)
        result = await db.exec(stmt)
        user = result.first()
        print("User Sample", user)

    except Exception as e:
        raise HTTPException(detail=f"Error Getting User. Full Details: {e}", status_code=404)
    return user

async def get_user_by_didx(did: str, db: AsyncSession) -> UserRead:

    try:
        stmt = select(User).where(User.user_did == did)
        result = await db.exec(stmt)
        user = result.first()
        if not user.email_verified:
            user.email_verified = True
            db.add(user)
            await db.commit()
            await db.refresh(user)
        print("User Sample", user)

    except Exception as e:
        raise HTTPException(detail=f"Error Getting User. Full Details: {e}", status_code=404)
    return user

async def get_user_by_did(did: str, db: AsyncSession) -> UserRead:

    try:
        stmt = select(User).where(User.user_did == did)
        result = await db.exec(stmt)
        user = result.first()
        print("User Sample", user)

    except Exception as e:
        raise HTTPException(detail=f"Error Getting User. Full Details: {e}", status_code=404)
    return user

async def update_user_pass(user_pass: str, user_id: UUID,  db: AsyncSession):
    if user_id and user_pass:
        try:
            stmt = select(User).where(User.id == user_id)
            result = await db.exec(stmt)
            user = result.first()
            user.login_password = bcrypt.hashpw(user_pass.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
            db.add(user)
            await db.commit()
            await db.refresh(user)

        except Exception as e:
            raise HTTPException(detail=f"Error Changing user password. Full details {e}", status_code=500)
        return user

async def get_vic_request_repo(user_id: UUID, db: AsyncSession):
        if user_id:
            try:
                stmt = select(UserDataVault).where(UserDataVault.user_id == user_id).where(UserDataVault.added_by != None)
                result = await db.exec(stmt)
                data = result.all()
                return data

            except Exception as e:
                raise HTTPException(detail=f"Error Getting Sent VIC. Full details: {e}", status_code=403)


async def approve_reject(data_id: str, response: Decision, db: AsyncSession):
    if data_id:
        try:
            stmt = select(ThirdPartyDataRequests).where(ThirdPartyDataRequests.id == data_id).options(selectinload(ThirdPartyDataRequests.user))
            result = await db.exec(stmt)
            data = result.first()
            user = data.user

            if data.third_party_id:
                stmt_b = select(ThirdParty).where(ThirdParty.id == data.third_party_id)
                result_b = await db.exec(stmt_b)
                org = result_b.first()


            data.data_consent_status = response
            db.add(data)
            await db.commit()
            await db.refresh(data)

        except Exception as e:
            raise HTTPException(detail=f"Error Changing Data Satus. Full details: {e}", status_code=500)

        return {"data": data, "org": org, "user": user}
