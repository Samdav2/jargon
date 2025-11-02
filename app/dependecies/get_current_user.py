from security.user_token import decode_access_token
from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader, HTTPBearer
from dependecies.db import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from repo.user_repo import get_user
from repo.third_party_repo import ThirdPartyRepo
from schemas.user import UserRead

security = HTTPBearer()


async def get_current_user(token: str = Depends(security), db: AsyncSession = Depends(get_session)) -> UserRead:
    try:
        payload = await decode_access_token(token)
        user_id = getattr("sub", None)

        if user_id:
            user = await get_user(user_id=user_id, db = db)
            return user
    except Exception as e:
        raise HTTPException(detail=f"Error during token decryption: full details{e}", status_code=500)


async def get_current_org(token: str = Depends(security), db: AsyncSession = Depends(get_session)) -> UserRead:
    repo = ThirdPartyRepo(session=db)
    try:
        payload = await decode_access_token(token)
        user_id = getattr("sub", None)

        if user_id:
            user = await repo.get_by_org_id(org_id=user_id)
            return user
    except Exception as e:
        raise HTTPException(detail=f"Error during token decryption: full details{e}", status_code=500)
