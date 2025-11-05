from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.data_vault import UserDataVautltCreate, GetUserData, Decision
from app.model.user import UserDataVault, User
from sqlmodel import select
from sqlalchemy.orm import selectinload
from app.dependecies.user_encryption import hash_identifier
from fastapi import HTTPException, Depends
from app.security.user_token import get_user_Pii, decode_user_pii
from uuid import UUID
import asyncio
from app.dependecies.db import get_session
from app.repo.third_party_repo import ThirdPartyRepo
from app.schemas.third_party import ThirdPartyDataRequestStorageCreate
from typing import Union
from app.model.third_party import ThirdParty
from asyncio import gather

async def save_user_data_to_db(data_vault_entry: UserDataVautltCreate, db: AsyncSession):
    data_vault = UserDataVault(**data_vault_entry.model_dump())
    db.add(data_vault)
    await db.commit()
    await db.refresh(data_vault)
    return data_vault

async def get_user_data(data_request: GetUserData, db: AsyncSession):
    if data_request.data_type == []:
        statement = select(User).where(User.id == data_request.user_id).options(selectinload(User.data_vault_entries))
        result = await db.exec(statement)
        user = result.first()
        data = user.data_vault_entries
        return {"user": user, "data": data}
    else:
        user_data = []
        statement = select(User).where(User.id == data_request.user_id).options(selectinload(User.data_vault_entries))
        result = await db.exec(statement)
        user = result.first()
        data = user.data_vault_entries
        for d in data:
            if d.data_type in data_request.data_type:
                user_data.append(d)
        return {"user": user, "data": user_data}


async def get_data_by_type(
        org_id: str,
        description: str,
        data_type: list[str],
        email: str,
        expire: int,
        db: AsyncSession
        ):
    data_store = []
    email_hash = await hash_identifier(email=email)
    stmt = select(User).where(User.email_index == email_hash).options(selectinload(User.data_vault_entries))
    stmt_b = select(ThirdParty).where(ThirdParty.id== org_id)

    async def run_statment(statement):
        result = await db.exec(statement)
        data = result.first()
        return data

    try:
        org, user_data = await gather(run_statment(stmt_b), run_statment(stmt))
        # result = await db.exec(stmt)
        # user_data = result.first()

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
            data_rejection_reason="Null"
        )

        third_party_repo = ThirdPartyRepo(db)

        await third_party_repo.save_request_data(storage)

        return {"pii":pii_data, "user": user_data, "org": org}

    except Exception as e:
        raise HTTPException(detail=f"Error Getting user. Full details: {e}", status_code=500)


async def decrypt_user_tk_data(token: str):
    try:
        encrypted_data = await  decode_user_pii(token=token)
        return encrypted_data
    except Exception as e:
        raise HTTPException(detail=f"Error Detokenizing Data. Full details: {e}", status_code=500)

async def approve_reject(data_id: UUID, response: Decision, db: AsyncSession):
    if data_id:
        try:
            stmt = select(UserDataVault).where(UserDataVault.id == data_id).options(selectinload(UserDataVault.user))
            result = await db.exec(stmt)
            data = result.first()
            user = data.user

            if data.added_by:
                stmt_b = select(ThirdParty).where (ThirdParty.id == data.added_by)
                result_b = await db.exec(stmt_b)
                org = result_b.first()


            data.status = response
            db.add(data)
            await db.commit()
            await db.refresh(data)

        except Exception as e:
            raise HTTPException(detail=f"Error Changing Data Satus. Full details: {e}", status_code=500)

        return {"data": data, "org": org, "user": user}
