from sqlmodel.ext.asyncio.session import AsyncSession
from schemas.data_vault import UserDataVautltCreate, GetUserData
from model.user import UserDataVault, User
from sqlmodel import select
from sqlalchemy.orm import selectinload

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
