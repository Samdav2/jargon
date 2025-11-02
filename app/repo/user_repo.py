from model.user import User, UserProfile
from sqlmodel import select
from uuid import uuid4
from schemas.user import UserCreate, UserProfileCreate, UserRead
from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from passlib.hash import bcrypt
import bcrypt
from dependecies.encrypt_user_data import encrypt_private_key, encrypt_pw_key
from dependecies.user_encryption import hash_identifier
import os
from dotenv import load_dotenv

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
        xxx_kkk= await encrypt_private_key(xxx_kkk)
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
